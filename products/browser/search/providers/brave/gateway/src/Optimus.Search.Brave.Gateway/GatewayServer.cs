using System.Net;
using System.Net.Http.Headers;
using System.Text.Json;
using Microsoft.AspNetCore.Hosting.Server;
using Microsoft.AspNetCore.Hosting.Server.Features;

namespace Optimus.Search.Brave.Gateway;

/// <summary>Explicit loopback-only candidate. No production executable or runtime registration.</summary>
public sealed class GatewayServer : IAsyncDisposable
{
    private readonly WebApplication application;
    private readonly PilotQuota quota;
    public string Address { get; }
    private GatewayServer(WebApplication application, PilotQuota quota, string address) { this.application = application; this.quota = quota; Address = address; }

    public static async Task<GatewayServer> StartAsync(string credentialPath, string quotaPath,
        Func<string,string,CancellationToken,Task<IReadOnlyList<BraveSearchResult>>> search, CancellationToken cancellationToken = default)
    {
        ArgumentNullException.ThrowIfNull(search);
        var quota = PilotQuota.Open(quotaPath);
        WebApplication? app = null;
        try
        {
            var registry = new CredentialRegistry(Path.GetFullPath(credentialPath));
            var admission = new SemaphoreSlim(1, 1);
            var builder = WebApplication.CreateSlimBuilder(new WebApplicationOptions { Args = [], ApplicationName = typeof(GatewayServer).Assembly.GetName().Name, EnvironmentName = Environments.Production });
            builder.Configuration.Sources.Clear(); builder.Logging.ClearProviders();
            builder.WebHost.ConfigureKestrel(kestrel => {
                kestrel.AddServerHeader = false; kestrel.Listen(IPAddress.Loopback, 0);
                kestrel.Limits.MaxRequestBodySize = 4096; kestrel.Limits.MaxConcurrentConnections = 32;
                kestrel.Limits.MaxRequestLineSize = 1024; kestrel.Limits.MaxRequestHeadersTotalSize = 8192;
                kestrel.Limits.RequestHeadersTimeout = TimeSpan.FromSeconds(2);
            });
            app = builder.Build(); var actualPort = 0;
            app.Run(async context => {
                context.Response.Headers.CacheControl = "no-store";
                context.Response.Headers.XContentTypeOptions = "nosniff";
                context.Response.Headers["Referrer-Policy"] = "no-referrer";
                async Task Error(int status, string error) { context.Response.StatusCode = status; await context.Response.WriteAsJsonAsync(new { error }, context.RequestAborted); }
                if (context.Request.Headers.ContainsKey("Origin") || context.Request.Host.Value != $"127.0.0.1:{actualPort}") { await Error(403, "request-forbidden"); return; }
                if (context.Request.Path != "/v1/web/search") { await Error(404, "not-found"); return; }
                if (context.Request.Method != "POST") { context.Response.Headers.Allow = "POST"; await Error(405, "method-not-allowed"); return; }
                var authorization = context.Request.Headers.Authorization;
                if (authorization.Count != 1 || !authorization[0]!.StartsWith("Bearer ", StringComparison.Ordinal) || !registry.Allows(authorization[0]![7..])) { await Error(401, "unauthorized"); return; }
                if (context.Request.QueryString.HasValue) { await Error(400, "invalid-request"); return; }
                if (!MediaTypeHeaderValue.TryParse(context.Request.ContentType, out var media) || media.MediaType != "application/json"
                    || media.CharSet != null && !media.CharSet.Trim('"').Equals("utf-8", StringComparison.OrdinalIgnoreCase)) { await Error(415, "unsupported-media-type"); return; }
                if (context.Request.ContentLength > 4096) { await Error(413, "request-too-large"); return; }
                if (!await admission.WaitAsync(0, context.RequestAborted)) { await Error(429, "gateway-busy"); return; }
                var providerStarted = false;
                var reservationStarted = false;
                var providerCompleted = false;
                try
                {
                    using var bodyDeadline = CancellationTokenSource.CreateLinkedTokenSource(context.RequestAborted, app.Lifetime.ApplicationStopping);
                    bodyDeadline.CancelAfter(TimeSpan.FromSeconds(2));
                    using var buffer = new MemoryStream(); var chunk = new byte[1024];
                    while (true)
                    {
                        var read = await context.Request.Body.ReadAsync(chunk.AsMemory(0, (int)Math.Min(chunk.Length, 4097 - buffer.Length)), bodyDeadline.Token);
                        if (read == 0) break;
                        if (buffer.Length + read > 4096) { await Error(413, "request-too-large"); return; }
                        buffer.Write(chunk, 0, read);
                    }
                    using var document = StrictInput.Parse(buffer.GetBuffer().AsMemory(0, (int)buffer.Length)); var root = document.RootElement;
                    if (!StrictInput.Fields(root, "query", "language")) { await Error(400, "invalid-request"); return; }
                    var query = root.GetProperty("query").GetString(); var language = root.GetProperty("language").GetString();
                    if (!StrictInput.Query(query) || !StrictInput.Language(language)) { await Error(400, "invalid-request"); return; }
                    bodyDeadline.Token.ThrowIfCancellationRequested();
                    if (!quota.TryBeginCall()) { await Error(429, "quota-exhausted"); return; }
                    reservationStarted = true;
                    using var upstreamDeadline = CancellationTokenSource.CreateLinkedTokenSource(context.RequestAborted, app.Lifetime.ApplicationStopping);
                    upstreamDeadline.CancelAfter(TimeSpan.FromSeconds(10));
                    providerStarted = true;
                    Task<IReadOnlyList<BraveSearchResult>> operation;
                    try { operation = search(query!, language!, upstreamDeadline.Token); }
                    catch { providerCompleted = true; throw; }
                    IReadOnlyList<BraveSearchResult> results;
                    try { results = await operation.WaitAsync(upstreamDeadline.Token); }
                    catch (OperationCanceledException)
                    {
                        // Allow bounded cooperative cleanup while the admission remains held.
                        if (!operation.IsCompleted)
                            try { await operation.WaitAsync(TimeSpan.FromMilliseconds(250)); } catch (Exception) { }
                        if (!operation.IsCompleted)
                        {
                            quota.StopUncertainPilot();
                            _ = operation.ContinueWith(task => { _ = task.Exception; }, CancellationToken.None, TaskContinuationOptions.OnlyOnFaulted | TaskContinuationOptions.ExecuteSynchronously, TaskScheduler.Default);
                        }
                        throw;
                    }
                    finally { providerCompleted = operation.IsCompleted; }
                    upstreamDeadline.Token.ThrowIfCancellationRequested();
                    if (results.Count > 20 || results.Any(result => result.Source != "Brave")) throw new BraveSearchException(BraveSearchFailure.InvalidResponse);
                    var response = JsonSerializer.SerializeToUtf8Bytes(new { version = 1, source = "Brave", results }, new JsonSerializerOptions(JsonSerializerDefaults.Web));
                    if (response.Length > 256 * 1024) throw new BraveSearchException(BraveSearchFailure.InvalidResponse);
                    context.Response.ContentType = "application/json; charset=utf-8";
                    await context.Response.Body.WriteAsync(response, context.RequestAborted);
                }
                catch (BraveSearchException ex) { await Error(ex.Failure == BraveSearchFailure.Timeout ? 504 : 502, ex.Failure == BraveSearchFailure.Timeout ? "upstream-timeout" : "upstream-failed"); }
                catch (OperationCanceledException) when (context.RequestAborted.IsCancellationRequested || app.Lifetime.ApplicationStopping.IsCancellationRequested) { context.Abort(); }
                catch (OperationCanceledException) { await Error(504, "request-timeout"); }
                catch (BadHttpRequestException ex) { await Error(ex.StatusCode == 413 ? 413 : 400, ex.StatusCode == 413 ? "request-too-large" : "invalid-request"); }
                catch (Exception ex) when (!providerStarted && ex is JsonException or InvalidOperationException or ArgumentException) { await Error(400, "invalid-request"); }
                catch (IOException) when (!providerStarted) { await Error(503, "quota-unavailable"); }
                catch (Exception) { await Error(502, "upstream-failed"); }
                finally
                {
                    try
                    {
                        if (reservationStarted && providerCompleted) quota.CompleteCall();
                    }
                    catch (IOException) { context.Abort(); }
                    finally { admission.Release(); }
                }
            });
            await app.StartAsync(cancellationToken);
            var address = app.Services.GetRequiredService<IServer>().Features.Get<IServerAddressesFeature>()!.Addresses.Single();
            actualPort = new Uri(address).Port;
            return new(app, quota, address);
        }
        catch { try { if (app != null) await app.DisposeAsync(); } finally { quota.Dispose(); } throw; }
    }
    public async ValueTask DisposeAsync()
    {
        try { using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(5)); await application.StopAsync(timeout.Token); }
        finally { try { await application.DisposeAsync(); } finally { quota.Dispose(); } }
    }
}
