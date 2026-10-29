using System.Globalization;
using System.Net;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Optimus.Core;

public sealed class OptimusSearchService(HttpClient client)
{
    private const int MaxResponseBytes = 1024 * 1024;
    private const int MaxResults = 20;

    public async Task<SearchResponse> SearchAsync(string query, IReadOnlyList<Bookmark> bookmarks,
        string? searxEndpoint, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var useSearx = searxEndpoint is not null;
        var provider = useSearx ? "SearXNG y marcadores" : "Wikipedia y marcadores";
        List<SearchResult> results = [];
        SearchResponse Response(string? error) => new(results.AsReadOnly(), provider, error);
        if (string.IsNullOrWhiteSpace(query) || query.Length > 500)
            return Response("Escribe una consulta de 1 a 500 caracteres.");
        if (useSearx && !IsValidEndpoint(searxEndpoint))
            return Response("La dirección de SearXNG no es válida: usa HTTPS o HTTP en localhost, sin credenciales, consulta ni fragmento.");

        var seen = new HashSet<string>(StringComparer.Ordinal);
        void Add(string title, string url, string snippet, string source)
        {
            if (results.Count >= MaxResults || !TryDestination(url, out var destination) || !seen.Add(destination.AbsoluteUri)) return;
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

        var endpoint = useSearx ? new Uri(searxEndpoint!.TrimEnd('/') + (new Uri(searxEndpoint).AbsolutePath.TrimEnd('/').EndsWith("/search", StringComparison.Ordinal) ? "" : "/search") + "?format=json&q=" + Uri.EscapeDataString(query))
            : new Uri("https://es.wikipedia.org/w/api.php?action=query&list=search&format=json&utf8=1&srlimit=20&srsearch=" + Uri.EscapeDataString(query));
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        deadline.CancelAfter(TimeSpan.FromSeconds(10));
        try
        {
            using var request = new HttpRequestMessage(HttpMethod.Get, endpoint);
            request.Headers.Accept.ParseAdd("application/json");
            request.Headers.UserAgent.ParseAdd("OptimusBrowser/0.2 (native search)");
            using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, deadline.Token).ConfigureAwait(false);
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
            if (root.ValueKind != JsonValueKind.Object || root.TryGetProperty("error", out _))
                return Response("El proveedor devolvió una respuesta de error.");
            JsonElement entries;
            if (useSearx)
            {
                if (!root.TryGetProperty("results", out entries) || entries.ValueKind != JsonValueKind.Array)
                    return Response("SearXNG no devolvió una lista de resultados válida; comprueba que permite format=json.");
                foreach (var item in entries.EnumerateArray())
                {
                    deadline.Token.ThrowIfCancellationRequested();
                    if (item.ValueKind == JsonValueKind.Object)
                        Add(Field(item, "title"), Field(item, "url"), Field(item, "content"), "SearXNG");
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
            return Response(null);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested) { throw; }
        catch (OperationCanceledException) { return Response("La búsqueda superó el tiempo límite de 10 segundos o la conexión se canceló."); }
        catch (JsonException) { return Response("El proveedor devolvió JSON no válido."); }
        catch (HttpRequestException) { return Response("No se pudo conectar con el proveedor. No se consultó otro proveedor."); }
        catch (IOException) { return Response("No se pudo leer la respuesta del proveedor."); }
    }

    public static bool IsValidEndpoint(string? endpoint) => TryDestination(endpoint, out var uri)
        && (uri.Scheme == Uri.UriSchemeHttps || uri.IsLoopback)
        && uri.Query.Length == 0 && uri.Fragment.Length == 0;

    private static bool TryDestination(string? value, out Uri uri)
    {
        uri = null!;
        return !string.IsNullOrWhiteSpace(value) && !value.Any(char.IsControl) && !value.Contains('\\')
            && Uri.TryCreate(value, UriKind.Absolute, out uri!) && uri.Host.Length > 0 && uri.UserInfo.Length == 0
            && (uri.Scheme == Uri.UriSchemeHttps || uri.Scheme == Uri.UriSchemeHttp);
    }

    private static string Field(JsonElement item, string name) => item.TryGetProperty(name, out var field) && field.ValueKind == JsonValueKind.String ? field.GetString() ?? "" : "";

    private static string ToText(string html, int limit)
    {
        // The returned strings are displayed by TextBlock only, never an HTML renderer.
        var text = WebUtility.HtmlDecode(Regex.Replace(html, "<[^>]*>", "", RegexOptions.NonBacktracking));
        text = Regex.Replace(text, @"\s+", " ", RegexOptions.NonBacktracking).Trim();
        if (text.Length <= limit) return text;
        var length = char.IsHighSurrogate(text[limit - 1]) ? limit - 1 : limit;
        return text[..length] + "…";
    }
}
