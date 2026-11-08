using System.Net;
using System.Text;
using System.Text.Json;
using System.Text.RegularExpressions;

namespace Optimus.Search.Brave;

/// <summary>Server-side Web adapter. Constructing it sends nothing; no application registers it.</summary>
public sealed class BraveSearchProvider : IDisposable
{
    private const int MaxBytes = 1024 * 1024;
    private readonly HttpClient client;
    private readonly string subscriptionToken;
    private static readonly Regex Tags = new("<[^>]*>", RegexOptions.CultureInvariant, TimeSpan.FromMilliseconds(100));

    public BraveSearchProvider(string subscriptionToken) : this(ValidateToken(subscriptionToken), CreateHandler()) { }

    // Transport replacement is deliberately internal: consumers cannot configure an arbitrary destination.
    internal BraveSearchProvider(string subscriptionToken, HttpMessageHandler handler)
    {
        this.subscriptionToken = ValidateToken(subscriptionToken);
        client = new HttpClient(handler, disposeHandler: true) { Timeout = Timeout.InfiniteTimeSpan };
    }

    internal static SocketsHttpHandler CreateHandler() => new()
    {
        AllowAutoRedirect = false, UseProxy = false, UseCookies = false,
        Credentials = null, DefaultProxyCredentials = null,
        AutomaticDecompression = DecompressionMethods.None,
        ActivityHeadersPropagator = null,
        ConnectTimeout = TimeSpan.FromSeconds(10),
        PooledConnectionLifetime = TimeSpan.Zero
    };

    public async Task<IReadOnlyList<BraveSearchResult>> SearchAsync(string query, string language, CancellationToken cancellationToken = default)
    {
        ValidateQuery(query);
        var searchLanguage = MapLanguage(language);
        cancellationToken.ThrowIfCancellationRequested();
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        deadline.CancelAfter(TimeSpan.FromSeconds(10));
        try
        {
            var uri = new Uri("https://api.search.brave.com/res/v1/web/search?q=" + Uri.EscapeDataString(query)
                + "&search_lang=" + searchLanguage + "&count=20&safesearch=strict&text_decorations=false&result_filter=web");
            using var request = new HttpRequestMessage(HttpMethod.Get, uri);
            request.Headers.Add("x-subscription-token", subscriptionToken);
            request.Headers.Accept.ParseAdd("application/json");
            request.Headers.AcceptEncoding.ParseAdd("identity");
            using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, deadline.Token);
            if (!response.IsSuccessStatusCode)
                throw new BraveSearchException(response.StatusCode switch {
                    HttpStatusCode.Unauthorized or HttpStatusCode.Forbidden => BraveSearchFailure.Authentication,
                    HttpStatusCode.TooManyRequests => BraveSearchFailure.RateLimited,
                    _ => BraveSearchFailure.Upstream
                });
            if (response.Content.Headers.ContentLength > MaxBytes || response.Content.Headers.ContentEncoding.Count != 0)
                throw InvalidResponse();
            await using var stream = await response.Content.ReadAsStreamAsync(deadline.Token);
            using var buffer = new MemoryStream();
            var chunk = new byte[8192];
            while (true)
            {
                var read = await stream.ReadAsync(chunk.AsMemory(0, (int)Math.Min(chunk.Length, MaxBytes + 1L - buffer.Length)), deadline.Token);
                if (read == 0) break;
                if (buffer.Length + read > MaxBytes) throw InvalidResponse();
                buffer.Write(chunk, 0, read);
            }
            deadline.Token.ThrowIfCancellationRequested();
            using var json = JsonDocument.Parse(buffer.GetBuffer().AsMemory(0, (int)buffer.Length), new JsonDocumentOptions { MaxDepth = 32 });
            ValidateUniqueFields(json.RootElement);
            var root = json.RootElement;
            if (root.ValueKind != JsonValueKind.Object || !HasString(root, "type", "search")) throw InvalidResponse();
            if (!root.TryGetProperty("web", out var web) || web.ValueKind == JsonValueKind.Null) return [];
            if (web.ValueKind != JsonValueKind.Object || !HasString(web, "type", "search")
                || !web.TryGetProperty("results", out var items) || items.ValueKind != JsonValueKind.Array) throw InvalidResponse();
            var results = new List<BraveSearchResult>();
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var item in items.EnumerateArray())
            {
                deadline.Token.ThrowIfCancellationRequested();
                if (item.ValueKind != JsonValueKind.Object || !item.TryGetProperty("url", out var url) || url.ValueKind != JsonValueKind.String
                    || !NormalizeUrl(url.GetString(), out var normalized) || !item.TryGetProperty("title", out var title) || title.ValueKind != JsonValueKind.String) continue;
                var cleanTitle = PlainText(title.GetString()!, 240);
                if (string.IsNullOrWhiteSpace(cleanTitle)) continue;
                var content = item.TryGetProperty("description", out var description) && description.ValueKind == JsonValueKind.String
                    ? PlainText(description.GetString()!, 1200) : "";
                // Do not return a credential echoed by a compromised upstream or transport.
                if (normalized.Contains(subscriptionToken, StringComparison.Ordinal) || cleanTitle.Contains(subscriptionToken, StringComparison.Ordinal)
                    || content.Contains(subscriptionToken, StringComparison.Ordinal)) throw InvalidResponse();
                if (!seen.Add(normalized)) continue;
                results.Add(new(cleanTitle, normalized, content, "Brave"));
                if (results.Count == 20) break;
            }
            deadline.Token.ThrowIfCancellationRequested();
            return results;
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested) { throw new OperationCanceledException(cancellationToken); }
        catch (OperationCanceledException) { throw new BraveSearchException(BraveSearchFailure.Timeout); }
        catch (Exception ex) when (ex is HttpRequestException or IOException) { throw new BraveSearchException(BraveSearchFailure.Transport); }
        catch (Exception ex) when (ex is JsonException or InvalidOperationException or RegexMatchTimeoutException) { throw InvalidResponse(); }
    }

    private static BraveSearchException InvalidResponse() => new(BraveSearchFailure.InvalidResponse);
    private static bool HasString(JsonElement element, string name, string value) => element.TryGetProperty(name, out var property) && property.ValueKind == JsonValueKind.String && property.GetString() == value;
    private static string ValidateToken(string token)
    {
        if (string.IsNullOrEmpty(token) || token.Length > 512 || token.Any(c => c < 33 || c > 126)) throw new ArgumentException("Invalid provider credential.");
        return token;
    }
    private static void ValidateQuery(string query)
    {
        if (string.IsNullOrWhiteSpace(query) || query.Length > 500 || query.Any(char.IsControl)
            || query.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries).Length > 75) throw new ArgumentException("Invalid query.");
        try { _ = new UTF8Encoding(false, true).GetByteCount(query); }
        catch (EncoderFallbackException) { throw new ArgumentException("Invalid query."); }
    }
    private static string MapLanguage(string language)
    {
        if (language == null || (language.Length != 2 && !(language.Length == 5 && language[2] == '-' && char.IsAsciiLetter(language[3]) && char.IsAsciiLetter(language[4]))))
            throw new ArgumentException("Unsupported search language.");
        var code = language[..2].ToLowerInvariant();
        return code is "es" or "ca" or "en" or "de" or "fr" or "ru" ? code : throw new ArgumentException("Unsupported search language.");
    }
    private static bool NormalizeUrl(string? value, out string normalized)
    {
        normalized = "";
        if (string.IsNullOrWhiteSpace(value) || value.Length > 2048 || value != value.Trim() || value.Any(char.IsControl) || value.Contains('\\')
            || !Uri.TryCreate(value, UriKind.Absolute, out var uri) || uri.Scheme is not ("https" or "http") || uri.UserInfo.Length != 0) return false;
        normalized = new UriBuilder(uri) { Fragment = "" }.Uri.AbsoluteUri;
        return normalized.Length <= 2048;
    }
    private static string PlainText(string value, int maximum)
    {
        var text = Tags.Replace(WebUtility.HtmlDecode(value), "");
        text = new string(text.Select(c => char.IsControl(c) ? ' ' : c).ToArray());
        if (text.Length <= maximum) return text;
        if (char.IsHighSurrogate(text[maximum - 1])) maximum--;
        return text[..maximum];
    }
    private static void ValidateUniqueFields(JsonElement element)
    {
        if (element.ValueKind == JsonValueKind.Object)
        {
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var field in element.EnumerateObject()) { if (!names.Add(field.Name)) throw InvalidResponse(); ValidateUniqueFields(field.Value); }
        }
        else if (element.ValueKind == JsonValueKind.Array) foreach (var item in element.EnumerateArray()) ValidateUniqueFields(item);
    }
    public void Dispose() => client.Dispose();
}
