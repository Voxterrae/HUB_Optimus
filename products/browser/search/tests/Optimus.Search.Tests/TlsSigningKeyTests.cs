using Optimus.Search;
using System.Runtime.Versioning;
using System.Security.Cryptography;
using System.Security.Cryptography.X509Certificates;

static class TlsSigningKeyTests
{
    public static void Register(Action<string, Func<Task>> test)
    {
        // Catches a disposed host minting another identity after its certificate was released.
        test("disposed TLS certificate owner cannot mint another identity", () =>
        {
            using var certificate = new ServiceCertificate(new string('a', 64));
            certificate.ForPort(17831);
            certificate.Dispose();
            try { certificate.ForPort(17831); }
            catch (ObjectDisposedException) { return Task.CompletedTask; }
            throw new Exception("A disposed certificate owner created another identity");
        });

        // Catches replacing the curve or releasing the signer before the certificate can use it.
        test("TLS signing owner signs with P-256 until disposal", () =>
        {
            using var owner = TlsSigningKey.Create();
            Require(owner.Key.KeySize == 256 && owner.Key.ExportParameters(false).Curve.Oid.Value == "1.2.840.10045.3.1.7", "TLS signing key must be P-256");
            VerifySignature(owner);
            owner.Dispose();
            owner.Dispose();
            try { owner.Key.SignData([1, 2, 3], HashAlgorithmName.SHA256); }
            catch (ObjectDisposedException) { return Task.CompletedTask; }
            throw new Exception("Disposed signing owner remained usable");
        });

        if (OperatingSystem.IsWindows()) RegisterWindows(test);
        else Console.WriteLine("SKIP Windows TLS CNG lifecycle checks: this platform is not Windows.");
    }

    [SupportedOSPlatform("windows")]
    private static void RegisterWindows(Action<string, Func<Task>> test)
    {
        // Catches ephemeral, machine-wide, exportable, or incorrectly scoped replacement keys.
        test("Windows TLS signing key uses the nonexportable current-user software provider", () =>
        {
            using var owner = TlsSigningKey.Create();
            var key = WindowsKey(owner);
            Require(!key.IsEphemeral && !key.IsMachineKey && !string.IsNullOrEmpty(key.KeyName), "Schannel requires a named current-user key");
            Require(key.Provider == CngProvider.MicrosoftSoftwareKeyStorageProvider, "Unexpected TLS key provider");
            Require(key.ExportPolicy == CngExportPolicies.None && key.KeyUsage == CngKeyUsages.Signing, "TLS private key must be signing-only and nonexportable");
            byte[] exported;
            try { exported = owner.Key.ExportPkcs8PrivateKey(); }
            catch (CryptographicException) { VerifySignature(owner); return Task.CompletedTask; }
            CryptographicOperations.ZeroMemory(exported);
            throw new Exception("TLS private key export unexpectedly succeeded");
        });

        // Catches Dispose merely closing handles and leaving the named private key behind.
        test("Windows TLS signing key deletion removes its exact provider identity", () =>
        {
            using var owner = TlsSigningKey.Create();
            var key = WindowsKey(owner); var name = key.KeyName!; var provider = key.Provider!;
            using (var reopened = CngKey.Open(name, provider, CngKeyOpenOptions.None))
                Require(reopened.KeyName == name && !reopened.IsMachineKey, "Live user key must be reopenable by its exact name");
            owner.Dispose(); owner.Dispose();
            RequireMissing(name, provider);
            return Task.CompletedTask;
        });

        // Catches shared key names or cleanup that deletes another live host's key.
        test("Windows TLS signing owners delete only their own independent keys", () =>
        {
            using var first = TlsSigningKey.Create(); using var second = TlsSigningKey.Create();
            var firstKey = WindowsKey(first); var secondKey = WindowsKey(second);
            var firstName = firstKey.KeyName!; var firstProvider = firstKey.Provider!;
            var secondName = secondKey.KeyName!; var provider = secondKey.Provider!;
            Require(firstName != secondName, "Hosts must never share a signing key name");
            first.Dispose(); RequireMissing(firstName, firstProvider);
            using (var reopened = CngKey.Open(secondName, provider, CngKeyOpenOptions.None))
                Require(reopened.KeyName == secondName, "Disposing one owner removed a different owner's key");
            VerifySignature(second);
            second.Dispose(); RequireMissing(secondName, provider);
            return Task.CompletedTask;
        });

        // Catches failure paths that retain a named key after certificate creation throws.
        test("Windows TLS signing scope cleans its key after failed certificate creation", () =>
        {
            string name = ""; CngProvider? provider = null; var failed = false;
            try
            {
                using var owner = TlsSigningKey.Create();
                var key = WindowsKey(owner); name = key.KeyName!; provider = key.Provider!;
                var request = new CertificateRequest("CN=failed-fixture", owner.Key, HashAlgorithmName.SHA256);
                using var certificate = request.CreateSelfSigned(DateTimeOffset.UtcNow, DateTimeOffset.UtcNow.AddMinutes(-1));
            }
            catch (ArgumentException) { failed = true; }
            Require(failed, "Certificate construction must actually fail inside the owning scope");
            RequireMissing(name, provider!);
            return Task.CompletedTask;
        });

        // Catches the production certificate dropping ownership early or omitting deletion on stop.
        test("Windows service certificate retains its named signing key until disposal", () =>
        {
            using var owner = new ServiceCertificate(new string('a', 64));
            var certificate = owner.ForPort(17831);
            Require(ReferenceEquals(certificate, owner.ForPort(17831)), "One running host must retain one certificate");
            string name; CngProvider provider;
            using (var signer = certificate.GetECDsaPrivateKey())
            {
                Require(signer is ECDsaCng, "Windows service certificate lost its provider-backed private key");
                var key = ((ECDsaCng)signer!).Key;
                name = key.KeyName!; provider = key.Provider!;
                Require(!string.IsNullOrEmpty(name) && CngKey.Exists(name, provider, CngKeyOpenOptions.None), "Host signing key was not retained");
            }
            owner.Dispose(); owner.Dispose(); RequireMissing(name, provider);
            return Task.CompletedTask;
        });
    }

    private static void VerifySignature(TlsSigningKey owner)
    {
        byte[] data = [0x54, 0x4c, 0x53, 0x01];
        using var publicKey = ECDsa.Create();
        publicKey.ImportSubjectPublicKeyInfo(owner.Key.ExportSubjectPublicKeyInfo(), out _);
        Require(publicKey.VerifyData(data, owner.Key.SignData(data, HashAlgorithmName.SHA256), HashAlgorithmName.SHA256), "Owned key cannot prove private-key possession");
    }

    [SupportedOSPlatform("windows")]
    private static CngKey WindowsKey(TlsSigningKey owner)
    {
        Require(owner.Key is ECDsaCng, "Windows signing key must retain its CNG provider identity");
        return ((ECDsaCng)owner.Key).Key;
    }

    [SupportedOSPlatform("windows")]
    private static void RequireMissing(string name, CngProvider provider)
    {
        Require(!CngKey.Exists(name, provider, CngKeyOpenOptions.None), "Disposed TLS key still exists in its provider");
        try { using var reopened = CngKey.Open(name, provider, CngKeyOpenOptions.None); }
        catch (CryptographicException) { return; }
        throw new Exception("Disposed TLS key could still be reopened");
    }

    private static void Require(bool value, string message) { if (!value) throw new Exception(message); }
}
