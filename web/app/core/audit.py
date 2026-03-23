"""
DataForge — Structured audit logging.

All security-relevant events are logged in JSON format for traceability.
"""

import json
import logging
import sys
import time
from typing import Optional

# Structured JSON logger for audit events
_audit_logger = logging.getLogger("dataforge.audit")
_audit_logger.setLevel(logging.INFO)

_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(logging.Formatter("%(message)s"))
_audit_logger.addHandler(_handler)
_audit_logger.propagate = False

# Application logger for general events
logger = logging.getLogger("dataforge")
logger.setLevel(logging.INFO)
_app_handler = logging.StreamHandler(sys.stdout)
_app_handler.setFormatter(
    logging.Formatter("[%(asctime)s] %(levelname)s %(name)s: %(message)s")
)
logger.addHandler(_app_handler)
logger.propagate = False


def audit_log(
    action: str,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    ip: Optional[str] = None,
    detail: Optional[dict] = None,
    success: bool = True,
):
    """Log a security-relevant event as structured JSON."""
    entry = {
        "ts": time.time(),
        "action": action,
        "success": success,
    }
    if user_id is not None:
        entry["user_id"] = user_id
    if username:
        entry["username"] = username
    if ip:
        entry["ip"] = ip
    if detail:
        entry["detail"] = detail
    _audit_logger.info(json.dumps(entry, default=str))
