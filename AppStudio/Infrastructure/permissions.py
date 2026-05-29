"""
Infrastructure: Permissions Guard

Access control matrix — determines which systems can communicate.
Enforced at the Gateway before any message is transported.
"""

from AppStudio.Config import PERMISSION_MATRIX
from AppStudio.Infrastructure.logger import InfraLogger

_logger = InfraLogger()


def is_allowed(source_system: str, target_system: str) -> bool:
    """
    Check if source_system is permitted to send to target_system.

    Rules:
    - Explicit True → allowed
    - Explicit False → blocked
    - Not listed → blocked (deny by default)
    - Same system → always allowed (intra-system)
    """
    if source_system == target_system:
        return True

    key = (source_system, target_system)
    allowed = PERMISSION_MATRIX.get(key, False)

    if not allowed:
        _logger.warning(
            source_system, target_system,
            message=f"PERMISSION DENIED: {source_system} → {target_system}"
        )

    return allowed


def get_allowed_targets(source_system: str) -> list[str]:
    """List all systems that source_system can send to."""
    targets = []
    for (src, tgt), allowed in PERMISSION_MATRIX.items():
        if src == source_system and allowed:
            targets.append(tgt)
    return targets


def get_allowed_sources(target_system: str) -> list[str]:
    """List all systems that can send to target_system."""
    sources = []
    for (src, tgt), allowed in PERMISSION_MATRIX.items():
        if tgt == target_system and allowed:
            sources.append(src)
    return sources
