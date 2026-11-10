"""Context Budget Manager: how full is the context, which component is too big, which techniques may run.

    window          max input tokens of the model (LiteLLM model map, an override, or the default)
    output reserve  the request's max_tokens (or CONTEXT_RESERVED_OUTPUT_TOKENS), at most half the window
    target          min(window - reserve, window * CONTEXT_MAX_UTILIZATION) * (1 - CONTEXT_SAFETY_BUFFER)
    utilization     estimated prompt tokens (times the model's calibration factor) / target

The budget never cuts anything itself. It records why it allowed each technique, and the techniques decide what is
safe to remove. System messages, tool definitions and the current query are reported but never reduced.
"""

from context_engineering.settings import ContextSettings
from context_engineering.structures import CATEGORIES, HISTORY, TOOL_OUTPUT, BudgetPlan, ContextProfile, ModelInfo

PRESSURE_LEVELS = ("low", "moderate", "high", "over")


def pressure_of(utilization: float, settings: ContextSettings) -> str:
    if utilization >= 1.0:
        return "over"
    if utilization >= settings.compaction_threshold:
        return "high"
    if utilization >= 0.5 * settings.compaction_threshold:
        return "moderate"
    return "low"


def target_tokens(model: ModelInfo, settings: ContextSettings, max_tokens=None) -> tuple[int, int]:
    window = max(1, model.window)
    try:
        requested = int(max_tokens) if max_tokens else 0
    except (TypeError, ValueError):
        requested = 0
    reserve = min(requested or settings.reserved_output_tokens, window // 2)
    usable = min(window - reserve, int(window * settings.max_utilization))
    return max(1, int(usable * (1.0 - settings.safety_buffer))), reserve


def plan(profile: ContextProfile, model: ModelInfo, settings: ContextSettings, max_tokens=None,
         calibration: float = 1.0) -> BudgetPlan:
    target, reserve = target_tokens(model, settings, max_tokens)
    estimated = int(profile.total_tokens * calibration)
    utilization = round(estimated / target, 4)
    limits = {category: int(settings.shares.get(category, 1.0) * target) for category in CATEGORIES}
    oversized = tuple(
        category for category in CATEGORIES
        if category in settings.shares and profile.totals.get(category, 0) * calibration > limits[category]
    )
    pressure = pressure_of(utilization, settings)
    techniques, decisions = set(), []
    if not settings.budget_enabled:
        # Without a budget only the triggers that do not need one apply.
        if settings.masking_enabled and settings.dedup_enabled:
            techniques.add("dedupe")
        if settings.masking_enabled and settings.mask_trigger == "always":
            techniques.add("mask")
        decisions.append("budget disabled: history techniques have no trigger")
        return BudgetPlan(False, model.window, target, reserve, utilization, pressure, limits, oversized,
                          frozenset(techniques), tuple(decisions))

    decisions.append(
        f"utilization {utilization:.2f} of target {target} (window {model.window} from {model.window_source}, "
        f"reserve {reserve}, calibration {calibration:.2f})"
    )
    for category in oversized:
        decisions.append(f"oversized: {category} {int(profile.totals.get(category, 0) * calibration)} > {limits[category]}")
    if settings.masking_enabled and settings.dedup_enabled:
        techniques.add("dedupe")
    if settings.masking_enabled:
        if settings.mask_trigger == "always":
            techniques.add("mask")
        elif TOOL_OUTPUT in oversized or pressure in ("high", "over"):
            techniques.add("mask")
            decisions.append("mask: triggered by tool-output share or pressure")
    if settings.compaction_enabled or settings.jit_enabled:
        if pressure in ("high", "over") or HISTORY in oversized:
            techniques.add("history")
            decisions.append(f"history: pressure {pressure}" + (" and history oversized" if HISTORY in oversized else ""))
    return BudgetPlan(True, model.window, target, reserve, utilization, pressure, limits, oversized,
                      frozenset(techniques), tuple(decisions))
