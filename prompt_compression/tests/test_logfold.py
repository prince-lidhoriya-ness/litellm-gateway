"""Log template folding (route "logfold", reports/production-readiness-audit/STRATEGY.md, C1.1)."""

from prompt_compression import logfold
from prompt_compression.texts import count_tokens

from .audit_cases import CASE_C_NEEDLES, CASE_D_NEEDLES, case_c, case_c_log, case_d
from .test_pipeline import make_pipeline


def default_pipeline(**overrides):
    return make_pipeline(routes=frozenset({"narrative", "logfold"}), protect_edges=True, **overrides)


def test_the_template_masks_values_but_keeps_field_names_and_words():
    line = '2026-11-17T10:01:11Z INFO checkout-service req=req-07732 user=u-12 path=/v1/cart msg="slow call" took 91ms'
    assert logfold.template(line) == ("<*> INFO checkout-service req=<*> user=<*> path=<*> msg=\"<*>\" took <*>")


def test_a_run_keeps_its_first_and_last_line_and_the_marker_says_what_was_folded():
    lines = [f"2026-11-17T10:00:{i:02d}Z INFO api GET /orders/{i} 200 {10 + i}ms" for i in range(20)]
    folds = logfold.plan_folds(lines, count_tokens)
    assert len(folds) == 1 and (folds[0].first, folds[0].last) == (1, 18)
    out = logfold.apply(lines, folds)
    assert out[0] == lines[0] and out[-1] == lines[-1] and len(out) == 3
    assert out[1] == ('[gateway: 18 similar lines folded (lines 2-19), template "<*> INFO api GET <*> <*> <*>", '
                      'first 2026-11-17T10:00:01Z, last 2026-11-17T10:00:18Z]')


def test_severity_lines_are_never_folded_and_split_runs():
    lines = [f"10:00:{i:02d} INFO worker processed batch {i}" for i in range(30)]
    lines[12] = "10:00:12 ERROR worker batch 12 failed: Traceback follows"
    lines[13] = "10:00:13 WARN worker retrying batch 12"
    folds = logfold.plan_folds(lines, count_tokens)
    out = logfold.apply(lines, folds)
    assert lines[12] in out and lines[13] in out
    assert all(not (fold.first <= 12 <= fold.last or fold.first <= 13 <= fold.last) for fold in folds)


def test_short_runs_are_not_folded():
    lines = [f"10:00:0{i} INFO api ok {i}" for i in range(3)] + ["10:00:09 INFO other thing"]
    assert logfold.plan_folds(lines, count_tokens) == []


def test_folding_is_deterministic_and_does_not_depend_on_the_question():
    log = case_c_log()
    outputs = set()
    for question in ("Why did order ord-7731 fail?", "Summarise the log.", "What happened at 10:01?"):
        pipeline, _, _ = default_pipeline()
        new, report = pipeline.process([{"role": "user", "content": f"Logs:\n\n{log}\n\n{question}"}])
        outputs.add(new[0]["content"].rsplit("\n\n", 1)[0])
        assert report.messages[0]["action"] == "folded_logs"
    assert len(outputs) == 1                       # byte-identical log part: cache-stable


def test_case_c_keeps_the_root_cause_and_saves_tokens():
    pipeline, _, _ = default_pipeline()
    new, report = pipeline.process(case_c())
    content = new[0]["content"]
    assert all(needle in content for needle in CASE_C_NEEDLES)       # the audit measured 1 of 5
    assert report.tokens_after < 0.3 * report.tokens_before
    assert report.segments["log_lines_folded"] > 100 and report.segments["omission_markers"] == 3
    assert content.count("[gateway: ") == report.segments["omission_markers"]


def test_case_d_saves_tokens_without_an_identifier_in_the_question():
    pipeline, _, _ = default_pipeline()
    new, report = pipeline.process(case_d())
    assert all(needle in new[0]["content"] for needle in CASE_D_NEEDLES)
    assert report.tokens_after < 0.2 * report.tokens_before          # the audit measured 0% saved


def test_a_question_that_names_a_value_inside_a_folded_run_keeps_that_run():
    log = case_c_log()
    pipeline, _, _ = default_pipeline()
    new, report = pipeline.process([{"role": "user", "content": f"Logs:\n\n{log}\n\nWhat did req-00045 do?"}])
    assert "req=req-00045 " in new[0]["content"]
    assert report.fidelity["logfold"]["reverted"] == 1 and report.fidelity["logfold"]["reasons"] == {"referenced": 1}
    assert report.segments["omission_markers"] == 2          # the other two runs are still folded


def test_logfold_applies_to_earlier_turns_too_because_it_ignores_the_question():
    log = case_c_log()
    messages = [{"role": "user", "content": f"Here is the log.\n\n{log}\n\nKeep it in mind."},
                {"role": "assistant", "content": "Noted."},
                {"role": "user", "content": "Which service logged the most lines?"}]
    pipeline, _, _ = default_pipeline()
    new, report = pipeline.process(messages)
    assert report.messages[0]["action"] == "folded_logs" and new[2] == messages[2]


def test_with_records_on_a_repetitive_log_is_folded_not_selected():
    # Folding is the first step; selection is the second (STRATEGY.md, C1.2). Selection here would keep less context.
    question = "What is the status of order ord-7731?"
    pipeline, _, _ = make_pipeline(routes=frozenset({"logfold", "records"}), protect_edges=True)
    new, report = pipeline.process([{"role": "user", "content": f"Logs:\n\n{case_c_log()}\n\n{question}"}])
    assert report.intent == "lookup" and report.messages[0]["action"] == "folded_logs"
    assert report.segments["record_lines_dropped"] == 0 and report.segments["log_lines_folded"] > 100


def test_with_records_on_a_log_with_nothing_to_fold_falls_back_to_selection():
    lines = [f"2026-11-17T10:{i // 60:02d}:{i % 60:02d}Z {verb} svc-{i} k{i}=v{i} order=ord-{1000 + i}"
             for i, verb in zip(range(60), ["INFO", "DEBUG", "TRACE", "NOTICE"] * 15)]
    lines = [line + " " + "x" * (i % 7) for i, line in enumerate(lines)]      # every line its own template
    question = "What is the status of order ord-1030?"
    pipeline, _, _ = make_pipeline(routes=frozenset({"logfold", "records"}), protect_edges=True)
    new, report = pipeline.process([{"role": "user", "content": "Logs:\n\n" + "\n".join(lines) + "\n\n" + question}])
    assert report.messages[0]["action"] == "selected_records" and "ord-1030" in new[0]["content"]
    assert report.segments["record_lines_dropped"] > 0 and report.segments["log_lines_folded"] == 0
