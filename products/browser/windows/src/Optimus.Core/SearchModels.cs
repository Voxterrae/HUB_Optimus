namespace Optimus.Core;

public record SearchResult(string Title, string Url, string Snippet, string Source);
public record SearchResponse(IReadOnlyList<SearchResult> Results, string Provider, string? Error);
