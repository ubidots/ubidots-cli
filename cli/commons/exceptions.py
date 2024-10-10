from enum import Enum


class InvalidOptionError(Exception):
    def __init__(
        self,
        invalid_option: str,
        valid_options: list | type[Enum],
        option_name: str = "option",
    ):
        if isinstance(valid_options, type) and issubclass(valid_options, Enum):
            valid_options = [method.name for method in valid_options]

        valid_options_str = ", ".join(valid_options)
        error_message = (
            f"'{invalid_option}' is not a valid {option_name}. "
            f"Valid options are: {valid_options_str}."
        )
        super().__init__(error_message)
