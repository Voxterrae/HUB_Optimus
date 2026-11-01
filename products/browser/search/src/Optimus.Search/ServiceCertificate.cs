using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;
using System.Text;

namespace Optimus.Search;

// Lifetime is exactly one host start. Windows owns a named, nonexportable user
// provider key for Schannel; all platforms avoid private-key export and trust stores.
internal sealed class ServiceCertificate(string token) : IDisposable
{
    private readonly object sync = new();
    private X509Certificate2? certificate;
    private TlsSigningKey? signingKey;
    private bool disposed;
    public X509Certificate2 ForPort(int port)
    {
        lock (sync)
        {
            ObjectDisposedException.ThrowIf(disposed, this);
            if (certificate is not null) return certificate;
            signingKey = TlsSigningKey.Create();
            try
            {
                var key = signingKey.Key;
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
            catch (Exception creationFailure)
            {
                try { Dispose(); }
                catch (Exception cleanupFailure) { throw new AggregateException("TLS certificate initialization and cleanup failed.", creationFailure, cleanupFailure); }
                throw;
            }
        }
    }
    public void Dispose()
    {
        lock (sync)
        {
            disposed = true;
            try { certificate?.Dispose(); }
            finally
            {
                certificate = null;
                signingKey?.Dispose();
                signingKey = null;
            }
        }
    }
}
