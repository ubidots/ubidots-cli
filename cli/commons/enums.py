from cli.compat import StrEnum


class MessageColorEnum(StrEnum):
    WARNING = "bright_yellow"
    SUCCESS = "bright_green"
    ERROR = "bright_red"
    INFO = "bright_blue"
    HINT = "bright_magenta"


class TableColorEnum(StrEnum):
    BRIGHT_RED = "bright_red"
    GREEN = "green"
    BRIGHT_BLUE = "bright_blue"
    MAGENTA = "magenta"
    CYAN = "cyan"
    YELLOW = "yellow"
    BRIGHT_YELLOW = "bright_yellow"
    BRIGHT_MAGENTA = "bright_magenta"


class EntityNameEnum(StrEnum):
    DEVICE = "device"
    VARIABLE = "variable"
    EVENT = "event"
    DASHBOARD = "dashboard"
    REPORT = "report"
    APP = "app"
    GROUP = "device_group"
    TYPES = "device_type"
    FUNCTION = "function"
    PLUGIN = "plugin"


class DefaultInstanceFieldEnum(StrEnum):
    ID = "id"
    LABEL = "label"
    NAME = "name"

    @classmethod
    def get_default_fields(cls) -> str:
        return f"{cls.ID},{cls.LABEL},{cls.NAME}"


class OutputFormatFieldsEnum(StrEnum):
    TABLE = "table"
    JSON = "json"

    @classmethod
    def get_default_format(cls) -> "OutputFormatFieldsEnum":
        return cls.TABLE
