"""Export the OpenAPI spec as a standalone JSON file.

Usage:
    python -m tradeshow.api.export_spec
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tradeshow.api.app import app

OUTPUT_DIR = Path(__file__).parent.parent / "lovable-reference"


def export():
    spec = app.openapi()

    # Save to api/ directory
    api_path = Path(__file__).parent / "openapi.json"
    with open(api_path, "w") as f:
        json.dump(spec, f, indent=2)
    print(f"Wrote {api_path} ({len(spec['paths'])} paths, {len(spec.get('components',{}).get('schemas',{}))} schemas)")

    # Also copy to lovable-reference/
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ref_path = OUTPUT_DIR / "openapi.json"
    with open(ref_path, "w") as f:
        json.dump(spec, f, indent=2)
    print(f"Wrote {ref_path}")


if __name__ == "__main__":
    export()
