"""
Permanent Memory: Guard Department

Blocks all auto-delete attempts on permanent memory.
Only user-confirmed deletions are allowed.
"""


def can_delete(user_confirmed: bool) -> bool:
    """
    Only returns True if user has explicitly confirmed deletion.
    All automated processes (decay, prune, cleanup) are blocked.
    """
    return user_confirmed is True


def can_modify(user_confirmed: bool) -> bool:
    """
    Content updates in permanent memory also require user confirmation.
    Access count / last_accessed updates are allowed automatically.
    """
    return user_confirmed is True


def block_auto_delete() -> str:
    """Message returned when an automated process tries to delete."""
    return "Permanent memory entries cannot be auto-deleted. Only user can delete."
