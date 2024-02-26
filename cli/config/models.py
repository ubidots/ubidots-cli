from enum import StrEnum

from cli.commons.models import BaseYAMLDumpModel
from cli.settings import settings


class AuthHeaderType(StrEnum):
    TOKEN = "X-Auth-Token"


class APIConfigModel(BaseYAMLDumpModel):
    api_domain: str = settings.CONFIG.API_DOMAIN
    auth_method: AuthHeaderType = AuthHeaderType.TOKEN
    access_token: str
