namespace Optimus.Search;

public interface IWebSearchProvider : IDisposable
{
    Task<IReadOnlyList<SearchResult>> SearchAsync(string query, string language, CancellationToken cancellationToken);
}
