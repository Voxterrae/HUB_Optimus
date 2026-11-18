using System.Globalization;
using System.Security.Cryptography;
using System.Text;
using System.Text.Json;

namespace Optimus.Search.Brave.Gateway;

internal sealed class CredentialRegistry(string path)
{
    private readonly object gate = new();
    private DateTimeOffset latestUtc;
    internal bool Allows(string? token)
    {
        if (!StrictInput.LowerHex(token)) return false;
        lock (gate)
        {
            try
            {
                var now = DateTimeOffset.UtcNow;
                if (now < latestUtc) return false;
                latestUtc = now;
                SafePath.RequireRegularAncestors(path);
                using var file = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
                if (file.Length is < 1 or > 8192) return false;
                var bytes = new byte[(int)file.Length]; file.ReadExactly(bytes);
                using var document = StrictInput.Parse(bytes); var root = document.RootElement;
                if (!StrictInput.Fields(root, "version", "credentials") || !root.GetProperty("version").TryGetInt32(out var version) || version != 1) return false;
                var credentials = root.GetProperty("credentials");
                if (credentials.ValueKind != JsonValueKind.Array || credentials.GetArrayLength() is < 1 or > 8) return false;
                var presented = SHA256.HashData(Encoding.ASCII.GetBytes(token!)); var accepted = false;
                var hashes = new HashSet<string>(StringComparer.Ordinal);
                foreach (var credential in credentials.EnumerateArray())
                {
                    if (!StrictInput.Fields(credential, "sha256", "expiresUtc")) return false;
                    var hash = credential.GetProperty("sha256").GetString(); var expires = credential.GetProperty("expiresUtc").GetString();
                    if (!StrictInput.LowerHex(hash) || !hashes.Add(hash!) || !DateTimeOffset.TryParseExact(expires, "yyyy-MM-dd'T'HH:mm:ss'Z'", CultureInfo.InvariantCulture,
                        DateTimeStyles.AssumeUniversal | DateTimeStyles.AdjustToUniversal, out var expiry)) return false;
                    var matches = CryptographicOperations.FixedTimeEquals(presented, Convert.FromHexString(hash!));
                    accepted |= matches && now < expiry;
                }
                return accepted;
            }
            catch (Exception ex) when (ex is IOException or UnauthorizedAccessException or JsonException or InvalidOperationException or FormatException)
            { return false; }
        }
    }
}
