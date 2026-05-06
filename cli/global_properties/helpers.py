import json

import typer

from cli.global_properties.enums import PropertyFormatEnum


def coerce_value(raw: str, value_format: PropertyFormatEnum) -> object:
    if value_format == PropertyFormatEnum.STRING:
        return raw
    if value_format == PropertyFormatEnum.INT:
        try:
            return int(raw)
        except ValueError as e:
            msg = f"--value '{raw}' is not a valid integer for --format int."
            raise typer.BadParameter(msg) from e
    if value_format == PropertyFormatEnum.FLOAT:
        try:
            return float(raw)
        except ValueError as e:
            msg = f"--value '{raw}' is not a valid float for --format float."
            raise typer.BadParameter(msg) from e
    if value_format == PropertyFormatEnum.BOOL:
        normalized = raw.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no"}:
            return False
        msg = f"--value '{raw}' is not a valid boolean for --format bool (use true/false)."
        raise typer.BadParameter(msg)
    if value_format == PropertyFormatEnum.JSON:
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            msg = f"--value is not valid JSON for --format json: {e}."
            raise typer.BadParameter(msg) from e
    msg = f"Unsupported --format: {value_format}"
    raise typer.BadParameter(msg)


def parse_scope(raw: str) -> list[str]:
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def build_add_payload(
    label: str,
    value_format: PropertyFormatEnum,
    value: str,
    name: str,
    description: str,
    scope: str,
    is_secret: bool,
) -> dict:
    payload: dict = {
        "label": label,
        "format": str(value_format),
        "value": coerce_value(value, value_format),
        "isSecret": is_secret,
    }
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    parsed_scope = parse_scope(scope)
    if parsed_scope:
        payload["scope"] = parsed_scope
    return payload


def build_update_payload(
    value: str | None,
    value_format: PropertyFormatEnum | None,
    name: str,
    description: str,
    scope: str | None,
    is_secret: bool | None,
) -> dict:
    payload: dict = {}
    if value is not None:
        if value_format is None:
            msg = "When passing --value, also pass --format to disambiguate the value type."
            raise typer.BadParameter(msg)
        payload["value"] = coerce_value(value, value_format)
        payload["format"] = str(value_format)
    if name:
        payload["name"] = name
    if description:
        payload["description"] = description
    if scope is not None:
        payload["scope"] = parse_scope(scope)
    if is_secret is not None:
        payload["isSecret"] = is_secret
    return payload
