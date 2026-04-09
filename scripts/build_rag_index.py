from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.rag_store import build_index  # noqa: E402


def main() -> None:
    result = build_index(force_rebuild=False)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
