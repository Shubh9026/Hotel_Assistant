import json
from pathlib import Path


def load_json(path: str):
    file = Path(path)

    if not file.exists():
        return {}

    # Some files may be created by Windows tools with a UTF-8 BOM (e.g. PowerShell).
    with open(file, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_json(path: str, data: dict):
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)

    with open(file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def append_json_list(path: str, record: dict):
    """
    Append a single record to a JSON file that stores a top-level list.

    Creates the file if missing. If the existing file is not a list, it will be
    replaced with a new list containing only the appended record.
    """
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)

    if file.exists():
        try:
            with open(file, "r", encoding="utf-8") as f:
                current = json.load(f)
        except Exception:
            current = []
    else:
        current = []

    if not isinstance(current, list):
        current = []

    current.append(record)

    with open(file, "w", encoding="utf-8") as f:
        json.dump(current, f, indent=2)
