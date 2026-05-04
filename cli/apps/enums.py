from cli.compat import StrEnum


class MenuAlignmentEnum(StrEnum):
    LEFT = "left"
    RIGHT = "right"


class MenuModeEnum(StrEnum):
    CUSTOM = "custom"
    DEFAULT = "default"
