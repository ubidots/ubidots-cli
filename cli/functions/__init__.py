BASE_ENDPOINT = "/api/-/functions"

API_ROUTES = {
    "base": BASE_ENDPOINT,
    "detail": f"{BASE_ENDPOINT}/{{function_key}}",
    "zip_file": f"{BASE_ENDPOINT}/{{function_key}}/zip-file",
}
