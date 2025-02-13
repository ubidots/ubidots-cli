from enum import Enum


class InvalidOptionError(Exception):
    def __init__(
        self,
        invalid_option: str,
        valid_options: list[str] | type[Enum] | str,
        option_name: str = "option",
    ):
        self.invalid_option = invalid_option
        self.option_name = option_name

        if isinstance(valid_options, str):
            self.valid_options = [valid_options]
        elif isinstance(valid_options, type) and issubclass(valid_options, Enum):
            self.valid_options = [method.name for method in valid_options]
        else:
            self.valid_options = valid_options

    def __str__(self):
        valid_options_str = ", ".join(self.valid_options)
        return (
            f"'{self.invalid_option}' is not a valid {self.option_name}. "
            f"Valid options are: {valid_options_str}."
        )


class NoProfileError(Exception):
    def __str__(self):
        return "Profile not provided. Please provide a profile name."


class UnexistentProfileError(Exception):
    def __init__(self, profile: str):
        self.profile = profile
    def __str__(self):
        return f"Profile {self.profile} does not exist yet. Please provide a valid profile name."


class RuntimeNotFoundError(Exception):
    def __str__(self):
        return (
            "No runtimes were found. This may be due to an invalid or missing access token, "
            "or an incorrect API domain. Please verify that your token is set correctly and "
            "that you are using the correct API domain."
        )
