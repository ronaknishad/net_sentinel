class NotFoundError(LookupError):
    """Requested record does not exist."""


class ConflictError(RuntimeError):
    """Request conflicts with current state (for example a training job is already running)."""


class BadRequestError(ValueError):
    """Request is well-formed but its values are not acceptable."""


class PayloadTooLargeError(ValueError):
    """Uploaded file exceeds the size limit."""
