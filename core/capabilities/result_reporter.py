# Re-export from the canonical location so both import paths work:
#   from core.capabilities.result_reporter import ActionResult   (legacy path)
#   from core.capabilities.action.result_reporter import ...     (canonical path)
from core.capabilities.action.result_reporter import (
    ActionResult,
    UndoInfo,
    ActionStep,
    ActionPlan,
)

__all__ = ["ActionResult", "UndoInfo", "ActionStep", "ActionPlan"]
