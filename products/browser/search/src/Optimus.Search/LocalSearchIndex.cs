using System.Text;
using System.Text.RegularExpressions;

namespace Optimus.Search;

public sealed class LocalSearchIndex
{
    private sealed record IndexedDocument(CatalogDocument Document, Dictionary<string, int> Terms, int Length);
    private readonly IndexedDocument[] documents;
    private readonly Dictionary<string, int> frequencies = new(StringComparer.Ordinal);
    private readonly double averageLength;
    public int DocumentCount => documents.Length;
    public LocalSearchIndex(IEnumerable<CatalogDocument> source)
    {
        documents = source.Select(doc => {
            var terms = new Dictionary<string, int>(StringComparer.Ordinal);
            foreach (var term in Tokens(doc.Content)) terms[term] = terms.GetValueOrDefault(term) + 1;
            foreach (var term in Tokens(doc.Title)) terms[term] = terms.GetValueOrDefault(term) + 3;
            return new IndexedDocument(doc, terms, Math.Max(1, terms.Values.Sum()));
        }).ToArray();
        foreach (var doc in documents) foreach (var term in doc.Terms.Keys) frequencies[term] = frequencies.GetValueOrDefault(term) + 1;
        averageLength = documents.Length == 0 ? 1 : documents.Average(d => d.Length);
    }
    public IReadOnlyList<SearchResult> Search(string query)
    {
        if (!SearchValidation.ValidQuery(query)) throw new ArgumentException("Invalid query.");
        var terms = Tokens(query).Distinct(StringComparer.Ordinal).ToArray();
        return documents.Select(doc => (Doc: doc, Score: terms.Sum(term => Score(doc, term))))
            .Where(x => x.Score > 0).OrderByDescending(x => x.Score).ThenBy(x => x.Doc.Document.Url, StringComparer.Ordinal).Take(20)
            .Select(x => new SearchResult(x.Doc.Document.Title, x.Doc.Document.Url, SearchValidation.Truncate(x.Doc.Document.Content, 1200), x.Doc.Document.Source)).ToArray();
    }
    private double Score(IndexedDocument document, string term)
    {
        if (!document.Terms.TryGetValue(term, out var frequency)) return 0;
        var inverse = Math.Log(1 + (documents.Length - frequencies[term] + 0.5) / (frequencies[term] + 0.5));
        return inverse * frequency * 2.2 / (frequency + 1.2 * (0.25 + 0.75 * document.Length / averageLength));
    }
    private static IEnumerable<string> Tokens(string value) => Regex.Matches(value.Normalize(NormalizationForm.FormKC).ToLowerInvariant(), @"[\p{L}\p{Nd}][\p{L}\p{Nd}\p{M}]*", RegexOptions.CultureInvariant).Select(m => m.Value);
}
