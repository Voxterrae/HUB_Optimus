namespace Optimus.Core;

public record SearchResult(string Title, string Url, string Snippet, string Source);
public record SearchResponse(IReadOnlyList<SearchResult> Results, string Provider, string? Error);

public enum OptimusSearchScope { Web, Index, Wikipedia }
// A value target preserves unambiguous legacy null-endpoint calls. Never stringify a secret.
public readonly record struct OptimusSearchTarget(OptimusSearchScope Scope, string? Endpoint, string? BearerToken)
{
    public const string LocalEndpoint = "https://127.0.0.1:17831";
    public override string ToString() => $"OptimusSearchTarget({Scope})";
}
