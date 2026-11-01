using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

[assembly: System.Runtime.CompilerServices.InternalsVisibleTo("Optimus.Search.Tests")]

namespace Optimus.Core;

public readonly record struct SearchHostConnection(OptimusSearchTarget Target, string? Error, string? WebError = null)
{
    public string? GetError(OptimusSearchScope scope) => Error ?? (scope == OptimusSearchScope.Web ? WebError ?? (OptimusSearchService.IsValidToken(Target.ExpectedSpkiSha256) ? null : "No se confirmó la identidad del servicio iniciado por esta ventana. El índice local sigue disponible.") : null);
}

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
    private Task<string?>? ownedSpki;
    private bool disposed, independent;
    private WebSearchConfiguration upstream;
    private long configurationRevision;
    public bool OwnsProcess { get { lock (sync) return owned is { HasExited: false }; } }

    public static ProcessStartInfo CreateStartInfo(string applicationDirectory, string? upstream, string tokenPath)
        => CreateStartInfo(applicationDirectory, LegacyConfiguration(upstream), tokenPath);

    public static ProcessStartInfo CreateStartInfo(string applicationDirectory, WebSearchConfiguration configuration, string tokenPath)
    {
        var start = new ProcessStartInfo(Path.Combine(Path.GetFullPath(applicationDirectory), "Search", "Optimus.SearchHost.exe"))
        { UseShellExecute = false, CreateNoWindow = true, RedirectStandardInput = true, RedirectStandardOutput = true, WorkingDirectory = Path.GetFullPath(applicationDirectory) };
        start.ArgumentList.Add("--token-file"); start.ArgumentList.Add(tokenPath);
        if (configuration.Provider == WebProvider.Searx) { start.ArgumentList.Add("--searx-url"); start.ArgumentList.Add(configuration.Endpoint!); }
        if (configuration.Provider == WebProvider.Mwmbl) { start.ArgumentList.Add("--web-provider"); start.ArgumentList.Add("mwmbl"); }
        start.ArgumentList.Add("--owner-stdin"); start.ArgumentList.Add("true");
        start.ArgumentList.Add("--owner-identity-stdout"); start.ArgumentList.Add("true");
        return start;
    }

    private static WebSearchConfiguration LegacyConfiguration(string? endpoint) => new(endpoint is null ? WebProvider.None : WebProvider.Searx, endpoint);

    public string ConfigureUpstream(string? endpoint) => ConfigureUpstream(LegacyConfiguration(endpoint));

    public string ConfigureUpstream(WebSearchConfiguration configuration)
    {
        lock (sync)
        {
            if (disposed) return "Optimus Search está cerrado.";
            if (upstream == configuration && ShutdownError is null) return independent ? IndependentWebError : "Solo el servicio iniciado por Optimus usará estos ajustes. Un servicio independiente requiere configurarse y reiniciarse aparte.";
            if (!StopOwned()) return ShutdownError!;
            upstream = configuration;
            configurationRevision++;
            return independent ? IndependentWebError
                : "El servicio iniciado por Optimus usará estos ajustes al buscar. Un servicio independiente requiere configurarse y reiniciarse aparte.";
        }
    }

    private const string IndependentWebError = "La fuente del servicio independiente no está confirmada. El índice local sigue disponible. Para Web, usa la ventana que inició ese servicio o ciérralo desde su origen y vuelve a buscar.";

    public Task<SearchHostConnection> ConnectAsync(string? endpoint, CancellationToken cancellationToken)
    {
        cancellationToken.ThrowIfCancellationRequested();
        if (endpoint is not null && !OptimusSearchService.IsValidEndpoint(endpoint))
            return Task.FromResult(new SearchHostConnection(new(OptimusSearchScope.Web, null, null), "El servidor SearXNG del operador no es válido."));
        return ConnectAsync(LegacyConfiguration(endpoint), OptimusSearchScope.Index, cancellationToken);
    }

    public Task<SearchHostConnection> ConnectAsync(WebSearchConfiguration configuration, CancellationToken cancellationToken)
        => ConnectAsync(configuration, OptimusSearchScope.Web, cancellationToken);

    public async Task<SearchHostConnection> ConnectAsync(WebSearchConfiguration configuration, OptimusSearchScope scope, CancellationToken cancellationToken)
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
            // Existing invalid files fail closed; only the host creates the token.
            if (File.Exists(tokenPath) && ReadToken() is null) return Failure("El token de perfil de Optimus Search no es válido. No se inició el servicio.");
            ConfigureUpstream(configuration);
            long revision;
            lock (sync)
            {
                if (ShutdownError is {} failure) return Failure(failure);
                if (upstream != configuration) return Failure("La configuración de búsqueda cambió. Vuelve a buscar.");
                revision = configurationRevision;
            }
            var bearer = await VerifiedTokenAsync(token).ConfigureAwait(false);
            lock (sync) if (configurationRevision != revision) return Failure("La configuración de búsqueda cambió. Vuelve a buscar.");
            if (bearer is not null)
            {
                lock (sync) independent = owned is null || owned.HasExited;
            }
            else
            {
                lock (sync)
                {
                    token.ThrowIfCancellationRequested();
                    if (disposed) throw new OperationCanceledException(token);
                    if (configurationRevision != revision) return Failure("La configuración de búsqueda cambió. Vuelve a buscar.");
                    if (owned is null || owned.HasExited)
                    {
                        if (!StopOwned()) return Failure(ShutdownError!);
                        var start = CreateStartInfo(applicationDirectory, upstream, tokenPath);
                        if (!File.Exists(start.FileName)) return Failure("No se encontró el servicio incluido en Search. Reinstala el paquete de Optimus.");
                        owned = startProcess(start);
                        ownedSpki = owned.ReadOwnerSpkiAsync(lifetime.Token);
                        startedHere = owned is not null;
                        independent = false;
                    }
                }
                // Cold startup shares the existing global deadline, including token creation.
                while (true)
                {
                    token.ThrowIfCancellationRequested();
                    lock (sync) if (configurationRevision != revision) return Failure("La configuración de búsqueda cambió. Vuelve a buscar.");
                    bearer = await VerifiedTokenAsync(token).ConfigureAwait(false);
                    if (bearer is not null) break;
                    await Task.Delay(100, token).ConfigureAwait(false);
                }
            }
            token.ThrowIfCancellationRequested();
            Task<string?>? identity;
            lock (sync) identity = owned is { HasExited: false } ? ownedSpki : null;
            string? pin = null;
            if (identity is not null && (scope == OptimusSearchScope.Web && configuration.Provider != WebProvider.None || identity.IsCompletedSuccessfully))
                pin = await identity.WaitAsync(token).ConfigureAwait(false);
            if (!OptimusSearchService.IsValidToken(pin)) pin = null;
            // Return only the token snapshot whose possession was proved, never a later profile-file value.
            lock (sync)
            {
                if (configurationRevision != revision) return Failure("La configuración de búsqueda cambió. Vuelve a buscar.");
                if (ShutdownError is {} failure) return Failure(failure);
                var webError = configuration.Provider == WebProvider.None ? "La búsqueda Web está desactivada. Elige una fuente en Ajustes · Privacidad y búsqueda. El índice local sigue disponible."
                    : owned is { HasExited: false } && ReferenceEquals(identity, ownedSpki) && pin is not null ? null : IndependentWebError;
                return bearer is null ? Failure("No se pudo leer un token válido del perfil para el servicio local.") : new(new(OptimusSearchScope.Web, null, bearer, pin), null, webError);
            }
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
            // Even an exited child must confirm normal completion rather than a crash/forced exit.
            owned.Stop();
            owned.Dispose(); owned = null; ownedSpki = null; ShutdownError = null; return true;
        }
        catch (Exception ex) when (ex is InvalidOperationException or System.ComponentModel.Win32Exception)
        {
            // Retain the handle so failure cannot permit a second process or pretend reconfiguration.
            ShutdownError = "No se pudo detener normalmente y confirmar la limpieza del servicio de búsqueda de Optimus. La nueva configuración no se aplicó; cierra el servicio y reinicia Optimus.";
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
    Task<string?> ReadOwnerSpkiAsync(CancellationToken token) => Task.FromResult<string?>(null);
    void Stop();
}
internal sealed class SystemSearchHostProcess(Process process) : ISearchHostProcess
{
    private bool forcedTermination;
    public bool HasExited => process.HasExited;
    public async Task<string?> ReadOwnerSpkiAsync(CancellationToken token)
    {
        // Bound the private report before allocating a complete line. The host emits
        // one startup record, with neither bearer, query nor filesystem paths.
        var text = new StringBuilder(128); var buffer = new char[1];
        try
        {
            while (text.Length < 128)
            {
                if (await process.StandardOutput.ReadAsync(buffer.AsMemory(), token).ConfigureAwait(false) == 0) return null;
                if (buffer[0] == '\n') return ParseOwnerIdentity(text.ToString().TrimEnd('\r'));
                text.Append(buffer[0]);
            }
        }
        catch (Exception ex) when (ex is IOException or InvalidOperationException or OperationCanceledException or ObjectDisposedException) { }
        return null;
    }
    internal static string? ParseOwnerIdentity(string line)
    {
        var parts = line.Split('|');
        return parts.Length == 3 && parts[0] == "OptimusSearch owner/1" && parts[1] == "17831" && OptimusSearchService.IsValidToken(parts[2]) ? parts[2] : null;
    }
    public void Stop()
    {
        if (!process.HasExited)
        {
            // Only the launcher-created pipe is closed. No network shutdown surface is exposed.
            try { process.StandardInput.Close(); }
            catch (Exception ex) when (ex is IOException or InvalidOperationException) { }
            if (!process.WaitForExit(3000))
            {
                forcedTermination = true;
                process.Kill();
                if (!process.WaitForExit(1000)) throw new InvalidOperationException("No se confirmó el cierre del proceso de búsqueda.");
                throw new InvalidOperationException("El cierre forzado no confirma la limpieza de la identidad TLS.");
            }
        }
        if (forcedTermination || process.ExitCode != 0) throw new InvalidOperationException("El servicio no confirmó un cierre normal y su limpieza.");
    }
    public void Dispose() => process.Dispose();
}
