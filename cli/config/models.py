from enum import Enum

from pydantic import BaseModel

from cli import settings


class AuthHeaderType(Enum):
    TOKEN = "X-Auth-Token"


class APIConfigModel(BaseModel):
    api_domain: str = settings.UBIDOTS_API_DOMAIN
    auth_method: AuthHeaderType = AuthHeaderType.TOKEN
    access_token: str

    def for_yaml_dump(self):
        data = self.model_dump()
        data["auth_method"] = self.auth_method.value
        return data
