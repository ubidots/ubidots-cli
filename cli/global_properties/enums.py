from cli.compat import StrEnum


class PropertyFormatEnum(StrEnum):
    STRING = "string"
    INT = "int"
    FLOAT = "float"
    BOOL = "bool"
    JSON = "json"
