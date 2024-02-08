from enum import Enum

from cli.commons.models import BaseYAMLDumpModel
from cli.settings import settings


class AuthHeaderType(Enum):
    TOKEN = "X-Auth-Token"


class APIConfigModel(BaseYAMLDumpModel):
    api_domain: str = settings.CONFIG.API_DOMAIN
    auth_method: AuthHeaderType = AuthHeaderType.TOKEN
    access_token: str
