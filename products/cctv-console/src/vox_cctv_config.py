"""Explicit installation binding; imports perform no network or vault access."""
import ipaddress
import os

RECORDER_IP = os.environ.get('HUB_OPTIMUS_CCTV_HOST', '127.0.0.1')
RECORDER_SERIAL = os.environ.get('HUB_OPTIMUS_CCTV_SERIAL', 'unconfigured')
CREDENTIAL_TARGET = os.environ.get('HUB_OPTIMUS_CCTV_CREDENTIAL_TARGET', 'unconfigured')

def require_configuration():
    try:
        address = ipaddress.IPv4Address(RECORDER_IP)
        configured = address.is_private and not address.is_loopback and not address.is_unspecified and not address.is_multicast
        configured = configured and RECORDER_IP == str(address)
        for value in (RECORDER_SERIAL, CREDENTIAL_TARGET):
            configured = configured and isinstance(value, str) and 1 <= len(value) <= 256
            configured = configured and value not in ('unconfigured',) and value == value.strip()
            configured = configured and not any(ord(char) < 32 or ord(char) == 127 for char in value)
    except (ValueError, TypeError):
        configured = False
    if not configured:
        raise ValueError('installation_configuration_required')
