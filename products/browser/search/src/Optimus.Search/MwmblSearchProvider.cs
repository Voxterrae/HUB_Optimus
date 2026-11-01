using System.Diagnostics;
using System.Net;
using System.Text.Json;

namespace Optimus.Search;

public sealed class MwmblSearchProvider : IWebSearchProvider
{
    private const int MaximumBytes = 1024 * 1024;
    private static readonly SemaphoreSlim DispatchGate = new(1, 1);
    private static readonly TimeSpan MinimumSpacing = TimeSpan.FromSeconds(1.1);
    private static long? lastDispatch;
    private readonly HttpClient client;

    public MwmblSearchProvider() : this(new SocketsHttpHandler
    {
        AllowAutoRedirect = false,
        UseCookies = false,
        Credentials = null,
        DefaultProxyCredentials = null,
        AutomaticDecompression = DecompressionMethods.None
    }) { }

    internal MwmblSearchProvider(HttpMessageHandler handler)
    {
        client = new HttpClient(handler) { Timeout = Timeout.InfiniteTimeSpan };
    }

    public async Task<IReadOnlyList<SearchResult>> SearchAsync(string query, string language, CancellationToken cancellationToken)
    {
        if (!SearchValidation.ValidQuery(query)) throw new ArgumentException("Invalid query.");
        using var deadline = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken);
        deadline.CancelAfter(TimeSpan.FromSeconds(10));
        var acquired = false;
        try
        {
            // Anonymous quota is per IP. This gate only coordinates this process, including separate instances.
            await DispatchGate.WaitAsync(deadline.Token);
            acquired = true;
            if (lastDispatch is {} previous)
            {
                var remaining = MinimumSpacing - Stopwatch.GetElapsedTime(previous);
                if (remaining > TimeSpan.Zero) await Task.Delay(remaining, deadline.Token);
            }
            deadline.Token.ThrowIfCancellationRequested();
            using var request = new HttpRequestMessage(HttpMethod.Get,
                "https://api.mwmbl.org/api/v2/search/?q=" + Uri.EscapeDataString(query));
            request.Headers.Accept.ParseAdd("application/json");
            request.Headers.UserAgent.ParseAdd("OptimusSearch/0.3 (Mwmbl pilot)");
            lastDispatch = Stopwatch.GetTimestamp();
            // Hold the gate through disposal so slow bodies cannot create an unbounded concurrent request pool.
            using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, deadline.Token);
            if (response.StatusCode == HttpStatusCode.TooManyRequests) throw new SearchProviderException(rateLimited: true);
            if (!response.IsSuccessStatusCode || response.Content.Headers.ContentLength > MaximumBytes) throw new SearchProviderException();
            await using var stream = await response.Content.ReadAsStreamAsync(deadline.Token);
            var bytes = await BoundedRead.ReadAsync(stream, MaximumBytes, deadline.Token);
            using var json = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 32 });
            var root = json.RootElement;
            if (root.ValueKind != JsonValueKind.Object
                || !root.TryGetProperty("results", out var rows) || rows.ValueKind != JsonValueKind.Array
                || root.TryGetProperty("error", out var error) && error.ValueKind != JsonValueKind.Null)
                throw new SearchProviderException();
            var results = new List<SearchResult>();
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var row in rows.EnumerateArray())
            {
                if (row.ValueKind != JsonValueKind.Object
                    || !row.TryGetProperty("url", out var url) || url.ValueKind != JsonValueKind.String
                    || !SearchValidation.TryNormalizeUrl(ReadString(url), out var normalized)
                    || !row.TryGetProperty("title", out var title) || title.ValueKind != JsonValueKind.String
                    || string.IsNullOrWhiteSpace(ReadString(title)) || !seen.Add(normalized)) continue;
                var content = row.TryGetProperty("content", out var text) && text.ValueKind == JsonValueKind.String ? ReadString(text) : "";
                var engine = row.TryGetProperty("engine", out var source) && source.ValueKind == JsonValueKind.String ? ReadString(source) : "";
                var provenance = engine switch
                {
                    "mwmbl" => "Mwmbl · índice",
                    "user" => "Mwmbl · comunidad",
                    "wikipedia" => "Mwmbl · Wikipedia",
                    "google" => "Mwmbl · Google",
                    _ => "Mwmbl · origen no especificado"
                };
                results.Add(new(SearchValidation.Truncate(ReadString(title), 240), normalized,
                    SearchValidation.Truncate(content, 1200), provenance));
                if (results.Count == 20) break;
            }
            deadline.Token.ThrowIfCancellationRequested();
            return results;
        }
        catch (OperationCanceledException) when (!cancellationToken.IsCancellationRequested) { throw new SearchProviderException(timedOut: true); }
        catch (Exception ex) when (ex is HttpRequestException or IOException or InvalidDataException or JsonException) { throw new SearchProviderException(); }
        finally { if (acquired) DispatchGate.Release(); }
    }

    private static string ReadString(JsonElement value)
    {
        try { return value.GetString()!; }
        catch (InvalidOperationException) { throw new SearchProviderException(); }
    }

    public void Dispose() => client.Dispose();
}
