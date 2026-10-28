"""Product-only import path and explicit synthetic recorder binding."""
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / 'src'))
os.environ.setdefault('HUB_OPTIMUS_CCTV_HOST', '10.20.30.40')
os.environ.setdefault('HUB_OPTIMUS_CCTV_SERIAL', 'unit-test-recorder')
os.environ.setdefault('HUB_OPTIMUS_CCTV_CREDENTIAL_TARGET', 'example/testing/recorder')
