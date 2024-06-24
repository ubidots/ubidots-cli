FUNCTION_BASE_ENDPOINT = "/api/-/functions"

FUNCTION_API_ROUTES = {
    "base": FUNCTION_BASE_ENDPOINT,
    "detail": f"{FUNCTION_BASE_ENDPOINT}/{{function_key}}",
    "logs": f"{FUNCTION_BASE_ENDPOINT}/{{function_key}}/logs",
    "zip_file": f"{FUNCTION_BASE_ENDPOINT}/{{function_key}}/zip-file",
}
