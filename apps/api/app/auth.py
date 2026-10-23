"""Development-only write authorization for eCare API.

This module provides an authorization-ready dependency that denies write
operations by default. Write access is only granted when the explicit
development-mode flag is set via the ECARE_DEV_MODE environment variable.

This is NOT production authentication. It is a development guardrail to
prevent unrestricted write endpoints from being exposed before a proper
authentication and authorization system is implemented.

Do not hardcode admin credentials or implement fake authentication here.
"""

import os
from typing import Optional

from fastapi import HTTPException, Header, status


def require_write_access(
    x_ecare_dev_mode: Optional[str] = Header(None, alias="X-Ecare-Dev-Mode"),
) -> None:
    """Dependency that grants write access only in development mode.

    Access is granted when either:
    - The ECARE_DEV_MODE environment variable is set to "true", or
    - The X-Ecare-Dev-Mode: true header is sent with the request.

    Otherwise, a 403 Forbidden response is returned.

    This is intentionally strict: by default, all write operations are
    denied. Public read-only endpoints are not protected by this dependency.
    """
    dev_mode = os.environ.get("ECARE_DEV_MODE", "false").lower() == "true"
    header_dev_mode = (x_ecare_dev_mode or "").lower() == "true"

    if not dev_mode and not header_dev_mode:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Write operations are disabled. "
                "Set ECARE_DEV_MODE=true or send X-Ecare-Dev-Mode: true "
                "for development access only."
            ),
        )