"""End-to-end evidence for the monitoring stack (docs/monitoring-plan.md, rollout steps 1-4).

Sends one chat request per prompt category through the proxy, then checks that each
request is visible in Jaeger (with the pipeline spans), Loki (log lines with the same
trace_id), Prometheus (series for every metric), Langfuse (trace, usage, cost) and
Grafana (provisioned dashboards return data). Secrets are read from .env and never printed.

    .venv-compression/Scripts/python monitoring/scripts/verify_observability.py [--model obs-priced-llama]
"""

import argparse
import base64
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

GATEWAY_DIR = Path(__file__).resolve().parents[2]

PROMPTS = {
    "sensitive": "Please update my customer profile. My email is jane.doe@example.com and my phone is "
                 "+1 555 013 2287. I was recently diagnosed with type 2 diabetes and the clinic needs the new "
                 "details before my appointment next Tuesday. Reply with one word: ok.",
    "critical": "Write a Python function parse_order(line) that splits on ';', returns a dict with keys id, sku, "
                "qty, and raises ValueError if qty is not a positive integer. Order IDs look like ORD-2024-88731. "
                "Use only the standard library and keep the signature exactly as given.",
    "non_sensitive": "The city park was renovated last year. It now has a larger playground, a walking trail along "
                     "the river, new benches near the pond and a small cafe that sells coffee and pastries. On "
                     "weekends many families visit and local musicians play near the entrance. Summarise in one line.",
    "less_important": "Hi there! Hope you're having a great day and a lovely week so far. Thanks so much again for "
                      "all the help last time, really appreciate it, you're the best! Anyway, as I said before, just "
                      "saying hello again, nothing urgent at all, have a nice evening and talk soon, cheers and kind regards!",
}
PIPELINE_METRICS = [
    "prompt_pipeline_requests_total", "prompt_pipeline_messages_total", "prompt_pipeline_duration_seconds_count",
    "prompt_pipeline_classifier_latency_seconds_count", "prompt_pipeline_compress_latency_seconds_count",
    "prompt_pipeline_classifier_top_score_count", "prompt_pipeline_tokens_before_total",
    "prompt_pipeline_tokens_after_total", "prompt_pipeline_tokens_saved_total", "prompt_pipeline_compression_ratio_count",
    "prompt_pipeline_rule_hits_total", "prompt_pipeline_classifier_cache_total", "prompt_pipeline_model_load_seconds",
    "prompt_pipeline_model_loaded", "prompt_pipeline_compute_seconds_total",
    "prompt_pipeline_estimated_compute_cost_usd_total",
]
LITELLM_METRICS = [
    "litellm_proxy_total_requests_metric_total", "litellm_request_total_latency_metric_count",
    "litellm_llm_api_latency_metric_count", "litellm_overhead_latency_metric_count", "litellm_spend_metric_total",
    "litellm_input_tokens_metric_total", "litellm_output_tokens_metric_total", "litellm_total_tokens_metric_total",
]
INFRA_METRICS = ["node_cpu_seconds_total", "container_memory_working_set_bytes{container_id!=\"\"}", "pg_up", "redis_up",
                 "process_start_time_seconds"]


def load_env() -> dict:
    values = {}
    for line in (GATEWAY_DIR / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"')
    return values


def http(url, data=None, headers=None, method=None, timeout=120):
    body = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json", **(headers or {})},
                                 method=method)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.status, dict(resp.headers), json.loads(resp.read() or b"null")


def prom(query):
    _, _, result = http("http://localhost:9090/api/v1/query?" + urllib.parse.urlencode({"query": query}))
    return result["data"]["result"]


def section(title):
    print(f"\n===== {title}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="obs-priced-llama")
    parser.add_argument("--wait", type=int, default=25, help="seconds to let exporters flush")
    args = parser.parse_args()
    env = load_env()
    master = {"Authorization": f"Bearer {env['LITELLM_MASTER_KEY']}"}
    failures = []

    section("requests (one per category) -> http://localhost:4000")
    sent = {}
    for category, text in PROMPTS.items():
        started = time.perf_counter()
        status, headers, body = http("http://localhost:4000/v1/chat/completions", {
            "model": args.model, "messages": [{"role": "user", "content": text}], "max_tokens": 40,
            "user": f"verify-user-{category}", "metadata": {"session_id": "observability-verification"},
        }, master)
        call_id = headers.get("x-litellm-call-id")
        usage = body.get("usage") or {}
        sent[category] = {"call_id": call_id, "usage": usage, "latency_s": round(time.perf_counter() - started, 2),
                          "cost": headers.get("x-litellm-response-cost")}
        print(f"[{category:14s}] HTTP {status} call_id={call_id} usage={usage} "
              f"cost_header={headers.get('x-litellm-response-cost')} latency={sent[category]['latency_s']}s")
    stream_req = urllib.request.Request("http://localhost:4000/v1/chat/completions", data=json.dumps({
        "model": args.model, "messages": [{"role": "user", "content": PROMPTS["less_important"]}], "max_tokens": 20,
        "stream": True, "stream_options": {"include_usage": True}}).encode(),
        headers={"Content-Type": "application/json", **master})
    with urllib.request.urlopen(stream_req, timeout=120) as resp:
        chunks = [line for line in resp.read().decode().splitlines() if line.startswith("data:")]
        sent["stream"] = {"call_id": resp.headers.get("x-litellm-call-id")}
    print(f"[stream        ] {len(chunks)} SSE chunks call_id={sent['stream']['call_id']}")

    print(f"waiting {args.wait}s for batch exporters / scrapes ...")
    time.sleep(args.wait)

    section("Jaeger: traces with pipeline spans")
    # Jaeger 2.22 serves only the OTLP-JSON api/v3 (the legacy /api/services path returns 404).
    _, _, services = http("http://localhost:16686/api/v3/services")
    print("services:", services.get("services"))
    now = time.time()
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    _, _, traces = http("http://localhost:16686/api/v3/traces?" + urllib.parse.urlencode({
        "query.service_name": "litellm-gateway", "query.search_depth": 50,
        "query.start_time_min": time.strftime(fmt, time.gmtime(now - 1800)),
        "query.start_time_max": time.strftime(fmt, time.gmtime(now + 60))}))
    spans_by_trace, call_to_trace = {}, {}
    for resource_spans in traces["result"]["resourceSpans"]:
        for scope in resource_spans.get("scopeSpans", []):
            for span in scope.get("spans", []):
                spans_by_trace.setdefault(span["traceId"], set()).add(span["name"])
                for attr in span.get("attributes", []):
                    if attr["key"] == "litellm.request_id":
                        call_to_trace[attr["value"].get("stringValue")] = span["traceId"]
    trace_by_call = {call: (tid, sorted(spans_by_trace[tid])) for call, tid in call_to_trace.items()}
    for category, info in sent.items():
        found = trace_by_call.get(info["call_id"])
        if not found:
            failures.append(f"jaeger: no trace for {category}")
            print(f"[{category:14s}] NO TRACE")
            continue
        info["trace_id"] = found[0]
        pipeline = [n for n in found[1] if n.startswith("prompt.")]
        others = [n for n in found[1] if not n.startswith("prompt.")]
        print(f"[{category:14s}] trace {found[0]} pipeline={pipeline} other={others}")

    section("Loki: log lines by trace_id")
    for category, info in sent.items():
        if not info.get("trace_id"):
            continue
        query = '{service_name="litellm-gateway"} | trace_id="%s"' % info["trace_id"]
        _, _, result = http("http://localhost:3100/loki/api/v1/query_range?" + urllib.parse.urlencode(
            {"query": query, "limit": 50, "start": int((time.time() - 1800) * 1e9)}))
        lines = [json.loads(v[1]) for stream in result["data"]["result"] for v in stream["values"]]
        events = sorted({line.get("event") for line in lines})
        same_trace = all(line.get("trace_id") == info["trace_id"] for line in lines)
        print(f"[{category:14s}] {len(lines)} lines, events={events}, all trace_id match={same_trace}")
        if not lines:
            failures.append(f"loki: no lines for {category}")

    section("Prometheus: one series check per metric")
    for name in PIPELINE_METRICS + LITELLM_METRICS + INFRA_METRICS:
        result = prom(name)
        print(f"{'OK ' if result else 'MISSING'} {name}: {len(result)} series")
        if not result:
            failures.append(f"prometheus: {name}")
    for query in ['sum by (label) (prompt_pipeline_requests_total)', 'sum(prompt_pipeline_tokens_saved_total)',
                  'up']:
        print(query, "->", [(r["metric"].get("label") or r["metric"].get("job"), r["value"][1]) for r in prom(query)])

    section("Langfuse: traces, usage and cost vs the proxy's numbers")
    host = env.get("LANGFUSE_HOST") or "https://us.cloud.langfuse.com"
    auth = base64.b64encode(f"{env['LANGFUSE_PUBLIC_KEY']}:{env['LANGFUSE_SECRET_KEY']}".encode()).decode()
    lf_headers = {"Authorization": f"Basic {auth}"}
    # Langfuse Cloud v3 deprecated GET /api/public/traces/{id} (answers 401); the v2 observations API replaces it.
    since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(time.time() - 3600))
    for category, info in sent.items():
        if not info.get("trace_id") or category == "stream":
            continue
        query = urllib.parse.urlencode({"fromStartTime": since, "limit": 50, "traceId": info["trace_id"],
                                        "fields": "core,basic,usage,model,io,metadata"})
        try:
            _, _, result = http(f"{host}/api/public/v2/observations?{query}", headers=lf_headers)
        except Exception as exc:
            failures.append(f"langfuse: {category} {type(exc).__name__}")
            print(f"[{category:14s}] lookup failed ({type(exc).__name__})")
            continue
        observations = result.get("data") or []
        gen = next((o for o in observations if o.get("type") == "GENERATION"), None)
        if gen is None:
            failures.append(f"langfuse: no generation for {category}")
            print(f"[{category:14s}] no generation yet")
            continue
        usage = gen.get("usageDetails") or {}
        proxy_usage = info["usage"]
        matches = (usage.get("input") == proxy_usage.get("prompt_tokens")
                   and usage.get("output") == proxy_usage.get("completion_tokens")
                   and abs(float(gen.get("totalCost") or 0) - float(info["cost"] or 0)) < 1e-9)
        text_in_trace = PROMPTS[category][:40] in json.dumps(observations)
        tags = (gen.get("metadata") or {}).get("attributes.langfuse.trace.tags")
        print(f"[{category:14s}] {gen['name']}: usage={usage} cost={gen.get('totalCost')} | proxy usage={proxy_usage} "
              f"cost={info['cost']} | match={matches} | input/output stored={gen.get('input') is not None or gen.get('output') is not None} "
              f"| raw text present={text_in_trace} | user={gen.get('userId')} session={gen.get('sessionId')} tags={tags}")
        if not matches:
            failures.append(f"langfuse: usage/cost mismatch for {category}")
        if text_in_trace:
            failures.append(f"langfuse: raw prompt text in {category} trace")

    section("Grafana: provisioned dashboards return data")
    g_auth = base64.b64encode(f"admin:{env['GRAFANA_ADMIN_PASSWORD']}".encode()).decode()
    g_headers = {"Authorization": f"Basic {g_auth}"}
    _, _, boards = http("http://localhost:3000/api/search?type=dash-db", headers=g_headers)
    for board in boards:
        _, _, full = http(f"http://localhost:3000/api/dashboards/uid/{board['uid']}", headers=g_headers)
        panels = full["dashboard"]["panels"]
        with_data = 0
        for panel in panels:
            target = panel["targets"][0]
            if panel["datasource"]["uid"] != "prometheus":
                continue
            _, _, result = http("http://localhost:3000/api/ds/query", {
                "queries": [{"refId": "A", "datasource": {"uid": "prometheus"}, "expr": target["expr"], "instant": True}],
                "from": "now-30m", "to": "now"}, g_headers, method="POST")
            frames = result["results"]["A"].get("frames") or []
            if any(f.get("data", {}).get("values") and f["data"]["values"][-1] for f in frames):
                with_data += 1
        prom_panels = sum(1 for p in panels if p["datasource"]["uid"] == "prometheus")
        print(f"{board['title']}: provisioned={full['meta'].get('provisioned')} "
              f"prometheus panels with data {with_data}/{prom_panels}")

    section("summary")
    print("FAILURES:" if failures else "all checks passed", *failures, sep="\n  ")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
