from enum import Enum
from pathlib import Path


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
        return f"Profile '{self.profile}' does not exist yet. Please provide a valid profile name."


class InvalidProfileError(Exception):
    def __init__(self, profile: str, exception: Exception):
        self.profile = profile
        self.exception = exception

    def __str__(self):
        return f"Profile {self.profile} is invalid. Make sure the profile is correctly configured. {self.exception}"


class ProfileConfigMissingFieldsError(Exception):
    def __init__(self, profile_file: Path, missing_fields: set):
        self.profile_file = profile_file
        self.missing_fields = missing_fields

    def __str__(self):
        return f"Missing required fields in {self.profile_file}: {', '.join(self.missing_fields)}"


class ProfileConfigEmptyFieldsError(Exception):
    def __init__(self, profile_file: Path, empty_fields: set):
        self.profile_file = profile_file
        self.empty_fields = empty_fields

    def __str__(self):
        return f"Required field(s) empty in {self.profile_file}: {', '.join(self.empty_fields)}"


class CurrentPlanDoesNotIncludeRuntimes(Exception):
    def __str__(self):
        return (
            "The current plan does not include the 'runtimes' feature. "
            "Please upgrade your plan to use this feature."
        )


class EmptyTokenError(Exception):
    def __str__(self):
        return "Access token is empty. Please provide a valid access token."


class OAuthFieldsRequiredError(Exception):
    def __init__(self, missing_fields: list[str]):
        self.missing_fields = missing_fields

    def __str__(self):
        joined = ", ".join(self.missing_fields)
        return (
            f"Profile uses auth_method=OAUTH2 but is missing required OAuth fields: {joined}. "
            "Run 'ubidots login' to populate them."
        )


class AuthorizationDeniedError(Exception):
    def __str__(self):
        return "Authorization denied"


class LoginTimeoutError(Exception):
    def __str__(self):
        return "Login timed out — run again"


class CSRFMismatchError(Exception):
    def __str__(self):
        return "CSRF mismatch — possible attack, aborting"


class UnknownOAuthClientError(Exception):
    def __str__(self):
        return "Unknown OAuth client. Verify with your DevOps team."


class TokenExchangeError(Exception):
    def __init__(self, detail: str = ""):
        self.detail = detail

    def __str__(self):
        if self.detail:
            return f"Failed to exchange authorization code for tokens: {self.detail}"
        return "Failed to exchange authorization code for tokens."


class RefreshTokenExpiredError(Exception):
    def __str__(self):
        return "Your session has expired. Please run 'ubidots login' again."


class RefreshFailedError(Exception):
    def __init__(self, detail: str = ""):
        self.detail = detail

    def __str__(self):
        return f"Could not refresh session: {self.detail or 'unknown error'}"


class CoreUnreachableError(Exception):
    def __init__(self, api_domain: str):
        self.api_domain = api_domain

    def __str__(self):
        return f"Cannot reach Ubidots core at {self.api_domain}. Check your network."


class RefreshLockBusyError(Exception):
    def __str__(self):
        return "Another ubidots command is currently refreshing the session, please retry."


class ContainerNotFoundError(Exception):
    """Raised by base Docker classes when a container cannot be found by label."""

    def __init__(self, label: str):
        super().__init__(f"Container '{label}' not found")


class ContainerAlreadyRunningException(Exception):
    def __init__(self, container_name: str):
        super().__init__(f"Container '{container_name}' is already running")


class ContainerExecutionException(Exception):
    def __init__(self, message: str = "Container execution failed"):
        super().__init__(message)
