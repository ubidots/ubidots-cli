PAGE_BASE_ENDPOINT = "/api/v2.0/pages"

PAGE_API_ROUTES = {
    "base": f"{PAGE_BASE_ENDPOINT}/",
    "detail": f"{PAGE_BASE_ENDPOINT}/{{page_key}}/",
    "code": f"{PAGE_BASE_ENDPOINT}/{{page_key}}/code/",
}
