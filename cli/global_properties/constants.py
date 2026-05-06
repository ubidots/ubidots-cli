GLOBAL_PROPERTIES_BASE_ENDPOINT = "/api/v2.0/account/_/properties"
GLOBAL_PROPERTIES_API_ROUTES = {
    "base": f"{GLOBAL_PROPERTIES_BASE_ENDPOINT}/",
    "detail": f"{GLOBAL_PROPERTIES_BASE_ENDPOINT}/{{property_key}}/",
}
