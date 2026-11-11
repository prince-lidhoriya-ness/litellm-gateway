# Plan: Full-Stack Observability for LiteLLM Gateway (Langfuse + Prometheus/Grafana/Loki)

## Context found
- Proxy (docker-compose.quickstart.yml + litellm_config.yaml) already wired for Langfuse via `langfuse_otel` OTel v2 callback; `.env` has Langfuse keys but some are commented/duplicated, and contains a suspicious embedded instruction comment (line ~10) resembling prompt injection - flag to user, recommend deleting.
- No metrics/logs/infra stack exists yet (no Prometheus/Grafana/Loki/exporters).
- ai-features/app.py -> rag.py (retrieve, uses Chroma + SentenceTransformer) -> rerank.py (CrossEncoder) -> litellm.completion() via litellm_proxy. These steps are invisible to proxy-side tracing today.
- No requirements.txt in ai-features/.

## User decisions (from clarifying questions)
- Stack: Prometheus + Grafana + Loki (self-hosted, docker-compose).
- Infra scope: containers only (cAdvisor) for litellm/postgres/redis - no node-exporter/host metrics.
- Add Postgres exporter + Redis exporter.
- Alerting: Grafana unified alerting (no separate Alertmanager service).
- Add Langfuse SDK `@observe` tracing inside app.py/rag.py/rerank.py for step-level spans.
- Deployment target: local/dev machine only.

## Steps

### Phase 1 - Langfuse cleanup & proxy metrics (foundation)
1. Clean `.env`: remove duplicate/commented Langfuse key lines, keep one active set, remove the suspicious injected comment line (confirm with user before deleting).
2. `litellm_config.yaml`: add `"prometheus"` to `litellm_settings.callbacks` list (alongside `langfuse_otel` and compression guardrail) to enable LiteLLM's built-in `/metrics` endpoint (request count, latency histogram, token usage, spend by model/key/team, error counts).
3. Verify `docker-compose.quickstart.yml` already exposes port 4000 (metrics served at `/metrics` on same port) - no port change needed, just confirm reachability from a shared compose network.

### Phase 2 - Metrics & infra stack (new compose file, parallel with Phase 3)
4. Create `monitoring/docker-compose.monitoring.yml` with services: `prometheus`, `grafana`, `cadvisor`, `postgres-exporter`, `redis-exporter`. Run alongside the main stack via `docker compose -f docker-compose.quickstart.yml -f monitoring/docker-compose.monitoring.yml up -d` so they share the default network and can resolve `litellm`, `db`, `redis` by service name.
5. `monitoring/prometheus/prometheus.yml`: scrape configs for `litellm:4000/metrics`, `cadvisor:8080`, `postgres-exporter:9187`, `redis-exporter:9121`.
6. `postgres-exporter`: point at `DATABASE_URL` (reuse `POSTGRES_PASSWORD` from `.env`). `redis-exporter`: point at redis with `REDIS_PASSWORD`.
7. `cadvisor`: standard container metrics (mount `/var/run/docker.sock`, `/sys`, `/var/lib/docker`).
8. `grafana`: provision datasources (Prometheus + Loki) via `monitoring/grafana/provisioning/datasources/datasources.yml`; import community dashboards (by ID, via UI or provisioning): cAdvisor (14282), Postgres Exporter (9628), Redis Exporter (11835); build/add one custom LiteLLM overview dashboard (request rate, p50/p95/p99 latency, error rate, token usage & spend by model) sourced from the `prometheus` callback metrics.

### Phase 3 - Centralized logs (parallel with Phase 2)
9. Add `loki` and `promtail` services to `monitoring/docker-compose.monitoring.yml`.
10. `monitoring/loki/loki-config.yml`: minimal single-binary config, local filesystem storage.
11. `monitoring/promtail/promtail-config.yml`: scrape all container logs via Docker service discovery (mount `/var/run/docker.sock` + `/var/lib/docker/containers`), push to `loki:3100`. Captures litellm proxy logs, Postgres, Redis, cAdvisor logs - one place for everything.
12. Add Loki as a Grafana datasource (same provisioning file as step 8) so logs and metrics are explorable side by side.

### Phase 4 - Alerting (depends on Phase 2 metrics existing)
13. Add Grafana provisioned alert rules (`monitoring/grafana/provisioning/alerting/rules.yml`) for: proxy error rate > threshold, p95 latency > threshold, spend-rate spike, and `up == 0` (any scrape target/container down). Configure a contact point (e.g. email/webhook - ask user for delivery channel before finalizing).

### Phase 5 - Application-level tracing (independent, can run in parallel with Phases 2-4)
14. Add `langfuse` to a new `ai-features/requirements.txt` (plus existing implicit deps: chromadb, sentence-transformers, litellm, python-dotenv, pydantic) so the script's dependencies are reproducible.
15. Instrument `ai-features/rag.py` (`retrieve`) and `ai-features/rerank.py` (`rerank`) with Langfuse `@observe` decorators to create child spans (retrieval latency, rerank latency/scores).
16. Instrument `ai-features/app.py` (`answer_question`) with `@observe` as the top-level span so retrieve -> rerank -> LLM generation nest under one trace.
17. Verify/establish trace propagation from app.py's in-process OTel span to the proxy's OTel span for the LLM call (W3C `traceparent` header over the HTTP call to the proxy). If automatic propagation doesn't nest correctly in Langfuse UI, fall back to explicit correlation via `metadata={"session_id": ...}` or `trace_id` tagging passed into `litellm.completion()`.

## Relevant files
- `litellm_config.yaml` - add `prometheus` callback.
- `.env` - cleanup Langfuse keys, remove suspicious comment (confirm with user first).
- `docker-compose.quickstart.yml` - no changes expected beyond confirming port/network sharing.
- `monitoring/docker-compose.monitoring.yml` - new: prometheus, grafana, cadvisor, postgres-exporter, redis-exporter, loki, promtail.
- `monitoring/prometheus/prometheus.yml` - new scrape config.
- `monitoring/loki/loki-config.yml`, `monitoring/promtail/promtail-config.yml` - new.
- `monitoring/grafana/provisioning/datasources/datasources.yml`, `monitoring/grafana/provisioning/dashboards/*`, `monitoring/grafana/provisioning/alerting/rules.yml` - new.
- `ai-features/requirements.txt` - new.
- `ai-features/app.py`, `ai-features/rag.py`, `ai-features/rerank.py` - add Langfuse `@observe` instrumentation.

## Verification
1. `docker compose -f docker-compose.quickstart.yml -f monitoring/docker-compose.monitoring.yml up -d` - all services healthy.
2. Hit `http://localhost:4000/metrics` - confirm Prometheus-format output with token/latency/spend metrics.
3. Prometheus UI (`:9090/targets`) - all scrape targets `UP`.
4. Grafana (`:3000`) - datasources connected, LiteLLM dashboard shows live latency/error/token/spend panels; Loki Explore shows container logs; cAdvisor/Postgres/Redis dashboards populated.
5. Trigger a few requests through `ai-features/app.py` - confirm a single nested trace appears in Langfuse UI (retrieve -> rerank -> generation spans) with cost/token/latency on the generation span.
6. Stop a container (e.g. `redis`) - confirm Grafana alert fires (`up == 0`) and reaches the configured contact point.

## Further Considerations
1. Alert contact point (email/Slack/webhook) not yet specified - ask user before implementing step 13.
2. Confirm with user whether to delete the suspicious injected comment line in `.env` before editing that file.
