import json
from pathlib import Path
from typing import Any


def load_json_file(path: Path) -> Any:
    """Load and deserialize a JSON file."""
    with open(path, "rb") as file:
        return json.load(file)
