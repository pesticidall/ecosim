import json
from pathlib import Path
from typing import Any


def load_json_file(file_path: Path) -> dict[str, Any]:
    with file_path.open("r", encoding="utf-8") as file:
        loaded_data = json.load(file)
        if not isinstance(loaded_data, dict):
            raise TypeError(
                f"Top-level JSON value in '{file_path}' must be an object."
            )
        return loaded_data