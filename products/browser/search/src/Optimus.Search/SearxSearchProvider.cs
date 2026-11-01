using System.Net;
using System.Text.Json;

namespace Optimus.Search;

public sealed class SearchProviderException(bool timedOut = false) : Exception(timedOut ? "Search provider timed out." : "Search provider failed.")
{
    public bool TimedOut { get; } = timedOut;
}

public sealed class SearxSearchProvider : IDisposable
{
    private readonly Uri endpoint;
    private readonly HttpClient client;
    public SearxSearchProvider(string endpoint)
    {
        this.endpoint = ValidateEndpoint(endpoint);
        client = new HttpClient(new SocketsHttpHandler {
            AllowAutoRedirect = false, UseCookies = false, Credentials = null, DefaultProxyCredentials = null,
            AutomaticDecompression = DecompressionMethods.None
        }) { Timeout = Timeout.InfiniteTimeSpan };
    }
    private static Uri ValidateEndpoint(string endpoint)
    {
        if (!SearchValidation.TryNormalizeUrl(endpoint, out _) || !Uri.TryCreate(endpoint, UriKind.Absolute, out var uri)
            || uri.Query.Length != 0 || uri.Fragment.Length != 0
            || (uri.Scheme != "https" && !(uri.Scheme == "http" && (uri.Host.Equals("localhost", StringComparison.OrdinalIgnoreCase) || IPAddress.TryParse(uri.Host.Trim('[', ']'), out var ip) && IPAddress.IsLoopback(ip)))))
            throw new ArgumentException("Invalid search provider configuration.");
        return uri;
    }
    public async Task<IReadOnlyList<SearchResult>> SearchAsync(string query, string language, CancellationToken cancellationToken)
    {
        if (!SearchValidation.ValidQuery(query)) throw new ArgumentException("Invalid query.");
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        deadline.CancelAfter(TimeSpan.FromSeconds(10));
        try
        {
            var prefix = endpoint.AbsoluteUri.TrimEnd('/');
            var requestUri = new Uri(prefix + (endpoint.AbsolutePath.TrimEnd('/').EndsWith("/search", StringComparison.Ordinal) ? "" : "/search") + "?format=json&q=" + Uri.EscapeDataString(query) + "&language=" + Uri.EscapeDataString(language) + "&categories=general");
            using var request = new HttpRequestMessage(HttpMethod.Get, requestUri);
            request.Headers.Accept.ParseAdd("application/json");
            using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, deadline.Token);
            if (!response.IsSuccessStatusCode || response.Content.Headers.ContentLength > 1024 * 1024) throw new SearchProviderException();
            await using var stream = await response.Content.ReadAsStreamAsync(deadline.Token);
            var bytes = await BoundedRead.ReadAsync(stream, 1024 * 1024, deadline.Token);
            using var json = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 32 });
            if (json.RootElement.ValueKind != JsonValueKind.Object || !json.RootElement.TryGetProperty("results", out var list) || list.ValueKind != JsonValueKind.Array) throw new SearchProviderException();
            // A reported engine failure is a conservative total failure, even with partial results.
            if (json.RootElement.TryGetProperty("unresponsive_engines", out var failures)
                && (failures.ValueKind != JsonValueKind.Array || failures.GetArrayLength() != 0)) throw new SearchProviderException();
            var results = new List<SearchResult>();
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var item in list.EnumerateArray())
            {
                if (item.ValueKind != JsonValueKind.Object || !item.TryGetProperty("url", out var url) || url.ValueKind != JsonValueKind.String
                    || !SearchValidation.TryNormalizeUrl(ReadString(url), out var normalized) || !item.TryGetProperty("title", out var title) || title.ValueKind != JsonValueKind.String
                    || string.IsNullOrWhiteSpace(ReadString(title)) || !seen.Add(normalized)) continue;
                var content = item.TryGetProperty("content", out var text) && text.ValueKind == JsonValueKind.String ? ReadString(text) : "";
                results.Add(new(SearchValidation.Truncate(ReadString(title)!, 240), normalized, SearchValidation.Truncate(content, 1200), "SearXNG"));
                if (results.Count == 20) break;
            }
            deadline.Token.ThrowIfCancellationRequested();
            return results;
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested) { throw new SearchProviderException(true); }
        catch (Exception ex) when (ex is HttpRequestException or IOException or InvalidDataException or JsonException) { throw new SearchProviderException(); }
    }
    private static string ReadString(JsonElement value)
    {
        try { return value.GetString()!; }
        catch (InvalidOperationException) { throw new SearchProviderException(); }
    }
    public void Dispose() => client.Dispose();
}
