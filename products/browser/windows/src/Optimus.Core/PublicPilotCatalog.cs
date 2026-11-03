using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Optimus.Core;

public readonly record struct PilotCatalogChange(bool Active, string? Error);

/// <summary>Explicit session-only selection of two fixed reviewed public assets.</summary>
public sealed class PublicPilotCatalog : IDisposable
{
    private const string CatalogHash = "8294911789f69f2c1262c80153ca0dddd6189e9a198b586f5fbb3beeb0d665ec";
    private const string ProvenanceHash = "5312f482daea11727c9c90a683bcf95dce587021aa6c63609b9038756eb05aae";
    private const string Failure = "No se pudo cargar el catálogo piloto. Se conserva el catálogo anterior.";
    private readonly SearchHostLauncher launcher;
    private readonly string applicationDirectory;
    private readonly Func<ProcessStartInfo, CancellationToken, Task<int>> importer;
    private readonly SemaphoreSlim changing = new(1, 1);
    private readonly CancellationTokenSource lifetime = new();
    private volatile bool active, disposed;
    private string? workspace;
    private readonly HashSet<string> workspaces = new(StringComparer.Ordinal);
    public bool IsActive => active;

    public PublicPilotCatalog(SearchHostLauncher launcher, string applicationDirectory)
        : this(launcher, applicationDirectory, RunImporterAsync) { }
    internal PublicPilotCatalog(SearchHostLauncher launcher, string applicationDirectory, Func<ProcessStartInfo, CancellationToken, Task<int>> importer)
    { this.launcher = launcher; this.applicationDirectory = Path.GetFullPath(applicationDirectory); this.importer = importer; }

    public async Task<PilotCatalogChange> SetActiveAsync(bool enabled, CancellationToken cancellationToken)
    {
        using var request = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, lifetime.Token);
        request.CancelAfter(TimeSpan.FromSeconds(15));
        var token = request.Token;
        bool acquired = false;
        string? candidate = null;
        try
        {
            await changing.WaitAsync(token).ConfigureAwait(false); acquired = true;
            token.ThrowIfCancellationRequested();
            if (disposed) throw new OperationCanceledException(token);
            if (!enabled && !active) return new(false, null);
            if (enabled)
            {
                // No directory discovery, user input or source download. Hash pins bind reviewed content.
                var catalog = ReadAsset("public-pilot-v0.1.json", CatalogHash);
                _ = ReadAsset("public-pilot-v0.1.provenance.json", ProvenanceHash);
                candidate = Directory.CreateTempSubdirectory("Optimus-public-pilot-").FullName;
                workspaces.Add(candidate);
                var input = Path.Combine(candidate, "catalog.json");
                var output = Path.Combine(candidate, "index.json");
                await File.WriteAllBytesAsync(input, catalog, token).ConfigureAwait(false);
                var start = new ProcessStartInfo(Path.Combine(applicationDirectory, "Search", "Optimus.SearchHost.exe"))
                { UseShellExecute = false, CreateNoWindow = true, WorkingDirectory = applicationDirectory };
                foreach (var value in new[] { "index", "--input", input, "--output", output }) start.ArgumentList.Add(value);
                using var deadline = CancellationTokenSource.CreateLinkedTokenSource(token);
                deadline.CancelAfter(TimeSpan.FromSeconds(5));
                if (await importer(start, deadline.Token).ConfigureAwait(false) != 0) return new(active, Failure);
                token.ThrowIfCancellationRequested();
                var info = new FileInfo(output);
                if (!info.Exists || info.Length is <= 0 or > 262144 || (info.Attributes & FileAttributes.ReparsePoint) != 0) return new(active, Failure);
                if (!MatchesReviewedCorpus(output, catalog)) return new(active, Failure);
            }
            token.ThrowIfCancellationRequested();
            var error = await launcher.SelectIndexAsync(enabled ? Path.Combine(candidate!, "index.json") : null, token).ConfigureAwait(false);
            if (error is not null) return new(active, error);
            // Launcher owns the committed selection. Closing cancels it before owned files are removed.
            var previous = workspace;
            workspace = candidate; candidate = null; active = enabled;
            Clean(previous);
            return new(active, null);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or ArgumentException or InvalidOperationException or OperationCanceledException or System.ComponentModel.Win32Exception or JsonException)
        { return new(active, Failure); }
        finally { if (launcher.CanRemoveUnusedIndex) Clean(candidate); if (acquired) changing.Release(); }
    }

    private byte[] ReadAsset(string name, string expectedHash)
    {
        var path = Path.Combine(applicationDirectory, "Search", "catalog", name);
        foreach (var directory in new[] { applicationDirectory, Path.Combine(applicationDirectory, "Search"), Path.GetDirectoryName(path)! })
            if ((File.GetAttributes(directory) & FileAttributes.ReparsePoint) != 0) throw new IOException();
        var attributes = File.GetAttributes(path);
        if ((attributes & (FileAttributes.ReparsePoint | FileAttributes.Directory)) != 0) throw new IOException();
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        if (stream.Length is <= 0 or > 262144) throw new IOException();
        var bytes = new byte[checked((int)stream.Length)]; stream.ReadExactly(bytes);
        var text = new UTF8Encoding(false, true).GetString(bytes).Replace("\r\n", "\n", StringComparison.Ordinal);
        var normalized = Encoding.UTF8.GetBytes(text);
        if (Convert.ToHexStringLower(SHA256.HashData(normalized)) != expectedHash) throw new IOException();
        return normalized;
    }

    private static bool MatchesReviewedCorpus(string output, byte[] reviewed)
    {
        using var stream = new FileStream(output, FileMode.Open, FileAccess.Read, FileShare.Read);
        if (stream.Length is <= 0 or > 262144) return false;
        var bytes = new byte[checked((int)stream.Length)]; stream.ReadExactly(bytes);
        if (stream.ReadByte() != -1) return false;
        var options = new JsonDocumentOptions { MaxDepth = 8 };
        using var expected = JsonDocument.Parse(reviewed, options);
        using var actual = JsonDocument.Parse(bytes, options);
        static bool Fields(JsonElement value, string[] fields) => value.ValueKind == JsonValueKind.Object
            && value.EnumerateObject().Select(p => p.Name).Order(StringComparer.Ordinal).SequenceEqual(fields.Order(StringComparer.Ordinal));
        var root = actual.RootElement;
        if (!Fields(root, ["schemaVersion", "documents"]) || !root.GetProperty("schemaVersion").TryGetInt32(out var version) || version != 1) return false;
        var documents = root.GetProperty("documents");
        if (documents.ValueKind != JsonValueKind.Array || documents.GetArrayLength() != 8) return false;
        var original = expected.RootElement.GetProperty("documents");
        for (var index = 0; index < 8; index++)
        {
            var document = documents[index]; var reference = original[index];
            if (!Fields(document, ["url", "title", "content", "source", "updatedUtc"])) return false;
            foreach (var field in new[] { "url", "title", "content", "source" })
                if (document.GetProperty(field).ValueKind != JsonValueKind.String || document.GetProperty(field).GetString() != reference.GetProperty(field).GetString()) return false;
            if (document.GetProperty("updatedUtc").ValueKind != JsonValueKind.String
                || !document.GetProperty("updatedUtc").TryGetDateTimeOffset(out var stamp) || stamp.Offset != TimeSpan.Zero
                || stamp != reference.GetProperty("updatedUtc").GetDateTimeOffset()) return false;
        }
        return true;
    }

    internal static async Task<int> RunImporterAsync(ProcessStartInfo start, CancellationToken token)
    {
        start.RedirectStandardOutput = true; start.RedirectStandardError = true;
        using var process = Process.Start(start) ?? throw new InvalidOperationException();
        static async Task DrainAsync(StreamReader reader, CancellationToken cancellation)
        {
            var buffer = new char[512]; int total = 0, count;
            while ((count = await reader.ReadAsync(buffer.AsMemory(), cancellation).ConfigureAwait(false)) != 0)
                if ((total += count) > 4096) throw new IOException();
        }
        var drains = Task.WhenAll(DrainAsync(process.StandardOutput, token), DrainAsync(process.StandardError, token));
        try
        {
            await process.WaitForExitAsync(token).ConfigureAwait(false);
            await drains.WaitAsync(token).ConfigureAwait(false);
            return process.ExitCode;
        }
        finally
        {
            if (!process.HasExited) { process.Kill(true); await process.WaitForExitAsync().ConfigureAwait(false); }
            try { await drains.ConfigureAwait(false); } catch (Exception ex) when (ex is IOException or OperationCanceledException) { }
        }
    }

    private void Clean(string? directory)
    {
        if (directory is null || !workspaces.Contains(directory)) return;
        try
        {
            if ((File.GetAttributes(directory) & FileAttributes.ReparsePoint) != 0) return;
            // Remove only our two known files; a foreign entry prevents directory removal.
            foreach (var name in new[] { "catalog.json", "index.json" })
            {
                var path = Path.Combine(directory, name);
                if (File.Exists(path) && (File.GetAttributes(path) & FileAttributes.ReparsePoint) == 0) File.Delete(path);
            }
            Directory.Delete(directory); workspaces.Remove(directory);
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException) { }
    }
    public void Dispose()
    {
        disposed = true; lifetime.Cancel();
        if (!changing.Wait(TimeSpan.FromSeconds(10))) return;
        try { if (launcher.HasConfirmedShutdown) { foreach (var directory in workspaces.ToArray()) Clean(directory); workspace = null; } }
        finally { changing.Release(); }
    }
}
