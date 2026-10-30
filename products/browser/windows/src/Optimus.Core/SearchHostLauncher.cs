using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

[assembly: System.Runtime.CompilerServices.InternalsVisibleTo("Optimus.Search.Tests")]

namespace Optimus.Core;

public readonly record struct SearchHostConnection(OptimusSearchTarget Target, string? Error);

/// <summary>One application-owned process; independent loopback services are never stopped.</summary>
public sealed class SearchHostLauncher : IDisposable
{
    private readonly Func<string, HttpClient> localClientFactory;
    private readonly string applicationDirectory, tokenPath;
    private readonly Func<ProcessStartInfo, ISearchHostProcess> startProcess;
    public SearchHostLauncher(HttpClient client, string applicationDirectory, string localApplicationData)
        : this(client, applicationDirectory, localApplicationData, null, LocalSearchTransport.CreateClient) { }
    internal SearchHostLauncher(HttpClient client, string applicationDirectory, string localApplicationData, Func<ProcessStartInfo, ISearchHostProcess>? startProcess = null, Func<string, HttpClient>? localClientFactory = null)
    {
        this.localClientFactory = localClientFactory ?? LocalSearchTransport.CreateClient; this.applicationDirectory = applicationDirectory;
        this.startProcess = startProcess ?? (start => new SystemSearchHostProcess(Process.Start(start) ?? throw new InvalidOperationException()));
        tokenPath = Path.Combine(localApplicationData, "Optimus", "Search", "service.token");
    }
    public string? ShutdownError { get; private set; }
    private readonly object sync = new();
    private readonly SemaphoreSlim connecting = new(1, 1);
    private readonly CancellationTokenSource lifetime = new();
    private ISearchHostProcess? owned;
    private bool disposed, independent;
    private string? upstream;
    public bool OwnsProcess { get { lock (sync) return owned is { HasExited: false }; } }

    public static ProcessStartInfo CreateStartInfo(string applicationDirectory, string? upstream, string tokenPath)
    {
        if (upstream is not null && !OptimusSearchService.IsValidEndpoint(upstream)) throw new ArgumentException("Servidor SearXNG no válido.");
        var start = new ProcessStartInfo(Path.Combine(Path.GetFullPath(applicationDirectory), "Search", "Optimus.SearchHost.exe"))
        { UseShellExecute = false, CreateNoWindow = true, WorkingDirectory = Path.GetFullPath(applicationDirectory) };
        start.ArgumentList.Add("--token-file"); start.ArgumentList.Add(tokenPath);
        if (upstream is not null) { start.ArgumentList.Add("--searx-url"); start.ArgumentList.Add(upstream); }
        return start;
    }

    public string ConfigureUpstream(string? endpoint)
    {
        lock (sync)
        {
            if (disposed) return "Optimus Search está cerrado.";
            if (upstream == endpoint && ShutdownError is null) return independent ? "El servicio es independiente: configura y reinicia ese servicio para aplicar el servidor Web." : "Solo el servicio iniciado por Optimus usará estos ajustes. Un servicio independiente requiere configurarse y reiniciarse aparte.";
            if (!StopOwned()) return ShutdownError!;
            upstream = endpoint;
            return independent ? "El servicio es independiente: configura y reinicia ese servicio para aplicar el servidor Web."
                : "El servicio iniciado por Optimus usará estos ajustes al buscar. Un servicio independiente requiere configurarse y reiniciarse aparte.";
        }
    }

    public async Task<SearchHostConnection> ConnectAsync(string? endpoint, CancellationToken cancellationToken)
    {
        using var request = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, lifetime.Token);
        request.CancelAfter(TimeSpan.FromSeconds(4));
        var token = request.Token;
        await connecting.WaitAsync(token).ConfigureAwait(false);
        bool startedHere = false;
        SearchHostConnection Failure(string error) => new(new(OptimusSearchScope.Web, null, null), error);
        try
        {
            token.ThrowIfCancellationRequested();
            if (endpoint is not null && !OptimusSearchService.IsValidEndpoint(endpoint)) return Failure("El servidor SearXNG del operador no es válido.");
            // Existing invalid files fail closed; only the host creates the token.
            if (File.Exists(tokenPath) && ReadToken() is null) return Failure("El token de perfil de Optimus Search no es válido. No se inició el servicio.");
            ConfigureUpstream(endpoint);
            lock (sync) if (ShutdownError is {} failure) return Failure(failure);
            var bearer = await VerifiedTokenAsync(token).ConfigureAwait(false);
            if (bearer is not null)
            {
                lock (sync) independent = owned is null;
            }
            else
            {
                lock (sync)
                {
                    token.ThrowIfCancellationRequested();
                    if (disposed) throw new OperationCanceledException(token);
                    if (owned is null || owned.HasExited)
                    {
                        StopOwned();
                        var start = CreateStartInfo(applicationDirectory, upstream, tokenPath);
                        if (!File.Exists(start.FileName)) return Failure("No se encontró el servicio incluido en Search. Reinstala el paquete de Optimus.");
                        owned = startProcess(start);
                        startedHere = owned is not null;
                        independent = false;
                    }
                }
                // Cold startup shares the existing global deadline, including token creation.
                while (true)
                {
                    token.ThrowIfCancellationRequested();
                    bearer = await VerifiedTokenAsync(token).ConfigureAwait(false);
                    if (bearer is not null) break;
                    await Task.Delay(100, token).ConfigureAwait(false);
                }
            }
            token.ThrowIfCancellationRequested();
            // Return only the token snapshot whose possession was proved, never a later profile-file value.
            return bearer is null ? Failure("No se pudo leer un token válido del perfil para el servicio local.") : new(new(OptimusSearchScope.Web, null, bearer), null);
        }
        catch (OperationCanceledException) when (cancellationToken.IsCancellationRequested || lifetime.IsCancellationRequested)
        { lock (sync) if (startedHere) StopOwned(); throw; }
        catch (OperationCanceledException)
        { lock (sync) if (startedHere) StopOwned(); return Failure("El servicio local de búsqueda no respondió a tiempo."); }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or System.ComponentModel.Win32Exception or InvalidOperationException)
        { lock (sync) if (startedHere) StopOwned(); return Failure("No se pudo preparar el servicio local de búsqueda."); }
        finally { connecting.Release(); }
    }

    private string? ReadToken()
    {
        try
        {
            using var file = new FileStream(tokenPath, FileMode.Open, FileAccess.Read, FileShare.Read);
            if (file.Length != 64) return null;
            Span<byte> bytes = stackalloc byte[64]; file.ReadExactly(bytes);
            var value = System.Text.Encoding.ASCII.GetString(bytes);
            return OptimusSearchService.IsValidToken(value) ? value : null;
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException) { return null; }
    }

    private async Task<string?> VerifiedTokenAsync(CancellationToken token)
    {
        var bearer = ReadToken();
        if (bearer is null) return null;
        try
        {
            using var deadline = CancellationTokenSource.CreateLinkedTokenSource(token);
            deadline.CancelAfter(TimeSpan.FromMilliseconds(300));
            var nonce = Convert.ToHexStringLower(RandomNumberGenerator.GetBytes(32));
            using var request = new HttpRequestMessage(HttpMethod.Get, OptimusSearchTarget.LocalEndpoint + "/health");
            request.Headers.Add("X-Optimus-Nonce", nonce);
            using var client = localClientFactory(bearer);
            using var response = await client.SendAsync(request, HttpCompletionOption.ResponseHeadersRead, deadline.Token).ConfigureAwait(false);
            if (!response.IsSuccessStatusCode || response.Content.Headers.ContentLength > 1024
                || !response.Headers.TryGetValues("X-Optimus-Proof", out var values)) return null;
            var proofs = values.ToArray();
            if (proofs.Length != 1 || !OptimusSearchService.IsValidToken(proofs[0])) return null;
            var message = $"OptimusSearch/v1|127.0.0.1:{request.RequestUri!.Port}|{nonce}";
            var expected = HMACSHA256.HashData(Encoding.ASCII.GetBytes(bearer), Encoding.ASCII.GetBytes(message));
            if (!CryptographicOperations.FixedTimeEquals(expected, Convert.FromHexString(proofs[0]))) return null;
            await using var stream = await response.Content.ReadAsStreamAsync(deadline.Token).ConfigureAwait(false);
            var bytes = new byte[1025]; int count = 0, read;
            while (count < bytes.Length && (read = await stream.ReadAsync(bytes.AsMemory(count), deadline.Token).ConfigureAwait(false)) != 0) count += read;
            if (count > 1024) return null;
            using var document = JsonDocument.Parse(bytes.AsMemory(0, count)); var root = document.RootElement;
            return root.ValueKind == JsonValueKind.Object && root.TryGetProperty("name", out var name) && name.ValueKind == JsonValueKind.String && name.GetString() == "OptimusSearch"
                && root.TryGetProperty("version", out var version) && version.ValueKind == JsonValueKind.Number && version.TryGetInt32(out var v) && v == 1 ? bearer : null;
        }
        catch (OperationCanceledException) when (!token.IsCancellationRequested) { return null; }
        catch (Exception ex) when (ex is HttpRequestException or IOException or JsonException) { return null; }
    }

    private bool StopOwned()
    {
        if (owned is null) { ShutdownError = null; return true; }
        try
        {
            if (!owned.HasExited) owned.Stop();
            owned.Dispose(); owned = null; ShutdownError = null; return true;
        }
        catch (Exception ex) when (ex is InvalidOperationException or System.ComponentModel.Win32Exception)
        {
            // Retain the handle so failure cannot permit a second process or pretend reconfiguration.
            ShutdownError = "No se pudo detener el servicio de búsqueda de Optimus. La nueva configuración no se aplicó; cierra el servicio y reinicia Optimus.";
            return false;
        }
    }
    public void Dispose()
    {
        lock (sync) { if (!disposed) { disposed = true; lifetime.Cancel(); } StopOwned(); }
        // In-flight callers still own linked tokens and the semaphore until their finally runs.
    }
}

// Only the OS boundary is replaceable in tests; launcher decisions run unchanged.
internal interface ISearchHostProcess : IDisposable
{
    bool HasExited { get; }
    void Stop();
}
internal sealed class SystemSearchHostProcess(Process process) : ISearchHostProcess
{
    public bool HasExited => process.HasExited;
    public void Stop()
    {
        if (process.HasExited) return;
        process.Kill();
        if (!process.WaitForExit(1000)) throw new InvalidOperationException("No se confirmó el cierre del proceso de búsqueda.");
    }
    public void Dispose() => process.Dispose();
}
