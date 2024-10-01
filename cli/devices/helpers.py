def build_devices_payload(**kwargs) -> dict:
    data = {
        "description": kwargs.get("description", ""),
        "organization": kwargs.get("organization") or None,
        "tags": kwargs.get("tags", "").split(",") if kwargs.get("tags") else [],
        "properties": kwargs.get("properties", {}),
    }
    if label := kwargs.get("label"):
        data["label"] = label
    if name := kwargs.get("name"):
        data["name"] = name

    return data
