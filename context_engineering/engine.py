"""The context-engineering stage, run once per request before the prompt-compression stage.

    1. resolve model     window, provider, prompt-caching support (models.py)
    2. analyze           categories, tokens, pinned messages, prefix fingerprint (analyzer.py)
    3. budget            utilization, oversized components, allowed techniques (budget.py)
    4. cache plan        caching support, history freeze, JIT permission, breakpoints (cache.py)
    5. relocate          optional: volatile system-prompt lines to the end of the query (cache.py)
    6. mask              duplicate folding and batched masking of old tool outputs (masking.py)
    7. history           re-analyze; if still under pressure: JIT retrieval and/or compaction (history.py)
    8. hints             metadata for the compression stage: the indexes it must keep verbatim (the summary)

Each of steps 5-7 runs in its own try/except and its output is checked by validate.check; a failing or invalid stage
is undone (the next stage starts from the last valid messages) and recorded in report.stages_failed. The input list is
never mutated.
"""

import copy
import logging
import time
from dataclasses import dataclass, field
from typing import Optional

from context_engineering import analyzer, budget, cache, history, masking, models, validate
from context_engineering import tokens as tk
from context_engineering.compaction import ModelSummarizer
from context_engineering.settings import ContextSettings
from context_engineering.store import build_store
from context_engineering.structures import ContextReport

logger = logging.getLogger("context_engineering.engine")


@dataclass
class EngineResult:
    messages: list
    report: ContextReport
    tools: Optional[list] = None
    breakpoints: Optional[list] = None
    pending_summaries: list = field(default_factory=list)


class ContextEngine:
    def __init__(self, settings: Optional[ContextSettings] = None, store=None, summarizer=None, calibration=None):
        self.settings = settings or ContextSettings.from_env()
        self.store = store if store is not None else build_store(self.settings)
        self.calibration = calibration or tk.CALIBRATION
        if summarizer is None and self.settings.compaction_mode == "llm" and self.settings.compaction_model:
            summarizer = ModelSummarizer(self.settings.compaction_model, self.store,
                                         self.settings.compaction_max_summary_tokens)
        self.summarizer = summarizer

    def process(self, messages: list, model: str = "", tools=None, max_tokens=None, request: Optional[dict] = None
                ) -> EngineResult:
        started = time.perf_counter()
        settings = self.settings
        report = ContextReport(mode=settings.mode)
        request = request or {}
        stage_started = time.perf_counter()

        def lap(name: str) -> None:
            nonlocal stage_started
            now = time.perf_counter()
            report.stage_ms[name] = round((now - stage_started) * 1000, 2)
            stage_started = now

        info = models.resolve(model, settings)
        report.model, report.window, report.window_source = info.resolved or info.name, info.window, info.window_source
        original = messages
        profile = analyzer.analyze(original, tools, settings.hash_salt, settings.observation_error_guard)
        report.tokens_before = profile.total_tokens
        report.by_category_before = dict(profile.totals)
        report.conversation_key, report.prefix_sha = profile.conversation_key, profile.prefix_sha
        report.volatile_prefix = list(profile.volatile)
        factor = self.calibration.factor(info.resolved or info.name)
        plan = budget.plan(profile, info, settings, max_tokens, factor)
        report.utilization_before, report.pressure = plan.utilization, plan.pressure
        report.oversized, report.techniques = list(plan.oversized), sorted(plan.techniques)
        report.decisions.extend(plan.decisions)
        cache_plan = cache.plan(profile, info, settings, request)
        report.caching = cache_plan.caching
        report.decisions.extend(cache_plan.decisions)
        lap("analyze")

        current = original
        result_tools = tools
        pending: list = []

        def stage(name: str, run, allow=frozenset()):
            nonlocal current
            try:
                candidate = run(current)
            except Exception as exc:
                report.stages_failed.append(f"{name}:{type(exc).__name__}")
                logger.warning("context engineering stage failed, skipped: stage=%s error=%s", name, type(exc).__name__)
                return False
            problems = validate.check(current, candidate, allow)
            if problems:
                report.stages_failed.append(f"{name}:invariant")
                report.invariant_violations.extend(f"{name}:{p}" for p in problems)
                logger.warning("context engineering stage undone: stage=%s invariants=%s", name, problems)
                return False
            current = candidate
            return True

        # 5. relocate volatile system-prompt lines (opt-in: it changes the system prompt and the query)
        if cache_plan.enabled and settings.relocate_volatile and profile.volatile:
            def relocate(msgs):
                moved_messages, moved = cache.relocate_volatile(msgs, analyzer.analyze(msgs, tools))
                if moved:
                    report.decisions.append(f"relocated {sum(n for _, n in moved)} volatile system line(s)")
                return moved_messages
            stage("relocate", relocate, frozenset({"system_edit", "query_suffix"}))
        if cache_plan.enabled and settings.canonical_tools:
            result_tools = cache.canonical_tools(tools)
        lap("cache")

        # 6. masking
        if plan.techniques & {"dedupe", "mask"}:
            def run_mask(msgs):
                masked, records, notes = masking.mask(msgs, analyzer.analyze(msgs, tools, error_ranks=settings.observation_error_guard), settings, plan.techniques,
                                                      self.store)
                report.masked.extend(records)
                report.decisions.extend(notes)
                return masked
            if not stage("mask", run_mask):
                report.masked.clear()
        lap("mask")

        # 7. history: re-measure after masking; mask first, compact only if still needed (cheapest loss first)
        if "history" in plan.techniques:
            after_mask = analyzer.analyze(current, tools, settings.hash_salt, settings.observation_error_guard)
            replan = budget.plan(after_mask, info, settings, max_tokens, factor)
            if "history" in replan.techniques:
                def run_history(msgs):
                    outcome = history.apply(msgs, after_mask, cache_plan, settings, self.store, self.summarizer)
                    report.decisions.extend(outcome.decisions)
                    report.history.extend(outcome.records)
                    report.summary_index, report.summary_source = outcome.summary_index, outcome.summary_source
                    pending.extend(outcome.pending)
                    return outcome.messages
                if not stage("history", run_history):
                    report.history.clear()
                    report.summary_index, report.summary_source = None, ""
                    pending.clear()
            else:
                report.decisions.append(f"history: not needed after masking (utilization {replan.utilization:.2f})")
        lap("history")

        # 8. final accounting and hints for the compression stage
        final = analyzer.analyze(current, result_tools, settings.hash_salt) if current is not original else profile
        report.tokens_after = final.total_tokens
        report.by_category_after = dict(final.totals)
        report.utilization_after = budget.plan(final, info, settings, max_tokens, factor).utilization
        # The compression stage reads protected_indexes and leaves those messages verbatim (pipeline.py, `protected`).
        hints: dict = {}
        if report.summary_index is not None:
            hints["protected_indexes"] = [report.summary_index]
        report.hints = hints
        report.breakpoints_added = bool(cache_plan.breakpoints)
        report.elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
        return EngineResult(
            messages=copy.deepcopy(current) if current is not original else current,
            report=report, tools=result_tools, breakpoints=cache_plan.breakpoints, pending_summaries=pending,
        )
