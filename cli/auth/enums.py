from enum import StrEnum


class CodeChallengeMethodEnum(StrEnum):
    S256 = "S256"
    PLAIN = "plain"


class TokenTypeEnum(StrEnum):
    BEARER = "Bearer"
    BASIC = "Basic"


class ResponseTypeEnum(StrEnum):
    CODE = "code"
    TOKEN = "token"
    ID_TOKEN = "id_token"


class GrantTypeEnum(StrEnum):
    AUTHORIZATION_CODE = "authorization_code"
    REFRESH_TOKEN = "refresh_token"
    CLIENT_CREDENTIALS = "client_credentials"
