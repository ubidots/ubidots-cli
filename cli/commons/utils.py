from cli.config.helpers import read_cli_configuration


def build_endpoint(route: str, **kwargs) -> str:
    access_config = read_cli_configuration()
    url = f"{access_config.api_domain}{route.format(**kwargs)}"
    headers = {access_config.auth_method.value: access_config.access_token}
    return url, headers
