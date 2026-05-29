# Re-export from the canonical location so both import paths work:
#   from MAIINNN.Functions.result_reporter import ActionResult   (legacy path)
#   from MAIINNN.Functions.action.result_reporter import ...     (canonical path)
from MAIINNN.Functions.action.result_reporter import (
    ActionResult,
    UndoInfo,
    ActionStep,
    ActionPlan,
)

__all__ = ["ActionResult", "UndoInfo", "ActionStep", "ActionPlan"]
