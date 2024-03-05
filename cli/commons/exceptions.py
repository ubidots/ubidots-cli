class HttpRequestException(Exception):
    def __init__(self, message: str = "Connection error, no response from the server."):
        super().__init__(message)


class HttpMaxAttemptsRequestException(Exception):
    def __init__(self, attemps: int):
        message = (
            f"Could not connect to the service after several attempts ({attemps})."
        )
        super().__init__(message)
