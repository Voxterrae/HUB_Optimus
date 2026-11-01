using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;

namespace Optimus.Core;

/// <summary>One token snapshot per transport. TLS authenticates every connection before HTTP is sent.</summary>
public static class LocalSearchTransport
{
    public static HttpClient CreateClient(string token)
    {
        if (!OptimusSearchService.IsValidToken(token)) throw new ArgumentException("Invalid local identity.");
        return new HttpClient(new HttpClientHandler
        {
            UseProxy = false, AllowAutoRedirect = false, UseCookies = false, Credentials = null, UseDefaultCredentials = false,
            ServerCertificateCustomValidationCallback = (request, certificate, _, _) => Validate(certificate, request.RequestUri, token)
        }) { Timeout = Timeout.InfiniteTimeSpan };
    }

    internal static bool Validate(X509Certificate2? certificate, Uri? endpoint, string token)
    {
        if (certificate is null || endpoint is null || endpoint.Scheme != "https" || endpoint.Host != "127.0.0.1" || endpoint.Port is < 1 or > 65535
            || endpoint.UserInfo.Length != 0 || !OptimusSearchService.IsValidToken(token)) return false;
        try
        {
            // This is private profile authentication, not public PKI trust. Exact HMAC + TLS key possession replace chain trust.
            if (DateTime.UtcNow < certificate.NotBefore.ToUniversalTime() || DateTime.UtcNow > certificate.NotAfter.ToUniversalTime()) return false;
            var proofs = certificate.Extensions.Cast<X509Extension>().Where(e => e.Oid?.Value == "1.3.6.1.4.1.57264.2021.1").ToArray();
            if (proofs.Length != 1 || proofs[0].RawData.Length != 32) return false;
            using var key = certificate.GetECDsaPublicKey();
            if (key is null || key.KeySize != 256) return false;
            var message = $"OptimusSearch/TLS/v1|https://127.0.0.1:{endpoint.Port}|{Convert.ToBase64String(key.ExportSubjectPublicKeyInfo())}";
            var expected = HMACSHA256.HashData(Encoding.ASCII.GetBytes(token), Encoding.ASCII.GetBytes(message));
            return CryptographicOperations.FixedTimeEquals(expected, proofs[0].RawData);
        }
        catch (Exception ex) when (ex is CryptographicException or ArgumentException) { return false; }
    }
}
