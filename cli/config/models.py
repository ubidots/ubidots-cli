from cli.commons.models import BaseYAMLDumpModel
from cli.compat import StrEnum
from cli.settings import settings


class AuthHeaderTypeEnum(StrEnum):
    TOKEN = "X-Auth-Token"


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
