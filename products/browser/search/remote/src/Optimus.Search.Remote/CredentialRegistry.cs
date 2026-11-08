using System.Globalization;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text;
namespace Optimus.Search.Remote;

internal sealed class CredentialRegistry
{
    internal sealed record Client(string Id,byte[] Hash,DateTimeOffset ExpiresUtc);
    private readonly Client[] clients;
    private readonly TimeProvider time;
    private readonly object gate=new();
    private DateTimeOffset latestUtc;
    private CredentialRegistry(Client[] rows,TimeProvider clock){clients=rows;time=clock;latestUtc=time.GetUtcNow();}
    public static async Task<CredentialRegistry> Load(string path,TimeProvider time)
    {
        try {
            if(!Path.IsPathFullyQualified(path)||Path.GetFullPath(path).StartsWith(Path.GetFullPath(AppContext.BaseDirectory),OperatingSystem.IsWindows()?StringComparison.OrdinalIgnoreCase:StringComparison.Ordinal))throw new InvalidDataException();
            var bytes=await StrictJson.FileBytes(path,16384);using var json=StrictJson.Parse(bytes);var root=json.RootElement;StrictJson.Fields(root,"schemaVersion","clients");if(root.GetProperty("schemaVersion").GetInt32()!=1)throw new JsonException();var array=root.GetProperty("clients");if(array.ValueKind!=JsonValueKind.Array||array.GetArrayLength() is <1 or >64)throw new JsonException();
            var now=time.GetUtcNow();var rows=new List<Client>();var ids=new HashSet<string>(StringComparer.Ordinal);var hashes=new HashSet<string>(StringComparer.Ordinal);
            foreach(var item in array.EnumerateArray()){
                StrictJson.Fields(item,"clientId","secretSha256","expiresUtc");var id=item.GetProperty("clientId").GetString()!;var hash=item.GetProperty("secretSha256").GetString()!;var expiryText=item.GetProperty("expiresUtc").GetString()!;
                if(id.Length is <1 or >64||!char.IsAsciiLetterOrDigit(id[0])||id.Any(c=>!char.IsAsciiLetterOrDigit(c)&&c!='-'&&c!='_')||!ids.Add(id))throw new JsonException();
                if(hash.Length!=64||hash.Any(c=>!(c is >= '0' and <= '9' or >= 'a' and <= 'f'))||!hashes.Add(hash))throw new JsonException();
                if(!(expiryText.EndsWith('Z')||expiryText.EndsWith("+00:00",StringComparison.Ordinal))||!DateTimeOffset.TryParse(expiryText,CultureInfo.InvariantCulture,DateTimeStyles.None,out var expiry)||expiry.Offset!=TimeSpan.Zero||expiry<=now||expiry>now.AddDays(7))throw new JsonException();
                rows.Add(new(id,Convert.FromHexString(hash),expiry));
            }
            return new(rows.ToArray(),time);
        }catch(Exception e)when(e is JsonException or FormatException or InvalidOperationException or ArgumentException or NullReferenceException){throw new InvalidDataException("Invalid remote configuration.");}
    }
    public Client? Authenticate(string authorization)
    {
        if(!authorization.StartsWith("Bearer ",StringComparison.Ordinal))return null;var token=authorization[7..];if(token.Length!=43||token.Any(c=>!char.IsAsciiLetterOrDigit(c)&&c!='-'&&c!='_'))return null;
        Span<byte> secret=stackalloc byte[32];if(!Convert.TryFromBase64String(token.Replace('-','+').Replace('_','/')+"=",secret,out var written)||written!=32)return null;
        var canonical=Convert.ToBase64String(secret).TrimEnd('=').Replace('+','-').Replace('/','_');if(!string.Equals(canonical,token,StringComparison.Ordinal)){CryptographicOperations.ZeroMemory(secret);return null;}
        Span<byte> hash=stackalloc byte[32];Span<byte> canonicalBytes=stackalloc byte[43];Encoding.ASCII.GetBytes(token,canonicalBytes);SHA256.HashData(canonicalBytes,hash);CryptographicOperations.ZeroMemory(canonicalBytes);CryptographicOperations.ZeroMemory(secret);DateTimeOffset now;bool clockValid;
        lock(gate){now=time.GetUtcNow();clockValid=now>=latestUtc;if(clockValid)latestUtc=now;}
        Client? found=null;foreach(var row in clients){var equal=CryptographicOperations.FixedTimeEquals(hash,row.Hash);if(equal&&clockValid&&now<row.ExpiresUtc)found=row;}CryptographicOperations.ZeroMemory(hash);return found;
    }
}
