import sys

if sys.version_info >= (3, 11):  # noqa: UP036
    from enum import StrEnum
else:
    from enum import Enum

    class StrEnum(str, Enum):
        def __str__(self):
            return self.value
