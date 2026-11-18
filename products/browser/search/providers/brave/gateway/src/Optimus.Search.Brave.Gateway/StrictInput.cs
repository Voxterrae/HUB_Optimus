using System.Text;
using System.Text.Json;

namespace Optimus.Search.Brave.Gateway;

internal static class StrictInput
{
    internal static JsonDocument Parse(ReadOnlyMemory<byte> bytes)
    {
        var document = JsonDocument.Parse(bytes, new JsonDocumentOptions { MaxDepth = 8 });
        try { Unique(document.RootElement); return document; } catch { document.Dispose(); throw; }
    }
    private static void Unique(JsonElement element)
    {
        if (element.ValueKind == JsonValueKind.Object)
        {
            var names = new HashSet<string>(StringComparer.Ordinal);
            foreach (var field in element.EnumerateObject()) { if (!names.Add(field.Name)) throw new JsonException(); Unique(field.Value); }
        }
        else if (element.ValueKind == JsonValueKind.Array) foreach (var item in element.EnumerateArray()) Unique(item);
    }
    internal static bool Fields(JsonElement element, params string[] names) => element.ValueKind == JsonValueKind.Object
        && element.EnumerateObject().Count() == names.Length && names.All(name => element.TryGetProperty(name, out _));
    internal static bool Query(string? query)
    {
        if (string.IsNullOrWhiteSpace(query) || query.Length > 500 || query.Any(char.IsControl)
            || query.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries).Length > 75) return false;
        try { _ = new UTF8Encoding(false, true).GetByteCount(query); return true; } catch (EncoderFallbackException) { return false; }
    }
    internal static bool Language(string? language) => language != null
        && (language.Length == 2 || language.Length == 5 && language[2] == '-' && char.IsAsciiLetter(language[3]) && char.IsAsciiLetter(language[4]))
        && language[..2].ToLowerInvariant() is "es" or "ca" or "en" or "de" or "fr" or "ru";
    internal static bool LowerHex(string? text) => text?.Length == 64 && text.All(c => c is >= '0' and <= '9' or >= 'a' and <= 'f');
}
