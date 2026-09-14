from __future__ import annotations

import json
from pathlib import Path

from optimus_admin_gateway.main import app

output = Path(__file__).parents[1] / "openapi" / "optimus-admin-gateway.openapi.json"
output.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(output)
