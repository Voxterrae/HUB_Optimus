using System.Security.Cryptography;
using System.Text;
using System.Text.Json;
using Optimus.Search;
namespace Optimus.Search.Remote;

public sealed record RemoteProvenance(string ReferenceKind,string ReferenceCheckedDate,string? SourceRevision,string SummarySha256);
public sealed record RemoteResult(string Title,string Url,string Content,string Source,string UpdatedUtc,RemoteProvenance Provenance);
internal sealed class PinnedCatalog
{
    public const string CatalogId="optimus-public-pilot-v0.1";
    public const string CatalogHash="8294911789f69f2c1262c80153ca0dddd6189e9a198b586f5fbb3beeb0d665ec";
    public const string ProvenanceHash="5312f482daea11727c9c90a683bcf95dce587021aa6c63609b9038756eb05aae";
    private readonly LocalSearchIndex index;
    private readonly Dictionary<string,RemoteResult> documents;
    public byte[] CatalogResponse{get;}
    private PinnedCatalog(Dictionary<string,RemoteResult> docs,byte[] catalog,byte[] provenance)
    {
        documents=docs;index=new LocalSearchIndex(docs.Values.Select(d=>new CatalogDocument(d.Url,d.Title,d.Content,d.Source,DateTimeOffset.Parse(d.UpdatedUtc,System.Globalization.CultureInfo.InvariantCulture))));
        CatalogResponse=JsonSerializer.SerializeToUtf8Bytes(new{schemaVersion=1,catalogId=CatalogId,catalogSha256=CatalogHash,provenanceSha256=ProvenanceHash,catalogBytesBase64=Convert.ToBase64String(catalog),provenanceBytesBase64=Convert.ToBase64String(provenance)});
        if(CatalogResponse.Length>RemoteLimits.ResponseBytes)throw new InvalidDataException("Invalid remote configuration.");
    }
    public static async Task<PinnedCatalog> Load(string catalogPath,string provenancePath)
    {
        var catalog=await StrictJson.FileBytes(catalogPath,32768);var provenance=await StrictJson.FileBytes(provenancePath,32768);
        if(Convert.ToHexStringLower(SHA256.HashData(catalog))!=CatalogHash||Convert.ToHexStringLower(SHA256.HashData(provenance))!=ProvenanceHash)throw new InvalidDataException("Invalid remote configuration.");
        try{
            using var cat=StrictJson.Parse(catalog,8);using var prov=StrictJson.Parse(provenance,8);var entries=prov.RootElement.GetProperty("entries").EnumerateArray().ToDictionary(e=>e.GetProperty("url").GetString()!,StringComparer.Ordinal);var docs=new Dictionary<string,RemoteResult>(StringComparer.Ordinal);
            if(cat.RootElement.GetProperty("schemaVersion").GetInt32()!=1||prov.RootElement.GetProperty("schemaVersion").GetInt32()!=1||prov.RootElement.GetProperty("catalogId").GetString()!=CatalogId||prov.RootElement.GetProperty("catalogCanonicalSha256").GetString()!=CatalogHash)throw new JsonException();
            foreach(var doc in cat.RootElement.GetProperty("documents").EnumerateArray()){
                var url=doc.GetProperty("url").GetString()!;var entry=entries[url];var content=doc.GetProperty("content").GetString()!;var hash=entry.GetProperty("summarySha256").GetString()!;
                if(Convert.ToHexStringLower(SHA256.HashData(Encoding.UTF8.GetBytes(content)))!=hash)throw new JsonException();
                docs.Add(url,new(doc.GetProperty("title").GetString()!,url,content,doc.GetProperty("source").GetString()!,doc.GetProperty("updatedUtc").GetString()!,new(entry.GetProperty("referenceKind").GetString()!,entry.GetProperty("referenceCheckedDate").GetString()!,entry.GetProperty("sourceRevision").GetString(),hash)));
            }
            if(docs.Count!=8||entries.Count!=8)throw new JsonException();return new(docs,catalog,provenance);
        }catch(Exception e)when(e is JsonException or InvalidOperationException or ArgumentException or KeyNotFoundException){throw new InvalidDataException("Invalid remote configuration.");}
    }
    public byte[] Search(string query,int limit)
    {
        // Ranking is reused unchanged; return the original complete authored summary, not its local-host snippet.
        var results=index.Search(query).Take(limit).Select(r=>documents[r.Url]).ToArray();return JsonSerializer.SerializeToUtf8Bytes(new{schemaVersion=1,catalogId=CatalogId,catalogSha256=CatalogHash,provenanceSha256=ProvenanceHash,results},JsonOptions);
    }
    internal static readonly JsonSerializerOptions JsonOptions=new(JsonSerializerDefaults.Web);
}
