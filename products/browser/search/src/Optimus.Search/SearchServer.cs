using System.Net;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Text.RegularExpressions;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;

namespace Optimus.Search;

public sealed record ServerOptions(int Port, string Token);

public sealed class SearchServer : IAsyncDisposable
{
    private readonly WebApplication application;
    private readonly ServiceCertificate certificate;
    public string Address { get; }
    private SearchServer(WebApplication application, string address, ServiceCertificate certificate) { this.application = application; Address = address; this.certificate = certificate; }
    public static async Task<SearchServer> StartAsync(ServerOptions options, LocalSearchIndex index, SearxSearchProvider? provider = null, CancellationToken cancellationToken = default)
    {
        if (options.Port is < 0 or > 65535 || !TokenStore.IsValid(options.Token)) throw new ArgumentException("Invalid service configuration.");
        var certificate = new ServiceCertificate(options.Token);
        var builder = WebApplication.CreateSlimBuilder(new WebApplicationOptions { Args = [], ApplicationName = typeof(SearchServer).Assembly.GetName().Name });
        builder.Configuration.Sources.Clear();
        builder.Logging.ClearProviders();
        builder.WebHost.ConfigureKestrel(kestrel => { kestrel.AddServerHeader = false; kestrel.Listen(IPAddress.Loopback, options.Port, listener => listener.UseHttps(tls => tls.ServerCertificateSelector = (connection, _) => certificate.ForPort(((IPEndPoint)connection!.LocalEndPoint!).Port))); kestrel.Limits.MaxRequestBodySize = 0; });
        builder.Services.ConfigureHttpJsonOptions(json => json.SerializerOptions.DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull);
        var app = builder.Build();
        var actualPort = options.Port;
        app.Run(async context => {
            context.Response.Headers.CacheControl = "no-store";
            context.Response.Headers.XContentTypeOptions = "nosniff";
            context.Response.Headers["Referrer-Policy"] = "no-referrer";
            async Task Error(int status, string error, string message, string scope = "web")
            {
                context.Response.StatusCode = status;
                await context.Response.WriteAsJsonAsync(new SearchResponse("", [], new(1, scope, provider != null, index.DocumentCount), error, message), context.RequestAborted);
            }
            if (context.Request.Headers.ContainsKey("Origin") || context.Request.Host.Value != $"127.0.0.1:{actualPort}") { await Error(403, "request-forbidden", "Request is not permitted."); return; }
            if (context.Request.Path != "/health" && context.Request.Path != "/search") { await Error(404, "not-found", "Endpoint not found."); return; }
            if (context.Request.Method != "GET") { context.Response.Headers.Allow = "GET"; await Error(405, "method-not-allowed", "Method is not permitted."); return; }
            if (context.Request.Path == "/health")
            {
                if (context.Request.Headers.TryGetValue("X-Optimus-Nonce", out var nonce))
                {
                    if (nonce.Count != 1 || !TokenStore.IsValid(nonce[0]))
                    {
                        context.Response.StatusCode = 400;
                        await context.Response.WriteAsJsonAsync(new { error = "invalid-request", message = "Invalid request." }, context.RequestAborted);
                        return;
                    }
                    // Bind possession to this listener, never a port supplied in an arbitrary Host header.
                    var message = $"OptimusSearch/v1|127.0.0.1:{context.Connection.LocalPort}|{nonce[0]}";
                    context.Response.Headers["X-Optimus-Proof"] = Convert.ToHexStringLower(HMACSHA256.HashData(Encoding.ASCII.GetBytes(options.Token), Encoding.ASCII.GetBytes(message)));
                }
                await context.Response.WriteAsJsonAsync(new { name = "OptimusSearch", version = 1 }, context.RequestAborted);
                return;
            }
            var authorization = context.Request.Headers.Authorization;
            if (authorization.Count != 1 || !authorization[0]!.StartsWith("Bearer ", StringComparison.Ordinal) || !TokenStore.Matches(options.Token, authorization[0]![7..])) { await Error(401, "unauthorized", "Authentication required."); return; }
            var query = context.Request.Query;
            string? Single(string name) => query.TryGetValue(name, out var value) && value.Count == 1 ? value[0] : null;
            var text = Single("q"); var scope = Single("scope"); var language = Single("language");
            if (Single("format") != "json" || !SearchValidation.ValidQuery(text) || scope is not ("web" or "index") || language == null
                || !Regex.IsMatch(language, @"\A[a-zA-Z]{2,3}(?:-[a-zA-Z]{2})?\z", RegexOptions.CultureInvariant)) { await Error(400, "invalid-query", "Invalid search request."); return; }
            if (scope == "index") { await context.Response.WriteAsJsonAsync(new SearchResponse(text!, index.Search(text!), new(1, scope, provider != null, index.DocumentCount)), context.RequestAborted); return; }
            if (provider == null) { await Error(503, "web-not-configured", "Web search is not configured.", scope); return; }
            try
            {
                var results = await provider.SearchAsync(text!, language, context.RequestAborted);
                context.RequestAborted.ThrowIfCancellationRequested();
                await context.Response.WriteAsJsonAsync(new SearchResponse(text!, results, new(1, scope, true, index.DocumentCount)), context.RequestAborted);
            }
            catch (SearchProviderException ex) { await Error(ex.TimedOut ? 504 : 502, ex.TimedOut ? "upstream-timeout" : "upstream-failed", ex.TimedOut ? "Web search timed out." : "Web search failed.", scope); }
            catch (OperationCanceledException) when (context.RequestAborted.IsCancellationRequested) { context.Abort(); }
        });
        try
        {
            await app.StartAsync(cancellationToken);
            var address = app.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>()!.Addresses.Single();
            actualPort = new Uri(address).Port;
            return new SearchServer(app, address, certificate);
        }
        catch { await app.DisposeAsync(); certificate.Dispose(); throw; }
    }
    public Task WaitForShutdownAsync(CancellationToken cancellationToken = default) => application.WaitForShutdownAsync(cancellationToken);
    public async ValueTask DisposeAsync() { try { await application.StopAsync(); await application.DisposeAsync(); } finally { certificate.Dispose(); } }
}
