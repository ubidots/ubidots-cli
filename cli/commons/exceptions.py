from enum import Enum


class InvalidOptionError(Exception):
    def __init__(
        self,
        invalid_option: str,
        valid_options: list | type[Enum],
        option_name: str = "option",
    ):
        self.invalid_option = invalid_option
        self.option_name = option_name

        if isinstance(valid_options, type) and issubclass(valid_options, Enum):
            self.valid_options = [method.name for method in valid_options]
        else:
            self.valid_options = valid_options

    def __str__(self):
        valid_options_str = ", ".join(self.valid_options)
        return (
            f"'{self.invalid_option}' is not a valid {self.option_name}. "
            f"Valid options are: {valid_options_str}."
        )
