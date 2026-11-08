using System.Text.Json;
namespace Optimus.Search.Remote;

internal static class StrictJson
{
    public static JsonDocument Parse(ReadOnlyMemory<byte> bytes,int depth=4)
    {
        var json=JsonDocument.Parse(bytes,new JsonDocumentOptions{MaxDepth=depth,CommentHandling=JsonCommentHandling.Disallow,AllowTrailingCommas=false});
        try {Validate(json.RootElement);return json;}catch{json.Dispose();throw;}
    }
    private static void Validate(JsonElement value)
    {
        if(value.ValueKind==JsonValueKind.Object){var names=new HashSet<string>(StringComparer.Ordinal);foreach(var p in value.EnumerateObject()){if(!names.Add(p.Name)||!ValidUnicode(p.Name))throw new JsonException();Validate(p.Value);}}
        else if(value.ValueKind==JsonValueKind.Array)foreach(var item in value.EnumerateArray())Validate(item);
        else if(value.ValueKind==JsonValueKind.String&&!ValidUnicode(value.GetString()!))throw new JsonException();
    }
    public static bool ValidUnicode(string value)
    {
        for(var i=0;i<value.Length;i++){if(char.IsHighSurrogate(value[i])){if(i+1==value.Length||!char.IsLowSurrogate(value[++i]))return false;}else if(char.IsLowSurrogate(value[i]))return false;}return true;
    }
    public static void Fields(JsonElement value,params string[] names)
    {
        if(value.ValueKind!=JsonValueKind.Object||value.EnumerateObject().Count()!=names.Length||value.EnumerateObject().Any(p=>!names.Contains(p.Name,StringComparer.Ordinal)))throw new JsonException();
    }
    public static async Task<byte[]> FileBytes(string path,int maximum)
    {
        try {
            await using var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read,4096,FileOptions.Asynchronous|FileOptions.SequentialScan);
            if(file.Length>maximum)throw new InvalidDataException();
            using var buffer=new MemoryStream();var data=new byte[4096];int read;
            while((read=await file.ReadAsync(data))!=0){if(buffer.Length+read>maximum)throw new InvalidDataException();buffer.Write(data,0,read);}return buffer.ToArray();
        }catch(Exception e)when(e is IOException or UnauthorizedAccessException or ArgumentException or NotSupportedException){throw new InvalidDataException("Invalid remote configuration.");}
    }
}
