from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings

settings = get_settings()

# In-memory storage — single-process. Fine for local dev and single-worker uvicorn.
# For multi-worker deployments, swap storage_uri to a shared backend.
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"],
    headers_enabled=True,
)
