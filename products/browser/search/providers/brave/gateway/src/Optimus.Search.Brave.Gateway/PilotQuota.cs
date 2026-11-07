using System.Globalization;
using System.Text;

namespace Optimus.Search.Brave.Gateway;

/// <summary>Operator-owned lifetime pilot budget. A reservation is never refunded.</summary>
public sealed class PilotQuota : IDisposable
{
    private readonly FileStream stream;
    private readonly string path;
    private readonly object gate = new();
    private int used;
    private bool faulted;
    private bool pending;
    private PilotQuota(string path, FileStream stream, int used) { this.path = path; this.stream = stream; this.used = used; }
    private static byte[] Record(int count) => Encoding.ASCII.GetBytes("OptimusBraveQuota/v1\n100\n" + count.ToString(CultureInfo.InvariantCulture) + "\n");

    public static void Initialize(string path)
    {
        SafePath.RequireRegularAncestors(path, requireFile: false);
        using var file = new FileStream(path, FileMode.CreateNew, FileAccess.Write, FileShare.None, 4096, FileOptions.WriteThrough);
        file.Write(Record(0)); file.Flush(flushToDisk: true);
    }
    public static PilotQuota Open(string path)
    {
        FileStream? file = null;
        try
        {
            SafePath.RequireRegularAncestors(path);
            file = new FileStream(path, FileMode.Open, FileAccess.ReadWrite, FileShare.None, 4096, FileOptions.WriteThrough);
            return new(Path.GetFullPath(path), file, ReadRecord(file));
        }
        catch (Exception ex) when (ex is IOException or UnauthorizedAccessException)
        { file?.Dispose(); throw new IOException("Pilot quota unavailable."); }
    }
    private static int ReadRecord(FileStream file)
    {
        if (file.Length is < 1 or > 64) throw new IOException("Pilot quota unavailable.");
        file.Position = 0;
        var bytes = new byte[(int)file.Length]; file.ReadExactly(bytes);
        var text = Encoding.ASCII.GetString(bytes); var lines = text.Split('\n');
        if (lines.Length != 4 || !int.TryParse(lines[2], NumberStyles.None, CultureInfo.InvariantCulture, out var count)
            || count is < 0 or > 100 || !bytes.AsSpan().SequenceEqual(Record(count))) throw new IOException("Pilot quota unavailable.");
        return count;
    }
    public bool TryReserve() => Reserve(markPending: false);
    internal bool TryBeginCall() => Reserve(markPending: true);
    private bool Reserve(bool markPending)
    {
        lock (gate)
        {
            if (faulted || pending) throw new IOException("Pilot quota unavailable.");
            try
            {
                SafePath.RequireRegularAncestors(path);
                if (ReadRecord(stream) != used) throw new IOException("Pilot quota unavailable.");
                if (used == 100) return false;
                var next = markPending ? Encoding.ASCII.GetBytes(Encoding.ASCII.GetString(Record(used + 1)) + "pending\n") : Record(used + 1);
                stream.Position = 0; stream.Write(next); stream.SetLength(next.Length); stream.Flush(flushToDisk: true);
                used++; pending = markPending; return true;
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or ObjectDisposedException)
            { faulted = true; throw new IOException("Pilot quota unavailable."); }
        }
    }
    internal void CompleteCall()
    {
        lock (gate)
        {
            if (faulted || !pending) throw new IOException("Pilot quota unavailable.");
            try
            {
                SafePath.RequireRegularAncestors(path);
                var expected = Encoding.ASCII.GetBytes(Encoding.ASCII.GetString(Record(used)) + "pending\n");
                if (stream.Length != expected.Length) throw new IOException("Pilot quota unavailable.");
                stream.Position = 0; var actual = new byte[expected.Length]; stream.ReadExactly(actual);
                if (!actual.AsSpan().SequenceEqual(expected)) throw new IOException("Pilot quota unavailable.");
                var complete = Record(used);
                stream.Position = 0; stream.Write(complete); stream.SetLength(complete.Length); stream.Flush(flushToDisk: true);
                pending = false;
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or ObjectDisposedException)
            { faulted = true; throw new IOException("Pilot quota unavailable."); }
        }
    }
    // The pending marker was durably flushed BEFORE forwarding, so no second
    // best-effort write is needed to block restart after an uncertain operation.
    internal void StopUncertainPilot()
    {
        lock (gate) { faulted = true; }
    }
    public void Dispose() { lock (gate) { faulted = true; stream.Dispose(); } }
}

internal static class SafePath
{
    internal static void RequireRegularAncestors(string path, bool requireFile = true)
    {
        var full = Path.GetFullPath(path);
        if (requireFile || File.Exists(full))
        {
            var attributes = File.GetAttributes(full);
            if ((attributes & (FileAttributes.ReparsePoint | FileAttributes.Directory)) != 0) throw new IOException("Local state unavailable.");
        }
        for (var directory = Path.GetDirectoryName(full); directory != null; directory = Path.GetDirectoryName(directory))
            if ((File.GetAttributes(directory) & FileAttributes.ReparsePoint) != 0) throw new IOException("Local state unavailable.");
    }
}
