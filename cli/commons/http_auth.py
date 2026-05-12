from cli.config.models import AuthHeaderTypeEnum
from cli.config.models import ProfileConfigModel


def get_auth_headers(config: ProfileConfigModel) -> dict[str, str]:
    if config.auth_method == AuthHeaderTypeEnum.OAUTH2:
        return {
            "Authorization": f"Bearer {config.access_token}",
            "Content-Type": "application/json",
        }
    return {
        AuthHeaderTypeEnum.TOKEN.value: config.access_token,
        "Content-Type": "application/json",
    }


def get_token_auth_headers(access_token: str) -> dict[str, str]:
    return {
        AuthHeaderTypeEnum.TOKEN.value: access_token,
        "Content-Type": "application/json",
    }
