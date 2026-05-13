from enum import StrEnum


class AuthHeaderTypeEnum(StrEnum):
    TOKEN = "X-Auth-Token"
    OAUTH2 = "Authorization"
