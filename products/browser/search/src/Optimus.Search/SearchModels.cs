using System.Text;

namespace Optimus.Search;

public sealed record CatalogDocument(string Url, string Title, string Content, string Source, DateTimeOffset UpdatedUtc);
public sealed record SearchResult(string Title, string Url, string Content, string Source);
public sealed record SearchMetadata(int Version, string Scope, bool WebConfigured, int IndexedDocuments);
public sealed record SearchResponse(string Query, IReadOnlyList<SearchResult> Results, SearchMetadata Optimus, string? Error = null, string? Message = null);

public static class SearchValidation
{
    public static bool ValidQuery(string? query) => !string.IsNullOrWhiteSpace(query) && query.Length <= 500 && !query.Any(char.IsControl);
    public static bool TryNormalizeUrl(string? value, out string normalized)
    {
        normalized = "";
        if (string.IsNullOrWhiteSpace(value) || value.Length > 2048 || value.Any(char.IsControl) || value.Contains('\\') || value != value.Trim()
            || !Uri.TryCreate(value, UriKind.Absolute, out var uri) || (uri.Scheme != "http" && uri.Scheme != "https") || !string.IsNullOrEmpty(uri.UserInfo)) return false;
        normalized = new UriBuilder(uri) { Fragment = "" }.Uri.AbsoluteUri;
        return normalized.Length <= 2048;
    }
    public static string Truncate(string text, int length)
    {
        if (text.Length <= length) return text;
        if (length > 0 && char.IsHighSurrogate(text[length - 1])) length--;
        return text[..length];
    }
}
