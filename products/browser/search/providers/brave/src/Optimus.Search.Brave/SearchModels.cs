namespace Optimus.Search.Brave;

public sealed record BraveSearchResult(string Title, string Url, string Content, string Source);
public enum BraveSearchFailure { Authentication, RateLimited, Timeout, Transport, InvalidResponse, Upstream }
public sealed class BraveSearchException(BraveSearchFailure failure) : Exception("Web search failed.")
{
    public BraveSearchFailure Failure { get; } = failure;
}
