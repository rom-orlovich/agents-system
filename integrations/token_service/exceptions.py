class TokenServiceError(Exception):
    pass


class InstallationNotFoundError(TokenServiceError):
    def __init__(self, platform: str, organization_id: str):
        self.platform = platform
        self.organization_id = organization_id
        super().__init__(
            f"Installation not found: platform={platform}, org={organization_id}"
        )


class TokenExpiredError(TokenServiceError):
    def __init__(self, installation_id: str):
        self.installation_id = installation_id
        super().__init__(f"Token expired for installation: {installation_id}")


class TokenRefreshError(TokenServiceError):
    def __init__(self, installation_id: str, reason: str):
        self.installation_id = installation_id
        self.reason = reason
        super().__init__(
            f"Token refresh failed for {installation_id}: {reason}"
        )


class DuplicateInstallationError(TokenServiceError):
    def __init__(self, platform: str, organization_id: str):
        self.platform = platform
        self.organization_id = organization_id
        super().__init__(
            f"Installation already exists: platform={platform}, org={organization_id}"
        )
