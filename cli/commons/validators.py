import json
import re

import typer


def is_valid_object_id(key: str) -> bool:
    object_id_regex = re.compile(r"[0-9a-fA-F]{24}")
    try:
        match = object_id_regex.search(key)
        if match is None:
            return False
        return len(key) == 24 and len(key) == len(match.group())
    except (ValueError, TypeError):
        return False


def is_valid_json_string(value: str) -> dict:
    try:
        return json.loads(value)
    except json.JSONDecodeError as error:
        error_message = "Invalid JSON format. Please provide a valid JSON string."
        raise typer.BadParameter(error_message) from error
