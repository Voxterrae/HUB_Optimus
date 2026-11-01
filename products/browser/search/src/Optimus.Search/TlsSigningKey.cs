using System.Runtime.CompilerServices;
using System.Runtime.Versioning;
using System.Security.Cryptography;

[assembly: InternalsVisibleTo("Optimus.Search.Tests")]

namespace Optimus.Search;

// Schannel must reopen a named provider key. Windows writes this current-user key
// to its protected profile storage; abrupt termination can leave it behind.
// No private-key export, trust-store change, machine key, or permission widening.
internal sealed class TlsSigningKey : IDisposable
{
    private readonly object sync = new();
    private ECDsa? key;
    private CngKey? windowsKey;
    private bool disposed;

    private TlsSigningKey(ECDsa key, CngKey? windowsKey = null) { this.key = key; this.windowsKey = windowsKey; }

    public ECDsa Key
    {
        get { lock (sync) { ObjectDisposedException.ThrowIf(disposed, this); return key!; } }
    }

    public static TlsSigningKey Create() => OperatingSystem.IsWindows()
        ? CreateWindows()
        : new(ECDsa.Create(ECCurve.NamedCurves.nistP256));

    [SupportedOSPlatform("windows")]
    private static TlsSigningKey CreateWindows()
    {
        var key = CngKey.Create(CngAlgorithm.ECDsaP256, "OptimusSearch-TLS-" + Guid.NewGuid().ToString("N"), new CngKeyCreationParameters
        {
            Provider = CngProvider.MicrosoftSoftwareKeyStorageProvider,
            KeyUsage = CngKeyUsages.Signing,
            ExportPolicy = CngExportPolicies.None,
            KeyCreationOptions = CngKeyCreationOptions.None
        });
        try { return new(new ECDsaCng(key), key); }
        catch (Exception creationFailure)
        {
            try { key.Delete(); }
            catch (Exception cleanupFailure) { throw new AggregateException("TLS signing key initialization and cleanup failed.", creationFailure, cleanupFailure); }
            finally { key.Dispose(); }
            throw;
        }
    }

    public void Dispose()
    {
        lock (sync)
        {
            disposed = true;
            try { key?.Dispose(); }
            finally
            {
                key = null;
                if (OperatingSystem.IsWindows() && windowsKey is { } retained)
                {
                    // Keep this handle if deletion fails so a later Dispose can retry.
                    // Closing a CNG handle by itself does not remove a named key.
                    retained.Delete();
                    retained.Dispose();
                    windowsKey = null;
                }
            }
        }
    }
}
