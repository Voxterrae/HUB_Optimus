"""Local zone labels and sanitised, dated capability observations.

Capabilities require observation of the explicitly configured installation.
Editable labels never change recorder titles, channel IDs or capability facts.
"""
import json
from pathlib import Path
import unicodedata

DEFAULT_ZONES = {i: f'Zona {i}' for i in range(1, 8)}
MAX_METADATA_BYTES = 8192


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate metadata key')
        result[key] = value
    return result


def load_zones(path):
    """Load strict, bounded local labels; reject the entire file on invalidity."""
    try:
        path = Path(path)
        if path.is_symlink() or getattr(path, 'is_junction', lambda: False)():
            raise ValueError('Linked metadata')
        with path.open('rb') as handle:
            raw = handle.read(MAX_METADATA_BYTES + 1)
        if len(raw) > MAX_METADATA_BYTES:
            raise ValueError('Metadata exceeds limit')
        document = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique_object)
        if not isinstance(document, dict) or set(document) != {'schema_version', 'zones'} or type(document['schema_version']) is not int or document['schema_version'] != 1:
            raise ValueError('Invalid metadata schema')
        labels = document['zones']
        if not isinstance(labels, dict) or set(labels) != {str(i) for i in DEFAULT_ZONES}:
            raise ValueError('Invalid camera labels')
        for label in labels.values():
            if not isinstance(label, str) or not 1 <= len(label) <= 64 or label != label.strip() or any(unicodedata.category(char).startswith('C') for char in label):
                raise ValueError('Invalid zone label')
        return {int(camera): label for camera, label in labels.items()}
    except (OSError, ValueError, TypeError, RecursionError):
        return dict(DEFAULT_ZONES)


def camera_label(zones, camera):
    return f'C{camera} · {zones[camera]}' if camera in zones else 'Grabador'


def capability_info(camera=None):
    """No installation-specific capability is asserted by the distribution."""
    return 'Capacidades del equipo: sin verificar en esta instalación'
