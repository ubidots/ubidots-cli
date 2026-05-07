APPS_BASE_ENDPOINT = "/api/-/apps"
APPS_API_ROUTES = {
    "base": APPS_BASE_ENDPOINT,
    "detail": f"{APPS_BASE_ENDPOINT}/{{app_key}}",
    "menu": f"{APPS_BASE_ENDPOINT}/{{app_key}}/menu",
}
