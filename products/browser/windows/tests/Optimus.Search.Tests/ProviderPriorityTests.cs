using System.Net;
using System.Text;
using System.Text.Json;
using Optimus.Core;

static class ProviderPriorityTests
{
    private const string Token = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef";
    public static void Register(Action<string, Func<Task>> test)
    {
        foreach (var scope in new[] { OptimusSearchScope.Web, OptimusSearchScope.Index })
            test($"typed {scope} provider remains visible with twenty matching bookmarks", async () =>
            {
                var source = scope == OptimusSearchScope.Web ? "SearXNG" : "Índice Optimus";
                using var handler = new Fixture(_ => Json(Body(scope, [Entry("https://provider.example/result", source)])));
                using var client = new HttpClient(handler);
                var response = await new OptimusSearchService(client, _ => TestTransport.Borrow(client))
                    .SearchAsync("sol", Bookmarks(), new OptimusSearchTarget(scope, null, Token), default);
                Check(response.Error is null && response.Results.Count == 20, "Bounded successful response");
                Check(response.Results[0].Source == source && response.Results[0].Url == "https://provider.example/result", "Selected provider has priority");
                Check(response.Results.Count(x => x.Source == "Marcadores") == 19, "Bookmarks fill remaining slots");
            });
        test("direct SearXNG provider remains visible with twenty matching bookmarks", async () =>
        {
            using var handler = new Fixture(_ => Json(Body(OptimusSearchScope.Web, [Entry("https://provider.example/result", "SearXNG")])));
            using var client = new HttpClient(handler);
            var response = await new OptimusSearchService(client).SearchAsync("sol", Bookmarks(), "https://search.example", default);
            Check(response.Error is null && response.Results.Count == 20 && response.Results[0].Source == "SearXNG", "Direct provider cannot be displaced");
        });
        test("Wikipedia provider remains visible with twenty matching bookmarks", async () =>
        {
            using var handler = new Fixture(_ => Json("""{"query":{"search":[{"pageid":19,"title":"Sol","snippet":"Public fixture"}]}}"""));
            using var client = new HttpClient(handler);
            var response = await new OptimusSearchService(client).SearchAsync("sol", Bookmarks(), null, default);
            Check(response.Error is null && response.Results.Count == 20 && response.Results[0].Source == "Wikipedia", "Selected Wikipedia provider cannot be displaced");
        });
        test("provider owns duplicate bookmark destination and provenance across fragments", async () =>
        {
            using var handler = new Fixture(_ => Json(Body(OptimusSearchScope.Web, [Entry("https://provider.example/result#web", "SearXNG")])));
            using var client = new HttpClient(handler);
            var response = await new OptimusSearchService(client, _ => TestTransport.Borrow(client))
                .SearchAsync("sol", [new("sol bookmark", "https://provider.example/result#bookmark")], new OptimusSearchTarget(OptimusSearchScope.Web, null, Token), default);
            Check(response.Error is null && response.Results.Single() == new SearchResult("Sol provider", "https://provider.example/result#web", "Public fixture", "SearXNG"), "Provider result wins canonical duplicate without losing provenance");
        });
        test("twenty provider results keep their order and bound ahead of bookmarks", async () =>
        {
            var entries = Enumerable.Range(0, 25).Select(i => Entry($"https://provider.example/{i}", "SearXNG")).ToArray();
            using var handler = new Fixture(_ => Json(Body(OptimusSearchScope.Web, entries)));
            using var client = new HttpClient(handler);
            var response = await new OptimusSearchService(client, _ => TestTransport.Borrow(client))
                .SearchAsync("sol", Bookmarks(), new OptimusSearchTarget(OptimusSearchScope.Web, null, Token), default);
            Check(response.Error is null && response.Results.Count == 20 && response.Results.All(x => x.Source == "SearXNG"), "Provider fills bounded list");
            Check(response.Results.Select(x => x.Url).SequenceEqual(Enumerable.Range(0, 20).Select(i => $"https://provider.example/{i}")), "Provider order preserved");
        });
        test("empty and failed provider responses retain twenty safe unique bookmarks", async () =>
        {
            foreach (var failure in new[] { false, true })
            {
                using var handler = new Fixture(_ => failure ? new HttpResponseMessage(HttpStatusCode.BadGateway) : Json(Body(OptimusSearchScope.Web, [])));
                using var client = new HttpClient(handler);
                var response = await new OptimusSearchService(client, _ => TestTransport.Borrow(client))
                    .SearchAsync("sol", Bookmarks(), new OptimusSearchTarget(OptimusSearchScope.Web, null, Token), default);
                Check((response.Error is not null) == failure && response.Results.Count == 20 && response.Results.All(x => x.Source == "Marcadores"), "Recovery keeps bookmarks and the actual error state");
            }
        });
        test("provider priority retains the bookmark snapshot from search submission", async () =>
        {
            using var handler = new DeferredProvider();
            using var client = new HttpClient(handler);
            var bookmarks = new List<Bookmark> { new("sol original", "https://bookmark.example/original") };
            var pending = new OptimusSearchService(client, _ => TestTransport.Borrow(client))
                .SearchAsync("sol", bookmarks, new OptimusSearchTarget(OptimusSearchScope.Web, null, Token), default);
            await handler.Started.Task.WaitAsync(TimeSpan.FromSeconds(2));
            bookmarks[0] = new("sol replacement", "https://bookmark.example/replacement");
            handler.Release.TrySetResult();
            var response = await pending.WaitAsync(TimeSpan.FromSeconds(2));
            Check(response.Error is null && response.Results.Count == 2, "Provider and submitted bookmark are retained");
            Check(response.Results[1].Url == "https://bookmark.example/original", "Edits during the request apply to the next search");
        });
    }
    private static Bookmark[] Bookmarks() => Enumerable.Range(0, 25).Select(i => new Bookmark($"sol {i}", $"https://bookmark.example/{i}")).ToArray();
    private static object Entry(string url, string source) => new { title = "Sol provider", url, content = "Public fixture", source };
    private static string Body(OptimusSearchScope scope, object[] results) => JsonSerializer.Serialize(new
    {
        query = "sol", results,
        optimus = new { version = 1, scope = scope == OptimusSearchScope.Web ? "web" : "index", webConfigured = true, indexedDocuments = 0 }
    });
    private static HttpResponseMessage Json(string body) => new(HttpStatusCode.OK) { Content = new StringContent(body, Encoding.UTF8, "application/json") };
    private static void Check(bool value, string message) { if (!value) throw new InvalidOperationException(message); }
    private sealed class DeferredProvider : HttpMessageHandler
    {
        public TaskCompletionSource Started { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        public TaskCompletionSource Release { get; } = new(TaskCreationOptions.RunContinuationsAsynchronously);
        protected override async Task<HttpResponseMessage> SendAsync(HttpRequestMessage request, CancellationToken token)
        {
            Started.TrySetResult();
            await Release.Task.WaitAsync(token);
            return Json(Body(OptimusSearchScope.Web, [Entry("https://provider.example/result", "SearXNG")]));
        }
        protected override void Dispose(bool disposing) { Release.TrySetCanceled(); base.Dispose(disposing); }
    }
}
