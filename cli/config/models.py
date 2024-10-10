from cli.commons.models import BaseYAMLDumpModel
from cli.compat import StrEnum
from cli.settings import settings


class AuthHeaderTypeEnum(StrEnum):
    TOKEN = "X-Auth-Token"


class APIConfigModel(BaseYAMLDumpModel):
    api_domain: str = settings.CONFIG.API_DOMAIN
    auth_method: AuthHeaderTypeEnum = AuthHeaderTypeEnum.TOKEN
    access_token: str = ""
