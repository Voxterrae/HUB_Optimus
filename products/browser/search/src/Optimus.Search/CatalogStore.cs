using System.Globalization;
using System.Text;
using System.Text.Json;

namespace Optimus.Search;

public static class CatalogStore
{
    public const int MaximumFileBytes = 16 * 1024 * 1024;
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web) { WriteIndented = true };
    public static async Task<IReadOnlyList<CatalogDocument>> LoadAsync(string path, CancellationToken cancellationToken = default)
    {
        try
        {
            await using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, 8192, FileOptions.Asynchronous);
            var bytes = await BoundedRead.ReadAsync(stream, MaximumFileBytes, cancellationToken);
            using var json = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 32 });
            var root = json.RootElement;
            if (root.ValueKind != JsonValueKind.Object || !root.TryGetProperty("schemaVersion", out var schema) || !schema.TryGetInt32(out var version) || version != 1
                || !root.TryGetProperty("documents", out var docs) || docs.ValueKind != JsonValueKind.Array || docs.GetArrayLength() > 1000) throw Invalid();
            var result = new List<CatalogDocument>();
            var seen = new HashSet<string>(StringComparer.Ordinal);
            foreach (var doc in docs.EnumerateArray())
            {
                var url = ReadString(doc, "url"); var title = ReadString(doc, "title"); var content = ReadString(doc, "content");
                var source = ReadString(doc, "source"); var updated = ReadString(doc, "updatedUtc");
                if (!SearchValidation.TryNormalizeUrl(url, out var normalized) || !seen.Add(normalized) || string.IsNullOrWhiteSpace(title) || title.Length > 240 || title.Any(char.IsControl)
                    || Encoding.UTF8.GetByteCount(content) > 64 * 1024 || string.IsNullOrWhiteSpace(source) || source.Length > 240 || source.Any(char.IsControl)
                    || !DateTimeOffset.TryParse(updated, CultureInfo.InvariantCulture, DateTimeStyles.RoundtripKind, out var date) || date.Offset != TimeSpan.Zero
                    || !(updated.EndsWith('Z') || updated.EndsWith("+00:00", StringComparison.Ordinal))) throw Invalid();
                result.Add(new(normalized, title, content, source, date));
            }
            return result.AsReadOnly();
        }
        catch (Exception ex) when (ex is JsonException or InvalidOperationException or FormatException) { throw Invalid(); }
    }
    public static async Task ImportAsync(string input, string output, CancellationToken cancellationToken = default)
    {
        var documents = await LoadAsync(input, cancellationToken);
        var bytes = JsonSerializer.SerializeToUtf8Bytes(new { schemaVersion = 1, documents }, JsonOptions);
        if (bytes.Length > MaximumFileBytes) throw Invalid();
        var full = Path.GetFullPath(output);
        Directory.CreateDirectory(Path.GetDirectoryName(full)!);
        var temporary = full + "." + Guid.NewGuid().ToString("N") + ".tmp";
        try
        {
            await using (var stream = new FileStream(temporary, FileMode.CreateNew, FileAccess.Write, FileShare.None, 8192, FileOptions.Asynchronous))
            {
                await stream.WriteAsync(bytes, cancellationToken);
                await stream.FlushAsync(cancellationToken);
                stream.Flush(true);
            }
            cancellationToken.ThrowIfCancellationRequested();
            File.Move(temporary, full, true);
        }
        finally { if (File.Exists(temporary)) File.Delete(temporary); }
    }
    private static InvalidDataException Invalid() => new("Invalid catalog.");
    private static string ReadString(JsonElement parent, string property) => parent.ValueKind == JsonValueKind.Object && parent.TryGetProperty(property, out var value) && value.ValueKind == JsonValueKind.String ? value.GetString()! : throw Invalid();
}
