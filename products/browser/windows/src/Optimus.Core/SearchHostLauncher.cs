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
    private string? upstream, indexFile;
    public bool OwnsProcess { get { lock (sync) return owned is { HasExited: false }; } }
    internal bool CanRemoveUnusedIndex { get { lock (sync) return ShutdownError is null; } }
    internal bool HasConfirmedShutdown { get { lock (sync) return owned is null && ShutdownError is null; } }

    public static ProcessStartInfo CreateStartInfo(string applicationDirectory, string? upstream, string tokenPath, string? indexFile = null)
    {
        if (upstream is not null && !OptimusSearchService.IsValidEndpoint(upstream)) throw new ArgumentException("Servidor SearXNG no válido.");
        var start = new ProcessStartInfo(Path.Combine(Path.GetFullPath(applicationDirectory), "Search", "Optimus.SearchHost.exe"))
        { UseShellExecute = false, CreateNoWindow = true, RedirectStandardInput = true, RedirectStandardOutput = true, WorkingDirectory = Path.GetFullPath(applicationDirectory) };
        start.ArgumentList.Add("--token-file"); start.ArgumentList.Add(tokenPath);
        if (upstream is not null) { start.ArgumentList.Add("--searx-url"); start.ArgumentList.Add(upstream); }
        if (indexFile is not null) { if (!Path.IsPathFullyQualified(indexFile) || indexFile.Any(char.IsControl)) throw new ArgumentException("Índice no válido."); start.ArgumentList.Add("--index-file"); start.ArgumentList.Add(indexFile); }
        start.ArgumentList.Add("--owner-stdin"); start.ArgumentList.Add("true");
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
        await connecting.WaitAsync(request.Token).ConfigureAwait(false);
        try { return await ConnectLockedAsync(endpoint, request.Token, cancellationToken).ConfigureAwait(false); }
        finally { connecting.Release(); }
    }

    internal async Task<string?> SelectIndexAsync(string? candidate, CancellationToken cancellationToken)
    {
        using var request = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, lifetime.Token);
        request.CancelAfter(TimeSpan.FromSeconds(8));
        var token = request.Token;
        bool acquired = false, changed = false, committed = false;
        string? previous = null;
        try
        {
            await connecting.WaitAsync(token).ConfigureAwait(false); acquired = true;
            lock (sync)
            {
                token.ThrowIfCancellationRequested();
                if (disposed) throw new OperationCanceledException(token);
                previous = indexFile;
            }
            bool hasOwned; lock (sync) hasOwned = owned is not null;
            if (!hasOwned && await VerifiedTokenAsync(token).ConfigureAwait(false) is not null)
                return "El servicio de búsqueda es independiente. Ciérralo por su vía habitual antes de cargar el piloto.";
            lock (sync)
            {
                token.ThrowIfCancellationRequested();
                if (disposed) throw new OperationCanceledException(token);
                if (!StopOwned()) return ShutdownError;
                indexFile = candidate; changed = true; independent = false;
            }
            var connection = await ConnectLockedAsync(upstream, token, cancellationToken, allowIndependent: false).ConfigureAwait(false);
            if (connection.Error is not null) return connection.Error;
            lock (sync) { token.ThrowIfCancellationRequested(); if (disposed) throw new OperationCanceledException(token); committed = true; }
            return null;
        }
        catch (OperationCanceledException) { return "No se pudo cambiar el catálogo. Se conserva la selección anterior."; }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or ArgumentException or InvalidOperationException)
        { return "No se pudo cambiar el catálogo. Se conserva la selección anterior."; }
        finally
        {
            if (changed && !committed) lock (sync) { StopOwned(); indexFile = previous; }
            if (acquired) connecting.Release();
        }
    }

    private async Task<SearchHostConnection> ConnectLockedAsync(string? endpoint, CancellationToken cancellationToken, CancellationToken callerToken, bool allowIndependent = true)
    {
        using var request = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, lifetime.Token);
        request.CancelAfter(TimeSpan.FromSeconds(4));
        var token = request.Token;
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
                lock (sync)
                {
                    if ((!allowIndependent || indexFile is not null) && owned is not { HasExited: false, Ready: true })
                        return Failure("Otro servicio responde en el puerto local. No se confirmó el catálogo seleccionado; cierra ese servicio por su vía habitual.");
                    independent = owned is null;
                }
            }
            else
            {
                lock (sync)
                {
                    token.ThrowIfCancellationRequested();
                    if (disposed) throw new OperationCanceledException(token);
                    if (owned is null || owned.HasExited)
                    {
                        if (!StopOwned()) return Failure(ShutdownError!);
                        var start = CreateStartInfo(applicationDirectory, upstream, tokenPath, indexFile);
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
                    lock (sync) if (bearer is not null && owned is { HasExited: false, Ready: true }) break;
                    await Task.Delay(100, token).ConfigureAwait(false);
                }
            }
            token.ThrowIfCancellationRequested();
            // Return only the token snapshot whose possession was proved, never a later profile-file value.
            return bearer is null ? Failure("No se pudo leer un token válido del perfil para el servicio local.") : new(new(OptimusSearchScope.Web, null, bearer), null);
        }
        catch (OperationCanceledException) when (callerToken.IsCancellationRequested || lifetime.IsCancellationRequested)
        { lock (sync) if (startedHere) StopOwned(); throw; }
        catch (OperationCanceledException)
        { lock (sync) if (startedHere) StopOwned(); return Failure("El servicio local de búsqueda no respondió a tiempo."); }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or System.ComponentModel.Win32Exception or InvalidOperationException)
        { lock (sync) if (startedHere) StopOwned(); return Failure("No se pudo preparar el servicio local de búsqueda."); }
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
            owned.Dispose(); owned = null; ShutdownError = null; return true;
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
    bool Ready => !HasExited;
    void Stop();
}
internal sealed class SystemSearchHostProcess : ISearchHostProcess
{
    private readonly Process process;
    private int ready;
    public SystemSearchHostProcess(Process process)
    {
        this.process = process;
        _ = ObserveReadyAsync();
    }
    public bool Ready => Volatile.Read(ref ready) == 1 && !HasExited;
    private async Task ObserveReadyAsync()
    {
        try
        {
            // Existing fixed stdout marker is emitted only after this child's server has bound.
            var line = new char[64]; int count = 0;
            while (count < line.Length)
            {
                if (await process.StandardOutput.ReadAsync(line.AsMemory(count, 1)).ConfigureAwait(false) == 0) return;
                if (line[count++] != '\n') continue;
                if (new string(line, 0, count).TrimEnd('\r', '\n') == "OptimusSearch ready.") Volatile.Write(ref ready, 1);
                return;
            }
        }
        catch (Exception ex) when (ex is IOException or InvalidOperationException) { }
    }
    private bool forcedTermination;
    public bool HasExited => process.HasExited;
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
