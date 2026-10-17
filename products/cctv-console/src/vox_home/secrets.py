"""Core-only, exact device/adapter credential delivery to an authorized host.

References come from trusted core configuration, never a plugin payload. The
injected provider reads one configured target; this broker never enumerates a
vault. No material is written to CLI arguments, environment, storage or logs.
An authorized worker can know material required by its protocol. This is not
protection against malicious code running as the same Windows user; separate
processes also require OS ACLs and separate network and secret permissions.
"""

from collections.abc import Callable

from .access import AccessContext, AccessDenied, AccessService
from .contracts import ContractValidationError, _epoch, _identifier, _text


class SecretBrokerError(PermissionError):
    """A safe code only; provider exceptions and private inputs are discarded."""

    _CODES = frozenset({
        "invalid_request", "invalid_configuration", "access_denied",
        "secret_not_approved", "provider_failed", "invalid_material",
    })

    def __init__(self, code: str = "invalid_request"):
        self.code = code if type(code) is str and code in self._CODES else "invalid_request"
        super().__init__(self.code)


class _PrivateRecord:
    """Read-only, non-serializable records without an exportable __dict__."""

    __slots__ = ()

    def __setattr__(self, name, value):
        raise AttributeError("private_record_is_read_only")

    def __delattr__(self, name):
        raise AttributeError("private_record_is_read_only")

    def __reduce_ex__(self, protocol):
        raise TypeError("private_record_not_serializable")

    def __getstate__(self):
        raise TypeError("private_record_not_serializable")


class SecretRef(_PrivateRecord):
    """A trusted core binding; the provider key is intentionally opaque to IPC."""

    __slots__ = ("site_id", "device_id", "adapter_id", "provider_key")

    def __init__(self, site_id: str, device_id: str, adapter_id: str, provider_key: str):
        valid = True
        try:
            for name, value in (("site_id", site_id), ("device_id", device_id),
                                ("adapter_id", adapter_id)):
                if type(value) is not str:
                    valid = False
                    break
                _identifier(value, name)
            if type(provider_key) is not str:
                valid = False
            else:
                _text(provider_key, "provider_key")
        except ContractValidationError:
            valid = False
        if not valid:
            raise SecretBrokerError("invalid_configuration")
        for name, value in (("site_id", site_id), ("device_id", device_id),
                            ("adapter_id", adapter_id), ("provider_key", provider_key)):
            object.__setattr__(self, name, value)

    def __repr__(self):
        return "SecretRef(<redacted>)"


class SecretMaterial(_PrivateRecord):
    """In-memory protocol material, readable only through this explicit API."""

    __slots__ = ("kind", "value")

    def __init__(self, kind: str, value: str):
        valid = type(kind) is str and type(value) is str
        if valid:
            try:
                _identifier(kind, "kind")
                _text(value, "value")
            except ContractValidationError:
                valid = False
        if not valid:
            raise SecretBrokerError("invalid_material")
        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "value", value)

    def __repr__(self):
        return "SecretMaterial(<redacted>)"


class SecretBroker:
    """Bind authorization to a copied, validated core credential configuration.

    ``resolve_for_worker`` is called by the trusted host after binding its
    adapter/device to the approved manifest. It is not a worker IPC command.
    The provider may be integrated with the native Windows exact-target reader
    later; it must return SecretMaterial and must never enumerate credentials.
    """

    __slots__ = ("_access", "_approved_refs", "_provider")

    def __init__(self, access: AccessService,
                 approved_refs: dict[tuple[str, str, str], SecretRef],
                 provider: Callable[[SecretRef], SecretMaterial]):
        if (type(access) is not AccessService or type(approved_refs) is not dict
                or not callable(provider)):
            raise SecretBrokerError("invalid_configuration")
        copied = {}
        for key, ref in approved_refs.items():
            if (type(key) is not tuple or len(key) != 3
                    or any(type(part) is not str for part in key)
                    or type(ref) is not SecretRef):
                raise SecretBrokerError("invalid_configuration")
            # Revalidate and copy the record as well as the input dictionary.
            copied_ref = SecretRef(ref.site_id, ref.device_id, ref.adapter_id, ref.provider_key)
            if key != (copied_ref.site_id, copied_ref.device_id, copied_ref.adapter_id):
                raise SecretBrokerError("invalid_configuration")
            copied[key] = copied_ref
        self._access = access
        self._approved_refs = copied
        self._provider = provider

    def resolve_for_worker(self, context: AccessContext, adapter_id: str,
                           device_id: str, now: float) -> SecretMaterial:
        valid = type(context) is AccessContext and type(adapter_id) is str and type(device_id) is str
        if valid:
            try:
                _identifier(adapter_id, "adapter_id")
                _identifier(device_id, "device_id")
                _epoch(now, "now")
            except ContractValidationError:
                valid = False
        if not valid:
            raise SecretBrokerError("invalid_request")

        denied = False
        try:
            self._access.require(context, device_id, "credential_use", now)
        except AccessDenied:
            denied = True
        if denied:
            raise SecretBrokerError("access_denied")

        ref = self._approved_refs.get((context.site_id, device_id, adapter_id))
        if ref is None:
            raise SecretBrokerError("secret_not_approved")

        failed = False
        try:
            material = self._provider(ref)
        except Exception:
            # Raise outside the except block so no sensitive exception context
            # survives, even for a caller that inspects __context__ explicitly.
            failed = True
        if failed:
            raise SecretBrokerError("provider_failed")
        if type(material) is not SecretMaterial:
            raise SecretBrokerError("invalid_material")
        return material
