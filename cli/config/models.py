from __future__ import annotations

from pydantic import model_validator

from cli.auth.enums import TokenTypeEnum
from cli.commons.enums import OutputFormatFieldsEnum
from cli.commons.models import BaseYAMLDumpModel
from cli.config.enums import AuthHeaderTypeEnum
from cli.settings import settings

_OAUTH_FIELD_DEFAULTS = {
    "oauth_client_id": "",
    "refresh_token": "",
    "expires_at": 0,
    "scope": "",
    "token_type": TokenTypeEnum.BEARER,
}


class CliConfigModel(BaseYAMLDumpModel):
    profilesPath: str = settings.CONFIG.PROFILES_PATH
    ignoreFunctionsFile: str = settings.CONFIG.IGNORE_FUNCTIONS_FILE
    profile: str = settings.CONFIG.DEFAULT_PROFILE


class ProfileConfigModel(BaseYAMLDumpModel):
    api_domain: str = settings.CONFIG.API_DOMAIN
    auth_method: AuthHeaderTypeEnum = AuthHeaderTypeEnum.TOKEN
    access_token: str = ""
    containerRepositoryBase: str = settings.CONFIG.DEFAULT_CONTAINER_REPOSITORY
    runtimes: list[str] = settings.CONFIG.DEFAULT_RUNTIMES
    output_format: OutputFormatFieldsEnum = OutputFormatFieldsEnum.MACHINE
    oauth_client_id: str = ""
    refresh_token: str = ""
    expires_at: int = 0
    scope: str = ""
    token_type: str = TokenTypeEnum.BEARER

    @model_validator(mode="after")
    def _validate_oauth_fields(self) -> ProfileConfigModel:
        from cli.commons.exceptions import OAuthFieldsRequiredError

        if self.auth_method != AuthHeaderTypeEnum.OAUTH2:
            return self
        missing = [
            field
            for field in (
                "access_token",
                "refresh_token",
                "expires_at",
                "oauth_client_id",
            )
            if not getattr(self, field)
        ]
        if missing:
            raise OAuthFieldsRequiredError(missing_fields=missing)
        return self

    def to_yaml_serializable_format(self):
        data = super().to_yaml_serializable_format()
        if self.auth_method != AuthHeaderTypeEnum.OAUTH2:
            for field, default in _OAUTH_FIELD_DEFAULTS.items():
                if data.get(field) == default:
                    data.pop(field, None)
        return data
