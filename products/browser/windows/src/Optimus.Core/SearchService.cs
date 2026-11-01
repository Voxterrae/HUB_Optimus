using System.Globalization;
using System.Net;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Optimus.Core;

public sealed class OptimusSearchService
{
    private readonly HttpClient client;
    private readonly Func<string, HttpClient> localClientFactory;
    public OptimusSearchService(HttpClient client) : this(client, LocalSearchTransport.CreateClient) { }
    internal OptimusSearchService(HttpClient client, Func<string, HttpClient> localClientFactory)
    { this.client = client; this.localClientFactory = localClientFactory; }
    private const int MaxResponseBytes = 1024 * 1024;
    private const int MaxResults = 20;

    public Task<SearchResponse> SearchAsync(string query, IReadOnlyList<Bookmark> bookmarks,
        string? searxEndpoint, CancellationToken cancellationToken) => SearchCoreAsync(query, bookmarks, searxEndpoint, null, cancellationToken);

    public Task<SearchResponse> SearchAsync(string query, IReadOnlyList<Bookmark> bookmarks,
        OptimusSearchTarget target, CancellationToken cancellationToken) => target.Scope == OptimusSearchScope.Wikipedia
        ? SearchCoreAsync(query, bookmarks, null, null, cancellationToken)
        : SearchCoreAsync(query, bookmarks, null, target, cancellationToken);

    private async Task<SearchResponse> SearchCoreAsync(string query, IReadOnlyList<Bookmark> bookmarks,
        string? searxEndpoint, OptimusSearchTarget? local, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var useSearx = searxEndpoint is not null;
        var scope = local?.Scope == OptimusSearchScope.Index ? "index" : "web";
        var provider = local.HasValue ? (scope == "index" ? "Índice Optimus y marcadores" : "Web Optimus y marcadores") : useSearx ? "SearXNG y marcadores" : "Wikipedia y marcadores";
        List<SearchResult> results = [];
        SearchResponse Response(string? error) => new(results.AsReadOnly(), provider, error);
        if (string.IsNullOrWhiteSpace(query) || query.Length > 500)
            return Response("Escribe una consulta de 1 a 500 caracteres.");
        if (local is {} target && (!Enum.IsDefined(target.Scope) || !IsValidLocalEndpoint(target.Endpoint) || !IsValidToken(target.BearerToken)))
            return Response("No se pudo autenticar el servicio local de Optimus Search. Comprueba su configuración y token de perfil.");
        if (useSearx && !IsValidEndpoint(searxEndpoint))
            return Response("La dirección de SearXNG no es válida: usa HTTPS o HTTP en localhost, sin credenciales, consulta ni fragmento.");

        var seen = new HashSet<string>(StringComparer.Ordinal);
        void Add(string title, string url, string snippet, string source)
        {
            if (results.Count >= MaxResults || !TryDestination(url, out var destination) || !seen.Add(new UriBuilder(destination) { Fragment = "" }.Uri.AbsoluteUri)) return;
            results.Add(new(ToText(title, 240), destination.AbsoluteUri, ToText(snippet, 1200), source));
        }
        query = query.Trim();
        foreach (var bookmark in bookmarks)
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (bookmark.Title.Contains(query, StringComparison.OrdinalIgnoreCase) || bookmark.Url.Contains(query, StringComparison.OrdinalIgnoreCase))
                Add(bookmark.Title, bookmark.Url, "Marcador guardado en este navegador", "Marcadores");
            if (results.Count == MaxResults) break;
        }

        var endpoint = local.HasValue ? new Uri(OptimusSearchTarget.LocalEndpoint + "/search?format=json&q=" + Uri.EscapeDataString(query) + "&scope=" + scope + "&language=es") : useSearx ? new Uri(searxEndpoint!.TrimEnd('/') + (new Uri(searxEndpoint).AbsolutePath.TrimEnd('/').EndsWith("/search", StringComparison.Ordinal) ? "" : "/search") + "?format=json&q=" + Uri.EscapeDataString(query))
            : new Uri("https://es.wikipedia.org/w/api.php?action=query&list=search&format=json&utf8=1&srlimit=20&srsearch=" + Uri.EscapeDataString(query));
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        deadline.CancelAfter(TimeSpan.FromSeconds(10));
        try
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, endpoint);
            request.Headers.Accept.ParseAdd("application/json");
            if (local is {} authenticated) request.Headers.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", authenticated.BearerToken);
            request.Headers.UserAgent.ParseAdd("OptimusBrowser/0.2 (native search)");
            using var localClient = local is {} localTarget ? localClientFactory(localTarget.BearerToken!) : null;
            using var response = await (localClient ?? client).SendAsync(request, HttpCompletionOption.ResponseHeadersRead, deadline.Token).ConfigureAwait(false);
            if (!response.IsSuccessStatusCode && local.HasValue) return Response(response.StatusCode switch
            {
                HttpStatusCode.ServiceUnavailable => "La búsqueda Web no está configurada en el servicio local. Configura el servidor SearXNG del operador.",
                HttpStatusCode.Unauthorized => "El servicio local no aceptó el token del perfil.",
                HttpStatusCode.GatewayTimeout => "El proveedor Web superó el tiempo límite.",
                _ => "El servicio local no pudo completar la búsqueda. No se consultó otro proveedor."
            });
            if (!response.IsSuccessStatusCode) return Response($"{(useSearx ? "SearXNG" : "Wikipedia")} devolvió HTTP {(int)response.StatusCode}. No se consultó otro proveedor.");
            if (response.Content.Headers.ContentLength > MaxResponseBytes) return Response("La respuesta supera el límite de 1 MiB.");
            await using var stream = await response.Content.ReadAsStreamAsync(deadline.Token).ConfigureAwait(false);
            using var bytes = new MemoryStream();
            var buffer = new byte[8192];
            while (true)
            {
                // Read at most one byte beyond the cap, including unknown/chunked lengths.
                int read = await stream.ReadAsync(buffer.AsMemory(0, (int)Math.Min(buffer.Length, MaxResponseBytes - bytes.Length + 1)), deadline.Token).ConfigureAwait(false);
                if (read == 0) break;
                if (bytes.Length + read > MaxResponseBytes) return Response("La respuesta supera el límite de 1 MiB.");
                bytes.Write(buffer, 0, read);
            }
            deadline.Token.ThrowIfCancellationRequested();
            using var document = JsonDocument.Parse(bytes.GetBuffer().AsMemory(0, (int)bytes.Length));
            var root = document.RootElement;
            if (local.HasValue && !ValidProtocol(root, scope))
                return Response("El servicio no devolvió el protocolo Optimus Search v1 esperado.");
            if (root.ValueKind != JsonValueKind.Object || (root.TryGetProperty("error", out var providerError) && providerError.ValueKind != JsonValueKind.Null))
                return Response("El proveedor devolvió una respuesta de error.");
            JsonElement entries;
            if (useSearx || local.HasValue)
            {
                if (!root.TryGetProperty("results", out entries) || entries.ValueKind != JsonValueKind.Array)
                    return Response("SearXNG no devolvió una lista de resultados válida; comprueba que permite format=json.");
                foreach (var item in entries.EnumerateArray())
                {
                    deadline.Token.ThrowIfCancellationRequested();
                    if (item.ValueKind == JsonValueKind.Object)
                        Add(Field(item, "title"), Field(item, "url"), Field(item, "content"), local.HasValue ? ToText(Field(item, "source"), 240) : "SearXNG");
                    if (results.Count == MaxResults) break;
                }
            }
            else
            {
                if (!root.TryGetProperty("query", out var data) || data.ValueKind != JsonValueKind.Object || !data.TryGetProperty("search", out entries) || entries.ValueKind != JsonValueKind.Array)
                    return Response("Wikipedia no devolvió una lista de resultados válida.");
                foreach (var item in entries.EnumerateArray())
                {
                    deadline.Token.ThrowIfCancellationRequested();
                    if (item.ValueKind == JsonValueKind.Object && item.TryGetProperty("pageid", out var id) && id.ValueKind == JsonValueKind.Number && id.TryGetInt64(out var pageId) && pageId > 0)
                        Add(Field(item, "title"), "https://es.wikipedia.org/?curid=" + pageId.ToString(CultureInfo.InvariantCulture), Field(item, "snippet"), "Wikipedia");
                    if (results.Count == MaxResults) break;
                }
            }
            cancellationToken.ThrowIfCancellationRequested();
            if (local.HasValue && scope == "index") provider += " (" + root.GetProperty("optimus").GetProperty("indexedDocuments").GetInt32().ToString(CultureInfo.InvariantCulture) + " documentos)";
            return Response(null);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested) { throw; }
        catch (OperationCanceledException) { return Response("La búsqueda superó el tiempo límite de 10 segundos o la conexión se canceló."); }
        catch (JsonException) { return Response("El proveedor devolvió JSON no válido."); }
        catch (HttpRequestException) { return Response("No se pudo conectar con el proveedor. No se consultó otro proveedor."); }
        catch (IOException) { return Response("No se pudo leer la respuesta del proveedor."); }
    }

    public static bool IsValidToken(string? token) => token is { Length: 64 } && token.All(char.IsAsciiHexDigit);
    public static bool IsValidLocalEndpoint(string? endpoint) => endpoint is null || endpoint == OptimusSearchTarget.LocalEndpoint || endpoint == OptimusSearchTarget.LocalEndpoint + "/";
    private static bool ValidProtocol(JsonElement root, string scope) => root.ValueKind == JsonValueKind.Object
        && root.TryGetProperty("optimus", out var marker) && marker.ValueKind == JsonValueKind.Object
        && marker.TryGetProperty("version", out var version) && version.ValueKind == JsonValueKind.Number && version.TryGetInt32(out var v) && v == 1
        && Field(marker, "scope") == scope
        && marker.TryGetProperty("webConfigured", out var configured) && configured.ValueKind is JsonValueKind.True or JsonValueKind.False
        && marker.TryGetProperty("indexedDocuments", out var documents) && documents.ValueKind == JsonValueKind.Number && documents.TryGetInt32(out var count) && count is >= 0 and <= 1000;

    public static bool IsValidEndpoint(string? endpoint) => TryDestination(endpoint, out var uri)
        && (uri.Scheme == Uri.UriSchemeHttps || uri.Host.Equals("localhost", StringComparison.OrdinalIgnoreCase) || IPAddress.TryParse(uri.Host.Trim('[', ']'), out var ip) && IPAddress.IsLoopback(ip))
        && uri.Query.Length == 0 && uri.Fragment.Length == 0;

    private static bool TryDestination(string? value, out Uri uri)
    {
        uri = null!;
        return !string.IsNullOrWhiteSpace(value) && value.Length <= 2048 && !value.Any(char.IsControl) && !value.Contains('\\')
            && Uri.TryCreate(value, UriKind.Absolute, out uri!) && uri.Host.Length > 0 && uri.UserInfo.Length == 0
            && (uri.Scheme == Uri.UriSchemeHttps || uri.Scheme == Uri.UriSchemeHttp) && uri.AbsoluteUri.Length <= 2048;
    }

    private static string Field(JsonElement item, string name) => item.TryGetProperty(name, out var field) && field.ValueKind == JsonValueKind.String ? field.GetString() ?? "" : "";

    private static string ToText(string html, int limit)
    {
        // The returned strings are displayed by TextBlock only, never an HTML renderer.
        var text = WebUtility.HtmlDecode(Regex.Replace(html, "<[^>]*>", "", RegexOptions.NonBacktracking));
        text = Regex.Replace(text, @"\s+", " ", RegexOptions.NonBacktracking).Trim();
        if (text.Length <= limit) return text;
        var length = char.IsHighSurrogate(text[limit - 2]) ? limit - 2 : limit - 1;
        return text[..length] + "…";
    }
}
