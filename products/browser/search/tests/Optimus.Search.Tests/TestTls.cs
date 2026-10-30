using System.Security.Cryptography.X509Certificates;
using System.Security.Cryptography;
using System.Text;

static class TestTls
{
    public static HttpClientHandler Handler(Func<string>? token = null) => new()
    {
        UseProxy = false,
        ServerCertificateCustomValidationCallback = (request, cert, _, _) =>
        {
            if(cert is null || request.RequestUri!.Scheme != "https" || request.RequestUri.Host != "127.0.0.1") return false;
            using var key = cert.GetECDsaPublicKey();
            var proof = cert.Extensions.Cast<System.Security.Cryptography.X509Certificates.X509Extension>().SingleOrDefault(e => e.Oid!.Value == "1.3.6.1.4.1.57264.2021.1");
            if(key is null || proof?.RawData.Length != 32) return false;
            var message = $"OptimusSearch/TLS/v1|https://127.0.0.1:{request.RequestUri.Port}|{Convert.ToBase64String(key.ExportSubjectPublicKeyInfo())}";
            return CryptographicOperations.FixedTimeEquals(proof.RawData, HMACSHA256.HashData(Encoding.ASCII.GetBytes(token?.Invoke() ?? new string('a',64)),Encoding.ASCII.GetBytes(message)));
        }
    };
}
