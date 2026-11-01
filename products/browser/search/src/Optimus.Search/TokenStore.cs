using System.Diagnostics;
using System.Security.Cryptography;
using System.Text;

namespace Optimus.Search;

public static class TokenStore
{
    public static string DefaultPath => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Optimus", "Search", "service.token");
    public static bool IsValid(string? token) => token is { Length: 64 } && token.All(Uri.IsHexDigit);
    public static bool Matches(string expected, string? supplied)
    {
        if (!IsValid(expected) || !IsValid(supplied)) return false;
        return CryptographicOperations.FixedTimeEquals(Encoding.ASCII.GetBytes(expected), Encoding.ASCII.GetBytes(supplied!));
    }
    public static async Task<string> LoadOrCreateAsync(string path, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        var full = Path.GetFullPath(path);
        if (File.Exists(full)) return await ReadAsync(full, cancellationToken);
        Directory.CreateDirectory(Path.GetDirectoryName(full)!);
        using var guard = await AcquireCreationGuardAsync(full + ".lock", cancellationToken);
        if (File.Exists(full)) return await ReadAsync(full, cancellationToken);
        var temporary = full + "." + Guid.NewGuid().ToString("N") + ".tmp";
        var token = Convert.ToHexStringLower(RandomNumberGenerator.GetBytes(32));
        try
        {
            var options = new FileStreamOptions { Mode = FileMode.CreateNew, Access = FileAccess.Write, Share = FileShare.None, Options = FileOptions.Asynchronous };
            if (!OperatingSystem.IsWindows()) options.UnixCreateMode = UnixFileMode.UserRead | UnixFileMode.UserWrite;
            await using (var stream = new FileStream(temporary, options))
            {
                await stream.WriteAsync(Encoding.ASCII.GetBytes(token), cancellationToken);
                await stream.FlushAsync(cancellationToken); stream.Flush(true);
            }
            cancellationToken.ThrowIfCancellationRequested();
            try { File.Move(temporary, full); }
            catch (IOException) when (File.Exists(full)) { return await ReadAsync(full, cancellationToken); }
            return token;
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }
    private static async Task<FileStream> AcquireCreationGuardAsync(string path, CancellationToken cancellationToken)
    {
        var started = Stopwatch.GetTimestamp();
        var options = new FileStreamOptions { Mode = FileMode.OpenOrCreate, Access = FileAccess.ReadWrite, Share = FileShare.None };
        if (!OperatingSystem.IsWindows()) options.UnixCreateMode = UnixFileMode.UserRead | UnixFileMode.UserWrite;
        while (true)
        {
            cancellationToken.ThrowIfCancellationRequested();
            if (Stopwatch.GetElapsedTime(started) >= TimeSpan.FromSeconds(5))
                throw new IOException("Timed out waiting for token creation.");
            FileStream guard;
            try { guard = new FileStream(path, options); }
            catch (IOException ex) when (IsLockContention(ex))
            {
                await Task.Delay(25, cancellationToken);
                continue;
            }
            try
            {
                if (!OperatingSystem.IsWindows() && (File.GetUnixFileMode(path) & (UnixFileMode.GroupRead | UnixFileMode.GroupWrite | UnixFileMode.GroupExecute | UnixFileMode.OtherRead | UnixFileMode.OtherWrite | UnixFileMode.OtherExecute)) != 0)
                    throw new InvalidDataException("Token creation guard permissions are not private.");
                // Unix FileShare locking can be disabled or unsupported; never publish without verified exclusion.
                try { using var probe = new FileStream(path, FileMode.Open, FileAccess.ReadWrite, FileShare.None); }
                catch (IOException ex) when (IsLockContention(ex))
                {
                    cancellationToken.ThrowIfCancellationRequested();
                    // Keep this empty sidecar permanently: unlinking it could split competing owners across inodes.
                    return guard;
                }
                throw new InvalidDataException("Token creation requires exclusive file locking.");
            }
            catch { guard.Dispose(); throw; }
        }
    }
    private static bool IsLockContention(IOException exception) => OperatingSystem.IsWindows()
        ? (exception.HResult & 0xffff) is 32 or 33
        : exception.HResult is 11 or 35; // EWOULDBLOCK on Linux and macOS.

    private static async Task<string> ReadAsync(string path, CancellationToken cancellationToken)
    {
        await using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, 128, FileOptions.Asynchronous);
        var bytes = await BoundedRead.ReadAsync(stream, 64, cancellationToken);
        var token = Encoding.ASCII.GetString(bytes);
        if (!IsValid(token)) throw new InvalidDataException("Invalid token file.");
        if (!OperatingSystem.IsWindows() && (File.GetUnixFileMode(path) & (UnixFileMode.GroupRead | UnixFileMode.GroupWrite | UnixFileMode.GroupExecute | UnixFileMode.OtherRead | UnixFileMode.OtherWrite | UnixFileMode.OtherExecute)) != 0)
            throw new InvalidDataException("Token file permissions are not private.");
        return token;
    }
}
