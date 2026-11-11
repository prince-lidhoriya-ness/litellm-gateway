"""Writes the provisioned Grafana dashboards to monitoring/grafana/dashboards/*.json.

Edit the panel lists here and rerun; Grafana reloads provisioned files on its own.
    python monitoring/grafana/build_dashboards.py
"""

import json
from pathlib import Path

OUT = Path(__file__).resolve().parent / "dashboards"
PROM = {"type": "prometheus", "uid": "prometheus"}
LOKI = {"type": "loki", "uid": "loki"}


def panel(title, exprs, kind="timeseries", unit=None, width=12, height=8, legend=None, ds=PROM):
    targets = [
        {"refId": chr(65 + i), "expr": expr, "legendFormat": (legend[i] if legend else "__auto"), "datasource": ds}
        for i, expr in enumerate(exprs)
    ]
    field_config = {"defaults": {"unit": unit} if unit else {}, "overrides": []}
    return {"type": kind, "title": title, "datasource": ds, "targets": targets, "fieldConfig": field_config,
            "gridPos": {"w": width, "h": height}, "options": {}}


def stat(title, expr, unit=None):
    return panel(title, [expr], kind="stat", unit=unit, width=6, height=4)


def dashboard(uid, title, panels, tags):
    x = y = row_height = 0
    for i, p in enumerate(panels, start=1):
        w, h = p["gridPos"]["w"], p["gridPos"]["h"]
        if x + w > 24:
            x, y = 0, y + row_height
            row_height = 0
        p["id"] = i
        p["gridPos"].update({"x": x, "y": y})
        x += w
        row_height = max(row_height, h)
    return {"uid": uid, "title": title, "tags": tags, "timezone": "browser", "schemaVersion": 41,
            "time": {"from": "now-1h", "to": "now"}, "refresh": "30s", "panels": panels, "editable": False}


REQUEST_HEALTH = dashboard("gw-request-health", "Gateway - request health", [
    stat("Requests / s", "sum(rate(litellm_proxy_total_requests_metric_total[5m]))", "reqps"),
    stat("Error rate", "sum(rate(litellm_proxy_failed_requests_metric_total[5m])) / clamp_min(sum(rate(litellm_proxy_total_requests_metric_total[5m])), 1e-9)", "percentunit"),
    stat("p95 latency", "histogram_quantile(0.95, sum by (le) (rate(litellm_request_total_latency_metric_bucket[5m])))", "s"),
    stat("Targets down", "count(up{job!=\"dcgm\"} == 0) or vector(0)"),
    panel("Throughput by model", ["sum by (model) (rate(litellm_proxy_total_requests_metric_total[5m]))"], unit="reqps"),
    panel("Failures by status code", ["sum by (status_code) (rate(litellm_proxy_failed_requests_metric_total[5m]))"], unit="reqps"),
    panel("End-to-end latency p50 / p95 / p99", [
        f"histogram_quantile({q}, sum by (le) (rate(litellm_request_total_latency_metric_bucket[5m])))" for q in (0.5, 0.95, 0.99)
    ], unit="s", legend=["p50", "p95", "p99"]),
    panel("Provider latency p95 and time to first token p95", [
        "histogram_quantile(0.95, sum by (le) (rate(litellm_llm_api_latency_metric_bucket[5m])))",
        "histogram_quantile(0.95, sum by (le) (rate(litellm_llm_api_time_to_first_token_metric_bucket[5m])))",
    ], unit="s", legend=["provider p95", "TTFT p95"]),
    panel("LiteLLM overhead p95 vs prompt pipeline p95", [
        "histogram_quantile(0.95, sum by (le) (rate(litellm_overhead_latency_metric_bucket[5m])))",
        "histogram_quantile(0.95, sum by (le) (rate(prompt_pipeline_duration_seconds_bucket[5m])))",
    ], unit="s", legend=["litellm overhead", "prompt pipeline"]),
    panel("Fallbacks", ["sum(rate(litellm_deployment_successful_fallbacks_total[5m]))", "sum(rate(litellm_deployment_failed_fallbacks_total[5m]))"],
          unit="reqps", legend=["successful", "failed"]),
    panel("Container CPU (cores, by container_id)", ["sum by (container_id) (rate(container_cpu_usage_seconds_total{container_id!=\"\"}[5m]))"], width=8),
    panel("Container memory (by container_id)", ["sum by (container_id) (container_memory_working_set_bytes{container_id!=\"\"})"], unit="bytes", width=8),
    panel("Postgres / Redis up", ["pg_up", "redis_up"], width=8, legend=["postgres", "redis"]),
    panel("Docker VM CPU busy", ["1 - avg(rate(node_cpu_seconds_total{mode=\"idle\"}[5m]))"], unit="percentunit", width=8),
    panel("Docker VM memory used", ["1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes"], unit="percentunit", width=8),
    panel("Container restarts (15m)", ["changes(container_start_time_seconds{container_id!=\"\"}[15m])"], width=8),
], ["litellm", "requests"])

COST_TOKENS = dashboard("gw-cost-tokens", "Gateway - cost and tokens", [
    stat("Spend (24h, USD)", "sum(increase(litellm_spend_metric_total[24h]))", "currencyUSD"),
    stat("Tokens (24h)", "sum(increase(litellm_total_tokens_metric_total[24h]))"),
    stat("Tokens saved by compression (24h)", "sum(increase(prompt_pipeline_tokens_saved_total[24h]))"),
    stat("Local compute cost (24h, ESTIMATE)", "sum(increase(prompt_pipeline_estimated_compute_cost_usd_total[24h]))", "currencyUSD"),
    panel("Spend by model (USD / h)", ["sum by (model) (rate(litellm_spend_metric_total[5m])) * 3600"], unit="currencyUSD"),
    panel("Spend by team (USD / h)", ["sum by (team_alias) (rate(litellm_spend_metric_total[5m])) * 3600"], unit="currencyUSD"),
    panel("Input / output tokens per second", [
        "sum by (model) (rate(litellm_input_tokens_metric_total[5m]))",
        "sum by (model) (rate(litellm_output_tokens_metric_total[5m]))",
    ], legend=["input {{model}}", "output {{model}}"]),
    panel("Prompt tokens before vs after compression", [
        "sum(rate(prompt_pipeline_tokens_before_total[5m]))", "sum(rate(prompt_pipeline_tokens_after_total[5m]))",
    ], legend=["before", "after"]),
    panel("Team budget remaining", ["litellm_remaining_team_budget_metric"], unit="currencyUSD", legend=["{{team_alias}}"]),
    panel("API key budget remaining", ["litellm_remaining_api_key_budget_metric"], unit="currencyUSD", legend=["{{hashed_api_key}}"]),
    panel("Budget burn (team, fraction used)", ["1 - litellm_remaining_team_budget_metric / (litellm_team_max_budget_metric > 0)"],
          unit="percentunit", legend=["{{team_alias}}"]),
    panel("Local compute seconds by component", ["sum by (component) (rate(prompt_pipeline_compute_seconds_total[5m]))"]),
], ["litellm", "cost"])

PIPELINE = dashboard("gw-prompt-pipeline", "Gateway - prompt pipeline", [
    stat("Compression ratio (avg, 1h)", "sum(increase(prompt_pipeline_compression_ratio_sum[1h])) / clamp_min(sum(increase(prompt_pipeline_compression_ratio_count[1h])), 1)"),
    stat("Tokens saved (1h)", "sum(increase(prompt_pipeline_tokens_saved_total[1h]))"),
    stat("Fail-open events (1h)", "sum(increase(prompt_pipeline_failures_total{mode=\"open\"}[1h])) or vector(0)"),
    stat("Models loaded", "min(prompt_pipeline_model_loaded)"),
    panel("Label mix (messages / s)", ["sum by (label) (rate(prompt_pipeline_messages_total[5m]))"], kind="timeseries"),
    panel("Decision source (rules / model / fallback)", ["sum by (source) (rate(prompt_pipeline_messages_total[5m]))"]),
    panel("Routing outcome", ["sum by (route) (rate(prompt_pipeline_messages_total[5m]))"]),
    panel("Request category share (1h)", ["sum by (label) (increase(prompt_pipeline_requests_total[1h]))"], kind="piechart"),
    panel("Classifier latency p50 / p95", [
        f"histogram_quantile({q}, sum by (le) (rate(prompt_pipeline_classifier_latency_seconds_bucket[5m])))" for q in (0.5, 0.95)
    ], unit="s", legend=["p50", "p95"]),
    panel("Compressor latency p50 / p95", [
        f"histogram_quantile({q}, sum by (le) (rate(prompt_pipeline_compress_latency_seconds_bucket[5m])))" for q in (0.5, 0.95)
    ], unit="s", legend=["p50", "p95"]),
    panel("Classifier confidence distribution (1h)", ["sum by (le) (increase(prompt_pipeline_classifier_top_score_bucket[1h]))"],
          kind="bargauge"),
    panel("Compression ratio by label (p50)", ["histogram_quantile(0.5, sum by (le, label) (rate(prompt_pipeline_compression_ratio_bucket[15m])))"],
          legend=["{{label}}"]),
    panel("Tokens saved by label", ["sum by (label) (rate(prompt_pipeline_tokens_saved_total[5m]))"], legend=["{{label}}"]),
    panel("Failures by mode and reason", ["sum by (mode, reason) (increase(prompt_pipeline_failures_total[5m]))"]),
    panel("Rule hits by type", ["sum by (rule) (increase(prompt_pipeline_rule_hits_total[1h]))"], kind="barchart"),
    panel("Classifier cache hit ratio", ["sum(rate(prompt_pipeline_classifier_cache_total{result=\"hit\"}[15m])) / clamp_min(sum(rate(prompt_pipeline_classifier_cache_total[15m])), 1e-9)"],
          unit="percentunit"),
    panel("Pipeline log events", ['{service_name="litellm-gateway"} | json | event=~"prompt_pipeline.*|llm.request.*"'],
          kind="logs", width=24, height=10, ds=LOKI),
], ["litellm", "prompt-pipeline"])


def _q(q, metric, by="le"):
    return f"histogram_quantile({q}, sum by ({by}) (rate({metric}_bucket[5m])))"


# context_engineering/ (metrics.py) plus the attribution family recorded after each answered request. Every saving is
# counted once: the stages run one after the other, so the gateway_optimization_tokens series add up without overlap.
CONTEXT = dashboard("gw-context-engineering", "Gateway - context engineering and attribution", [
    stat("Prompt tokens saved, all techniques (1h)", "sum(increase(gateway_optimization_tokens_total{technique!=\"provider_cache\"}[1h]))"),
    stat("Provider cache hit rate (1h)", "sum(increase(context_engine_provider_cached_tokens_total[1h])) / clamp_min(sum(increase(context_engine_provider_prompt_tokens_total[1h])), 1)", "percentunit"),
    stat("Estimated savings (24h, USD, ESTIMATE)", "sum(increase(gateway_optimization_saved_usd_total[24h]))", "currencyUSD"),
    stat("Stages undone / fail-open (1h)", "sum(increase(context_engine_stage_undone_total[1h])) + sum(increase(context_engine_failures_total[1h])) or vector(0)"),
    panel("Tokens saved by technique (tokens / s)", ["sum by (technique) (rate(gateway_optimization_tokens_total[5m]))"],
          legend=["{{technique}}"]),
    panel("Estimated savings by technique (USD / h, ESTIMATE)", ["sum by (technique) (rate(gateway_optimization_saved_usd_total[5m])) * 3600"],
          unit="currencyUSD", legend=["{{technique}}"]),
    panel("Context size before / after p50 (tokens)", [_q(0.5, "context_engine_context_tokens", "le, stage")], legend=["{{stage}}"]),
    panel("Context utilization p50 / p95 (share of the effective target)", [
        _q(0.5, "context_engine_utilization", "le, stage"), _q(0.95, "context_engine_utilization", "le, stage")],
        unit="percentunit", legend=["p50 {{stage}}", "p95 {{stage}}"]),
    panel("Context preparation latency p50 / p90 / p95", [_q(q, "context_engine_duration_seconds") for q in (0.5, 0.9, 0.95)],
          unit="s", legend=["p50", "p90", "p95"]),
    panel("End-to-end request latency p50 / p90 / p95", [_q(q, "litellm_request_total_latency_metric") for q in (0.5, 0.9, 0.95)],
          unit="s", legend=["p50", "p90", "p95"]),
    panel("Observations masked / folded / restored (per 5m)", [
        "sum by (reason) (increase(context_engine_masked_total[5m]))", "sum by (kind) (increase(context_engine_restored_total[5m]))"],
        legend=["masked: {{reason}}", "restored: {{kind}}"]),
    panel("History decisions and compactions (per 5m)", [
        "sum by (action) (increase(context_engine_history_turns_total[5m]))", "sum by (source) (increase(context_engine_compactions_total[5m]))"],
        legend=["turns: {{action}}", "compactions: {{source}}"]),
    panel("Retrieved-turn relevance p50", [_q(0.5, "context_engine_retrieval_score", "le, backend")], legend=["{{backend}}"]),
    panel("Pressure mix (requests / s)", ["sum by (pressure) (rate(context_engine_requests_total[5m]))"], legend=["{{pressure}}"]),
    panel("Provider cache reads / writes (tokens / s)", [
        "sum by (provider) (rate(context_engine_provider_cached_tokens_total[5m]))",
        "sum by (provider) (rate(context_engine_provider_cache_write_tokens_total[5m]))"], legend=["read {{provider}}", "write {{provider}}"]),
    panel("Compression: validation rejects and early stops (per 5m)", [
        "sum(increase(prompt_pipeline_validation_rejects_total[5m]))", "sum by (reason) (increase(prompt_pipeline_compress_stopped_total[5m]))",
        "sum by (reason) (increase(prompt_pipeline_failures_total[5m]))"], legend=["ratio-cap rejects", "stopped: {{reason}}", "fallback: {{reason}}"]),
    panel("Volatile system-prompt content (requests / 5m)", ["sum by (pattern) (increase(context_engine_volatile_prefix_total[5m]))"],
          legend=["{{pattern}}"]),
    panel("Context engineering log events", ['{service_name="litellm-gateway"} |= "context engineering"'],
          kind="logs", width=12, height=8, ds=LOKI),
], ["litellm", "context-engineering"])


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for board in (REQUEST_HEALTH, COST_TOKENS, PIPELINE, CONTEXT):
        (OUT / f"{board['uid']}.json").write_text(json.dumps(board, indent=2), encoding="utf-8")
        print(f"wrote {board['uid']}.json ({len(board['panels'])} panels)")


if __name__ == "__main__":
    main()
