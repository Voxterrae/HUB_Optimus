//! Owned software CNG signing keys. These types confer no enrollment authority.

use std::fmt;
use std::ptr::{null, null_mut};
use windows_sys::Win32::Foundation::NTE_BAD_SIGNATURE;
use windows_sys::Win32::Security::Cryptography as cng;
use windows_sys::core::PCWSTR;

const NAME_PREFIX: &str = "HUB_Relay.NativePilot.Test.";
const NAME_UNITS: usize = NAME_PREFIX.len() + 32 + 1;

/// An operation failure, without a key name or cryptographic material.
#[derive(Clone, Copy, Debug)]
pub struct Failure {
    operation: &'static str,
    status: Option<i32>,
}

impl Failure {
    pub fn operation(&self) -> &'static str {
        self.operation
    }

    /// The unmodified Windows status; `None` denotes a local invariant failure.
    pub fn status(&self) -> Option<i32> {
        self.status
    }
}

/// Keeps the original failure and a failed attempt to delete a partial key.
#[derive(Debug)]
pub struct Error {
    failure: Failure,
    cleanup_failure: Option<Failure>,
}

impl Error {
    fn invalid(operation: &'static str) -> Self {
        Self {
            failure: Failure {
                operation,
                status: None,
            },
            cleanup_failure: None,
        }
    }

    pub fn operation(&self) -> &'static str {
        self.failure.operation
    }

    pub fn status(&self) -> Option<i32> {
        self.failure.status
    }

    pub fn cleanup_failure(&self) -> Option<&Failure> {
        self.cleanup_failure.as_ref()
    }
}

impl fmt::Display for Failure {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self.status {
            Some(status) => write!(
                formatter,
                "{}: Windows status {status:#010x}",
                self.operation
            ),
            None => write!(formatter, "{}: invariant mismatch", self.operation),
        }
    }
}

impl fmt::Display for Error {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.failure.fmt(formatter)?;
        if let Some(cleanup) = self.cleanup_failure {
            write!(formatter, "; owned-key cleanup failed: {cleanup}")?;
        }
        Ok(())
    }
}

impl std::error::Error for Error {}

fn check(status: i32, operation: &'static str) -> Result<(), Error> {
    if status == 0 {
        Ok(())
    } else {
        Err(Error {
            failure: Failure {
                operation,
                status: Some(status),
            },
            cleanup_failure: None,
        })
    }
}

struct Provider(cng::NCRYPT_PROV_HANDLE);

impl Provider {
    fn open() -> Result<Self, Error> {
        let mut provider = Self(0);
        // SAFETY: the output is writable and the provider identifier is a CNG constant.
        check(
            unsafe {
                cng::NCryptOpenStorageProvider(&mut provider.0, cng::MS_KEY_STORAGE_PROVIDER, 0)
            },
            "NCryptOpenStorageProvider",
        )?;
        Ok(provider)
    }
}

impl Drop for Provider {
    fn drop(&mut self) {
        if self.0 != 0 {
            // SAFETY: this wrapper exclusively owns this provider handle.
            unsafe {
                cng::NCryptFreeObject(self.0);
            }
        }
    }
}

struct Key(cng::NCRYPT_KEY_HANDLE);

impl Key {
    fn delete(&mut self) -> Result<(), Error> {
        // SAFETY: this wrapper owns the key; success frees and invalidates its handle.
        check(
            unsafe { cng::NCryptDeleteKey(self.0, cng::NCRYPT_SILENT_FLAG) },
            "NCryptDeleteKey",
        )?;
        self.0 = 0;
        Ok(())
    }
}

impl Drop for Key {
    fn drop(&mut self) {
        if self.0 != 0 {
            // SAFETY: a successfully deleted key was set to zero and cannot be freed twice.
            unsafe {
                cng::NCryptFreeObject(self.0);
            }
        }
    }
}

/// Opaque, cloneable in-memory reference to an owned key and its expected identity.
/// No public constructor, serializer, deserializer or name accessor is provided.
#[derive(Clone)]
pub struct KeyReference {
    name: Vec<u16>,
    public_sec1: [u8; 65],
    identity_sha256: [u8; 32],
}

/// User-scoped Microsoft Software KSP key; neither hardware nor enrollment proof.
pub struct SigningKey {
    // Field drop order releases the key before its provider.
    key: Key,
    _provider: Provider,
}

impl SigningKey {
    /// Creates a new unpredictable name without overwrite or machine-key flags.
    /// On later failure, attempts to delete this exact newly owned object.
    pub fn create_owned() -> Result<(Self, KeyReference), Error> {
        let name = random_name()?;
        let mut created = Self {
            key: Key(0),
            _provider: Provider::open()?,
        };
        // SAFETY: both output and terminated internal name are valid; flags zero
        // intentionally exclude overwrite and machine scope.
        check(
            unsafe {
                cng::NCryptCreatePersistedKey(
                    created._provider.0,
                    &mut created.key.0,
                    cng::NCRYPT_ECDSA_P256_ALGORITHM,
                    name.as_ptr(),
                    0,
                    0,
                )
            },
            "NCryptCreatePersistedKey",
        )?;

        let setup: Result<(Self, KeyReference), Error> = (|| {
            set_u32(created.key.0, cng::NCRYPT_EXPORT_POLICY_PROPERTY, 0)?;
            set_u32(
                created.key.0,
                cng::NCRYPT_KEY_USAGE_PROPERTY,
                cng::NCRYPT_ALLOW_SIGNING_FLAG,
            )?;
            // SAFETY: only this created key is finalized, after setting both policies.
            check(
                unsafe { cng::NCryptFinalizeKey(created.key.0, cng::NCRYPT_SILENT_FLAG) },
                "NCryptFinalizeKey",
            )?;
            #[cfg(test)]
            inject_creation_failure(&name)?;
            created.validate_policy()?;
            let public_sec1 = created.public_sec1()?;
            let reference = KeyReference {
                name,
                public_sec1,
                identity_sha256: sha256_sec1(&public_sec1)?,
            };
            // Read the persisted object back through a second, fully checked open
            // while retaining the original owned handle for failure cleanup.
            Ok((Self::reopen(&reference)?, reference))
        })();

        match setup {
            Ok(result) => Ok(result),
            Err(mut error) => {
                if let Err(cleanup) = created.key.delete() {
                    error.cleanup_failure = Some(cleanup.failure);
                }
                Err(error)
            }
        }
    }

    /// Opens only an opaque reference and checks policy and public identity.
    pub fn reopen(reference: &KeyReference) -> Result<Self, Error> {
        validate_name(&reference.name)?;
        let mut opened = Self {
            key: Key(0),
            _provider: Provider::open()?,
        };
        // SAFETY: the bounded name has one trailing NUL; output is exclusively owned.
        check(
            unsafe {
                cng::NCryptOpenKey(
                    opened._provider.0,
                    &mut opened.key.0,
                    reference.name.as_ptr(),
                    0,
                    cng::NCRYPT_SILENT_FLAG,
                )
            },
            "NCryptOpenKey",
        )?;
        opened.validate_policy()?;
        let public = opened.public_sec1()?;
        if public != reference.public_sec1 || sha256_sec1(&public)? != reference.identity_sha256 {
            return Err(Error::invalid("reference.public_identity"));
        }
        Ok(opened)
    }

    /// Deletes only after the same checked reopening used for access.
    pub fn delete(reference: &KeyReference) -> Result<(), Error> {
        let mut opened = Self::reopen(reference)?;
        opened.key.delete()
    }

    fn validate_policy(&self) -> Result<(), Error> {
        let algorithm = get_property::<22>(self.key.0, cng::NCRYPT_ALGORITHM_PROPERTY)?;
        let actual = algorithm
            .as_chunks::<2>()
            .0
            .iter()
            .map(|unit| u16::from_le_bytes(*unit));
        if !actual.eq("ECDSA_P256\0".encode_utf16())
            || get_u32(self.key.0, cng::NCRYPT_LENGTH_PROPERTY)? != 256
            || get_u32(self.key.0, cng::NCRYPT_EXPORT_POLICY_PROPERTY)? != 0
            || get_u32(self.key.0, cng::NCRYPT_KEY_USAGE_PROPERTY)?
                != cng::NCRYPT_ALLOW_SIGNING_FLAG
        {
            return Err(Error::invalid("key.algorithm_or_policy"));
        }
        Ok(())
    }

    /// Exports only the public P-256 point, as 0x04 || X || Y.
    pub fn public_sec1(&self) -> Result<[u8; 65], Error> {
        let mut blob = [0; 72];
        let mut written = 0;
        // SAFETY: fixed 8-byte ECC header plus two 32-byte coordinates; no private blob.
        check(
            unsafe {
                cng::NCryptExportKey(
                    self.key.0,
                    0,
                    cng::BCRYPT_ECCPUBLIC_BLOB,
                    null(),
                    blob.as_mut_ptr(),
                    72,
                    &mut written,
                    cng::NCRYPT_SILENT_FLAG,
                )
            },
            "NCryptExportKey.public",
        )?;
        let magic = u32::from_le_bytes([blob[0], blob[1], blob[2], blob[3]]);
        let coordinate_bytes = u32::from_le_bytes([blob[4], blob[5], blob[6], blob[7]]);
        if written != 72 || magic != cng::BCRYPT_ECDSA_PUBLIC_P256_MAGIC || coordinate_bytes != 32 {
            return Err(Error::invalid("public_blob.shape"));
        }
        let mut public = [0; 65];
        public[0] = 4;
        public[1..].copy_from_slice(&blob[8..]);
        Ok(public)
    }

    /// SHA256 of exactly the 65 public SEC1 bytes, using BCrypt.
    pub fn identity_sha256(&self) -> Result<[u8; 32], Error> {
        sha256_sec1(&self.public_sec1()?)
    }

    /// Signs an already hashed SHA256 digest, without rehashing or DER conversion.
    pub fn sign_digest(&self, digest: &[u8; 32]) -> Result<[u8; 64], Error> {
        let mut signature = [0; 64];
        let mut written = 0;
        // SAFETY: P-256 ECDSA consumes the fixed prehash and emits fixed P1363 r||s.
        check(
            unsafe {
                cng::NCryptSignHash(
                    self.key.0,
                    null(),
                    digest.as_ptr(),
                    32,
                    signature.as_mut_ptr(),
                    64,
                    &mut written,
                    cng::NCRYPT_SILENT_FLAG,
                )
            },
            "NCryptSignHash",
        )?;
        if written != 64 {
            return Err(Error::invalid("signature.length"));
        }
        Ok(signature)
    }

    /// Checks P1363 against the supplied prehash; only NTE_BAD_SIGNATURE is false.
    pub fn verify_digest(&self, digest: &[u8; 32], signature: &[u8; 64]) -> Result<bool, Error> {
        // SAFETY: both buffers have the exact P-256 sizes and remain live for the call.
        let status = unsafe {
            cng::NCryptVerifySignature(
                self.key.0,
                null(),
                digest.as_ptr(),
                32,
                signature.as_ptr(),
                64,
                cng::NCRYPT_SILENT_FLAG,
            )
        };
        if status == NTE_BAD_SIGNATURE {
            return Ok(false);
        }
        check(status, "NCryptVerifySignature")?;
        Ok(true)
    }
}

fn get_property<const N: usize>(
    key: cng::NCRYPT_KEY_HANDLE,
    property: PCWSTR,
) -> Result<[u8; N], Error> {
    let mut output = [0; N];
    let capacity = u32::try_from(N).map_err(|_| Error::invalid("property.capacity"))?;
    let mut written = 0;
    // SAFETY: callers supply static CNG property names and a writable bounded buffer.
    check(
        unsafe {
            cng::NCryptGetProperty(
                key,
                property,
                output.as_mut_ptr(),
                capacity,
                &mut written,
                0,
            )
        },
        "NCryptGetProperty",
    )?;
    if written != capacity {
        return Err(Error::invalid("property.length"));
    }
    Ok(output)
}

fn get_u32(key: cng::NCRYPT_KEY_HANDLE, property: PCWSTR) -> Result<u32, Error> {
    Ok(u32::from_le_bytes(get_property::<4>(key, property)?))
}

fn set_u32(key: cng::NCRYPT_KEY_HANDLE, property: PCWSTR, value: u32) -> Result<(), Error> {
    // SAFETY: each property expects this exact DWORD; it is persisted before finalize.
    check(
        unsafe {
            cng::NCryptSetProperty(
                key,
                property,
                value.to_le_bytes().as_ptr(),
                4,
                cng::NCRYPT_PERSIST_FLAG,
            )
        },
        "NCryptSetProperty",
    )
}

fn validate_name(name: &[u16]) -> Result<(), Error> {
    if name.len() != NAME_UNITS
        || name.last() != Some(&0)
        || !name[..NAME_PREFIX.len()]
            .iter()
            .copied()
            .eq(NAME_PREFIX.encode_utf16())
        || !name[NAME_PREFIX.len()..NAME_UNITS - 1]
            .iter()
            .all(|unit| matches!(*unit, 0x30..=0x39 | 0x61..=0x66))
    {
        return Err(Error::invalid("reference.name"));
    }
    Ok(())
}

fn random_name() -> Result<Vec<u16>, Error> {
    let mut random = [0; 16];
    // SAFETY: the system-preferred RNG accepts a null algorithm and a 16-byte buffer.
    check(
        unsafe {
            cng::BCryptGenRandom(
                null_mut(),
                random.as_mut_ptr(),
                16,
                cng::BCRYPT_USE_SYSTEM_PREFERRED_RNG,
            )
        },
        "BCryptGenRandom",
    )?;
    const HEX: &[u8; 16] = b"0123456789abcdef";
    let mut name = String::from(NAME_PREFIX);
    for byte in random {
        name.push(char::from(HEX[usize::from(byte >> 4)]));
        name.push(char::from(HEX[usize::from(byte & 15)]));
    }
    let name: Vec<u16> = name.encode_utf16().chain(Some(0)).collect();
    validate_name(&name)?;
    Ok(name)
}

struct HashAlgorithm(cng::BCRYPT_ALG_HANDLE);
struct Hash(cng::BCRYPT_HASH_HANDLE);

impl Drop for HashAlgorithm {
    fn drop(&mut self) {
        if !self.0.is_null() {
            // SAFETY: exclusively owned algorithm; hash locals are dropped first.
            unsafe {
                cng::BCryptCloseAlgorithmProvider(self.0, 0);
            }
        }
    }
}

impl Drop for Hash {
    fn drop(&mut self) {
        if !self.0.is_null() {
            // SAFETY: exclusively owned hash; CNG owns and frees its internal object buffer.
            unsafe {
                cng::BCryptDestroyHash(self.0);
            }
        }
    }
}

fn sha256_sec1(public: &[u8; 65]) -> Result<[u8; 32], Error> {
    let mut algorithm = HashAlgorithm(null_mut());
    // SAFETY: writable output and static SHA256 identifier, no custom provider or flags.
    check(
        unsafe {
            cng::BCryptOpenAlgorithmProvider(
                &mut algorithm.0,
                cng::BCRYPT_SHA256_ALGORITHM,
                null(),
                0,
            )
        },
        "BCryptOpenAlgorithmProvider",
    )?;
    let mut hash_length = [0; 4];
    let mut written = 0;
    // SAFETY: DWORD output buffer for the provider's fixed hash length.
    check(
        unsafe {
            cng::BCryptGetProperty(
                algorithm.0,
                cng::BCRYPT_HASH_LENGTH,
                hash_length.as_mut_ptr(),
                4,
                &mut written,
                0,
            )
        },
        "BCryptGetProperty.hash_length",
    )?;
    if written != 4 || u32::from_le_bytes(hash_length) != 32 {
        return Err(Error::invalid("hash.length"));
    }
    let mut hash = Hash(null_mut());
    // SAFETY: Windows 7+ CNG allocates the hash object when its buffer is null.
    // The hash is destroyed before the algorithm, including every failure path.
    check(
        unsafe { cng::BCryptCreateHash(algorithm.0, &mut hash.0, null_mut(), 0, null(), 0, 0) },
        "BCryptCreateHash",
    )?;
    // SAFETY: hash exactly the complete public SEC1 buffer, once.
    check(
        unsafe { cng::BCryptHashData(hash.0, public.as_ptr(), 65, 0) },
        "BCryptHashData",
    )?;
    let mut digest = [0; 32];
    // SAFETY: the output matches the checked provider hash length.
    check(
        unsafe { cng::BCryptFinishHash(hash.0, digest.as_mut_ptr(), 32, 0) },
        "BCryptFinishHash",
    )?;
    Ok(digest)
}

#[cfg(test)]
#[derive(Default)]
struct CreationFailure {
    armed: bool,
    name: Option<Vec<u16>>,
}

#[cfg(test)]
thread_local! {
    static CREATION_FAILURE: std::cell::RefCell<CreationFailure> = std::cell::RefCell::new(CreationFailure::default());
}

#[cfg(test)]
fn inject_creation_failure(name: &[u16]) -> Result<(), Error> {
    CREATION_FAILURE.with(|state| {
        let mut state = state.borrow_mut();
        if state.armed {
            state.armed = false;
            state.name = Some(name.to_vec());
            Err(Error::invalid("test.after_finalize"))
        } else {
            Ok(())
        }
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::ptr::{null, null_mut};
    use windows_sys::Win32::Security::Cryptography::*;

    // Test-only positive control. Its export policy deliberately fails production
    // reopening/deletion checks, so cleanup retains the exact created raw handle.
    struct ExportableControl {
        key: Key,
        provider: Provider,
        name: Vec<u16>,
    }

    impl ExportableControl {
        fn create() -> Result<Self, Error> {
            let provider = Provider::open()?;
            let name = random_name()?;
            let mut key = Key(0);
            // SAFETY: a fresh internal name, owned output, no overwrite/machine flag.
            check(
                unsafe {
                    NCryptCreatePersistedKey(
                        provider.0,
                        &mut key.0,
                        NCRYPT_ECDSA_P256_ALGORITHM,
                        name.as_ptr(),
                        0,
                        0,
                    )
                },
                "test.control.create",
            )?;
            let setup: Result<(), Error> = (|| {
                set_u32(
                    key.0,
                    NCRYPT_EXPORT_POLICY_PROPERTY,
                    NCRYPT_ALLOW_EXPORT_FLAG | NCRYPT_ALLOW_PLAINTEXT_EXPORT_FLAG,
                )?;
                set_u32(key.0, NCRYPT_KEY_USAGE_PROPERTY, NCRYPT_ALLOW_SIGNING_FLAG)?;
                // SAFETY: this test exclusively owns the created key.
                check(
                    unsafe { NCryptFinalizeKey(key.0, NCRYPT_SILENT_FLAG) },
                    "test.control.finalize",
                )
            })();
            if let Err(mut error) = setup {
                if let Err(cleanup) = key.delete() {
                    error.cleanup_failure = Some(cleanup.failure);
                }
                return Err(error);
            }
            Ok(Self {
                key,
                provider,
                name,
            })
        }

        fn cleanup_checked(&mut self) -> Result<(), Error> {
            self.key.delete()?;
            let mut reopened = Key(0);
            // SAFETY: bounded internal name and owned output; never deletes by name.
            let status = unsafe {
                NCryptOpenKey(
                    self.provider.0,
                    &mut reopened.0,
                    self.name.as_ptr(),
                    0,
                    NCRYPT_SILENT_FLAG,
                )
            };
            if status == windows_sys::Win32::Foundation::NTE_BAD_KEYSET {
                Ok(())
            } else if status == 0 {
                Err(Error::invalid("test.control.deleted_reopened"))
            } else {
                check(status, "test.control.deleted_reopen")
            }
        }
    }

    impl Drop for ExportableControl {
        fn drop(&mut self) {
            if self.key.0 != 0
                && let Err(error) = self.key.delete()
            {
                eprintln!("owned export-control cleanup failed: {error}");
                if !std::thread::panicking() {
                    panic!("owned export-control cleanup failed");
                }
            }
        }
    }

    fn private_size_query(key: NCRYPT_KEY_HANDLE) -> (i32, u32) {
        let mut size = 0;
        // SAFETY: identical size-only arguments for both owned keys; there is no
        // private-output buffer and this helper never requests private bytes.
        let status = unsafe {
            NCryptExportKey(
                key,
                0,
                BCRYPT_ECCPRIVATE_BLOB,
                null(),
                null_mut(),
                0,
                &mut size,
                0,
            )
        };
        (status, size)
    }

    fn cleanup_owned_checked(owned: &mut OwnedTestKey) -> Result<(), Error> {
        SigningKey::delete(owned.reference())?;
        match SigningKey::reopen(owned.reference()) {
            Err(error)
                if error.status() == Some(windows_sys::Win32::Foundation::NTE_BAD_KEYSET) =>
            {
                owned.reference.take();
                Ok(())
            }
            Err(error) => Err(error),
            Ok(reopened) => {
                drop(reopened);
                Err(Error::invalid("test.owned.deleted_reopened"))
            }
        }
    }

    // This is SHA256 of the empty message, independently fixed by FIPS 180-4.
    const EMPTY_DIGEST: [u8; 32] = [
        0xe3, 0xb0, 0xc4, 0x42, 0x98, 0xfc, 0x1c, 0x14, 0x9a, 0xfb, 0xf4, 0xc8, 0x99, 0x6f, 0xb9,
        0x24, 0x27, 0xae, 0x41, 0xe4, 0x64, 0x9b, 0x93, 0x4c, 0xa4, 0x95, 0x99, 0x1b, 0x78, 0x52,
        0xb8, 0x55,
    ];

    struct OwnedTestKey {
        reference: Option<KeyReference>,
    }

    impl OwnedTestKey {
        fn create() -> (SigningKey, Self) {
            let (key, reference) = SigningKey::create_owned().expect("create owned test key");
            (
                key,
                Self {
                    reference: Some(reference),
                },
            )
        }

        fn reference(&self) -> &KeyReference {
            self.reference.as_ref().expect("test still owns its key")
        }

        fn cleanup(mut self) {
            SigningKey::delete(self.reference()).expect("delete exact owned test key");
            let deleted = self.reference.take().expect("owned reference");
            assert!(
                SigningKey::reopen(&deleted).is_err(),
                "deleted key reopened"
            );
        }
    }

    impl Drop for OwnedTestKey {
        fn drop(&mut self) {
            if let Some(reference) = self.reference.take()
                && let Err(error) = SigningKey::delete(&reference)
            {
                eprintln!("owned test cleanup failed: {error}");
                if !std::thread::panicking() {
                    panic!("owned test cleanup failed");
                }
            }
        }
    }

    #[test]
    fn persists_public_identity_and_signing_only_nonexport_policy() {
        let (key, owned) = OwnedTestKey::create();
        let public = key.public_sec1().expect("public SEC1");
        let identity = key.identity_sha256().expect("identity digest");
        assert_eq!(public.len(), 65);
        assert_eq!(public[0], 4);
        drop(key);
        let reopened = SigningKey::reopen(owned.reference()).expect("reopen persistent key");
        assert_eq!(reopened.public_sec1().unwrap(), public);
        assert_eq!(reopened.identity_sha256().unwrap(), identity);
        assert_eq!(
            get_u32(reopened.key.0, NCRYPT_LENGTH_PROPERTY).unwrap(),
            256
        );
        assert_eq!(
            get_u32(reopened.key.0, NCRYPT_EXPORT_POLICY_PROPERTY).unwrap(),
            0
        );
        assert_eq!(
            get_u32(reopened.key.0, NCRYPT_KEY_USAGE_PROPERTY).unwrap(),
            NCRYPT_ALLOW_SIGNING_FLAG
        );
        drop(reopened);
        owned.cleanup();
    }

    #[test]
    fn valid_signature_passes_and_changed_digest_signature_and_wrong_key_fail() {
        let (key, owned) = OwnedTestKey::create();
        let (other, other_owned) = OwnedTestKey::create();
        let signature = key.sign_digest(&EMPTY_DIGEST).expect("sign digest");
        assert!(key.verify_digest(&EMPTY_DIGEST, &signature).unwrap());
        let mut changed_digest = EMPTY_DIGEST;
        changed_digest[0] ^= 1;
        assert!(!key.verify_digest(&changed_digest, &signature).unwrap());
        let mut changed_signature = signature;
        changed_signature[0] ^= 1;
        assert!(
            !key.verify_digest(&EMPTY_DIGEST, &changed_signature)
                .unwrap()
        );
        assert!(!other.verify_digest(&EMPTY_DIGEST, &signature).unwrap());
        drop(key);
        drop(other);
        owned.cleanup();
        other_owned.cleanup();
    }

    #[test]
    fn private_export_is_denied_without_requesting_private_bytes() {
        let (key, mut owned) = OwnedTestKey::create();
        let mut control = ExportableControl::create().expect("create exact owned export control");
        let negative_policy = get_u32(key.key.0, NCRYPT_EXPORT_POLICY_PROPERTY);
        let positive_policy = get_u32(control.key.0, NCRYPT_EXPORT_POLICY_PROPERTY);
        let positive_usage = get_u32(control.key.0, NCRYPT_KEY_USAGE_PROPERTY);
        let (negative_status, _) = private_size_query(key.key.0);
        let (positive_status, positive_size) = private_size_query(control.key.0);
        drop(key);
        // Complete both normal deletions and deleted-reopen checks before any
        // oracle/status assertion; a failed oracle cannot skip either cleanup.
        let negative_cleanup = cleanup_owned_checked(&mut owned);
        let positive_cleanup = control.cleanup_checked();
        assert!(
            negative_cleanup.is_ok(),
            "nonexportable cleanup failed: {negative_cleanup:?}"
        );
        assert!(
            positive_cleanup.is_ok(),
            "export-control cleanup failed: {positive_cleanup:?}"
        );
        assert_eq!(negative_policy.unwrap(), 0);
        assert_eq!(
            positive_policy.unwrap(),
            NCRYPT_ALLOW_EXPORT_FLAG | NCRYPT_ALLOW_PLAINTEXT_EXPORT_FLAG
        );
        assert_eq!(positive_usage.unwrap(), NCRYPT_ALLOW_SIGNING_FLAG);
        assert_eq!(
            positive_status, 0,
            "same-provider/blob size query must be supported"
        );
        assert_eq!(positive_size, 104);
        assert!(
            matches!(
                negative_status,
                windows_sys::Win32::Foundation::NTE_PERM
                    | windows_sys::Win32::Foundation::NTE_NOT_SUPPORTED
            ),
            "unexpected private-export status: {negative_status:#010x}"
        );
    }

    #[test]
    fn altered_reference_cannot_reopen_or_delete_the_real_key() {
        let (key, owned) = OwnedTestKey::create();
        let mut altered = owned.reference().clone();
        altered.public_sec1[1] ^= 1;
        assert!(SigningKey::reopen(&altered).is_err());
        assert!(SigningKey::delete(&altered).is_err());
        let still_present = SigningKey::reopen(owned.reference()).expect("real key preserved");
        assert_eq!(
            still_present.public_sec1().unwrap(),
            key.public_sec1().unwrap()
        );
        drop(still_present);
        drop(key);
        owned.cleanup();
    }

    #[test]
    fn failure_after_finalization_removes_the_exact_partial_key() {
        CREATION_FAILURE.with(|state| state.borrow_mut().armed = true);
        let error = match SigningKey::create_owned() {
            Ok((key, reference)) => {
                drop(key);
                SigningKey::delete(&reference).expect("cleanup unexpected creation");
                panic!("injected creation failure was ignored");
            }
            Err(error) => error,
        };
        assert_eq!(error.operation(), "test.after_finalize");
        assert!(
            error.cleanup_failure().is_none(),
            "partial-key deletion failed: {error}"
        );
        let name = CREATION_FAILURE.with(|state| state.borrow_mut().name.take().unwrap());
        let provider = Provider::open().unwrap();
        let mut raw = 0;
        let status =
            unsafe { NCryptOpenKey(provider.0, &mut raw, name.as_ptr(), 0, NCRYPT_SILENT_FLAG) };
        if status == 0 {
            let mut unexpected = Key(raw);
            unexpected
                .delete()
                .expect("cleanup leaked partial test key");
        }
        assert_eq!(status, windows_sys::Win32::Foundation::NTE_BAD_KEYSET);
    }

    #[test]
    fn emits_only_public_vector_for_independent_p1363_verification() {
        let (key, owned) = OwnedTestKey::create();
        let signature = key.sign_digest(&EMPTY_DIGEST).unwrap();
        let public = key.public_sec1().unwrap();
        let identity = key.identity_sha256().unwrap();
        let hex = |bytes: &[u8]| {
            bytes
                .iter()
                .map(|byte| format!("{byte:02x}"))
                .collect::<String>()
        };
        println!(
            "PUBLIC_CNG_VECTOR sec1={} identity={} signature={}",
            hex(&public),
            hex(&identity),
            hex(&signature)
        );
        assert!(key.verify_digest(&EMPTY_DIGEST, &signature).unwrap());
        drop(key);
        owned.cleanup();
    }

    #[test]
    fn altered_identity_digest_cannot_reopen_or_delete_the_real_key() {
        let (key, owned) = OwnedTestKey::create();
        let mut altered = owned.reference().clone();
        altered.identity_sha256[0] ^= 1;
        assert!(SigningKey::reopen(&altered).is_err());
        assert!(SigningKey::delete(&altered).is_err());
        let still_present = SigningKey::reopen(owned.reference()).expect("real key preserved");
        assert_eq!(
            still_present.public_sec1().unwrap(),
            key.public_sec1().unwrap()
        );
        drop(still_present);
        drop(key);
        owned.cleanup();
    }

    #[test]
    fn invalid_native_handle_is_an_error_instead_of_invalid_signature() {
        let invalid = SigningKey {
            key: Key(0),
            _provider: Provider::open().unwrap(),
        };
        let error = invalid.verify_digest(&EMPTY_DIGEST, &[0; 64]).unwrap_err();
        assert_eq!(
            error.status(),
            Some(windows_sys::Win32::Foundation::NTE_INVALID_HANDLE)
        );
    }
}
