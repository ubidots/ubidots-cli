def build_variables_payload(**kwargs) -> dict:
    properties = kwargs.get("properties", {})
    if kwargs.get("min") is not None:
        properties["minimum_value"] = kwargs["min"]

    if kwargs.get("max") is not None:
        properties["maximum_value"] = kwargs["max"]

    data = {
        "description": kwargs.get("description", ""),
        "device": kwargs.get("device") or None,
        "type": kwargs.get("type"),
        "unit": kwargs.get("unit") or None,
        "synthetic_expression": kwargs.get("synthetic_expression", ""),
        "tags": kwargs.get("tags", "").split(",") if kwargs.get("tags") else [],
        "properties": properties,
    }
    if label := kwargs.get("label"):
        data["label"] = label
    if name := kwargs.get("name"):
        data["name"] = name

    return data
