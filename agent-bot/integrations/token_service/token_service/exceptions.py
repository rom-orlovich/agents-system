class TokenServiceError(Exception):
    pass


class InstallationNotFoundError(TokenServiceError):
    pass


class TokenExpiredError(TokenServiceError):
    pass


class TokenRefreshError(TokenServiceError):
    pass
