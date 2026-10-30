using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;

namespace Optimus.Search;

// Lifetime is exactly one host start. No key export, certificate store or profile writes.
internal sealed class ServiceCertificate(string token) : IDisposable
{
    private readonly object sync = new();
    private X509Certificate2? certificate;
    public X509Certificate2 ForPort(int port)
    {
        lock (sync)
        {
            if (certificate is not null) return certificate;
            using var key = ECDsa.Create(ECCurve.NamedCurves.nistP256);
            var request = new CertificateRequest("CN=OptimusSearch", key, HashAlgorithmName.SHA256);
            var names = new SubjectAlternativeNameBuilder(); names.AddIpAddress(System.Net.IPAddress.Loopback);
            request.CertificateExtensions.Add(names.Build());
            request.CertificateExtensions.Add(new X509KeyUsageExtension(X509KeyUsageFlags.DigitalSignature, true));
            request.CertificateExtensions.Add(new X509EnhancedKeyUsageExtension(new OidCollection { new("1.3.6.1.5.5.7.3.1") }, false));
            var message = $"OptimusSearch/TLS/v1|https://127.0.0.1:{port}|{Convert.ToBase64String(key.ExportSubjectPublicKeyInfo())}";
            var proof = HMACSHA256.HashData(Encoding.ASCII.GetBytes(token), Encoding.ASCII.GetBytes(message));
            request.CertificateExtensions.Add(new X509Extension("1.3.6.1.4.1.57264.2021.1", proof, false));
            certificate = request.CreateSelfSigned(DateTimeOffset.UtcNow.AddMinutes(-5), DateTimeOffset.UtcNow.AddDays(30));
            return certificate;
        }
    }
    public void Dispose() { lock (sync) { certificate?.Dispose(); certificate = null; } }
}
