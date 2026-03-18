FUNCTION_BASE_ENDPOINT = "/api/-/functions"
DEFAULT_RUNTIME = "nodejs20.x:lite"

# Well-known runtime strings used across tests and documentation
PYTHON_3_9_BASE_RUNTIME = "python3.9:base"
PYTHON_3_9_FULL_RUNTIME = "python3.9:full"
PYTHON_3_9_LITE_RUNTIME = "python3.9:lite"
PYTHON_3_11_LITE_RUNTIME = "python3.11:lite"

FUNCTION_API_ROUTES = {
    "base": FUNCTION_BASE_ENDPOINT,
    "detail": f"{FUNCTION_BASE_ENDPOINT}/{{function_key}}",
    "logs": f"{FUNCTION_BASE_ENDPOINT}/{{function_key}}/logs",
    "zip_file": f"{FUNCTION_BASE_ENDPOINT}/{{function_key}}/zip-file",
}
