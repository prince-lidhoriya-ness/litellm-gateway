# monitoring

Observability stack for the LiteLLM gateway and its prompt pipeline. The design, signal inventory,
privacy rules and retention are in [`../docs/monitoring-plan.md`](../docs/monitoring-plan.md).

## Start

From the gateway folder (`litellm-gateway/`), with the quickstart stack already running:

```bash
docker compose -p litellm-monitoring --env-file .env -f monitoring/docker-compose.monitoring.yml up -d
docker compose -f docker-compose.quickstart.yml up -d litellm
```

- `-p litellm-monitoring` is required: `.env` sets `COMPOSE_PROJECT_NAME=litellm-gateway`, which
  otherwise overrides the file's `name:` and merges these services into the gateway project.
- `--env-file .env` supplies `POSTGRES_PASSWORD`, `REDIS_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`.
- The second command recreates only the LiteLLM container so it picks up `litellm_config.yaml`
  (callbacks `otel`, `langfuse_otel`, `prometheus`, observed pipeline hook) and the new env vars.

| Tool | URL | Login |
|---|---|---|
| Grafana (3 dashboards in folder "LiteLLM gateway") | http://localhost:3000 | `admin` / `GRAFANA_ADMIN_PASSWORD` from `.env` |
| Prometheus | http://localhost:9090 | - |
| Alertmanager | http://localhost:9093 | - |
| Jaeger | http://localhost:16686 | - |
| Loki (API, query through Grafana) | http://localhost:3100 | - |
| Langfuse | https://us.cloud.langfuse.com (project of the keys in `.env`) | your Langfuse account |
| LiteLLM metrics | http://localhost:4000/metrics | - |

All ports bind to 127.0.0.1.

## Files

| Path | What |
|---|---|
| `docker-compose.monitoring.yml` | Prometheus, Alertmanager, Grafana, Loki, Jaeger, OTel Collector, node_exporter, cAdvisor, postgres/redis exporters, DCGM (profile `gpu`) |
| `otel-collector/config.yaml` | OTLP in; traces -> Jaeger, logs -> Loki; scrubs prompt/completion attributes |
| `prometheus/prometheus.yml`, `prometheus/rules/alerts.yml` | scrape jobs, 15 alert rules |
| `alertmanager/alertmanager.yml` | routing (placeholder webhook receiver) |
| `loki/config.yaml` | single binary, 7-day retention, OTLP ingest |
| `grafana/provisioning/`, `grafana/dashboards/` | datasources (trace_id links Loki <-> Jaeger) and dashboards |
| `grafana/build_dashboards.py` | generates the dashboard JSON; edit and rerun |
| `monitoring.env.example` | every new environment variable with its default |
| `scripts/verify_observability.py` | end-to-end evidence (requests -> Jaeger, Loki, Prometheus, Langfuse, Grafana) |
| `scripts/measure_overhead.py`, `overhead/` | telemetry-on vs telemetry-off latency |
| `results/` | saved verification and overhead output |

Application side: `../observability/` (callback, metrics, JSON logs, privacy helpers, tests) and the
span hooks in `../prompt_compression/pipeline.py`.

## Verify

```bash
.venv-compression/Scripts/python monitoring/scripts/verify_observability.py
```

Sends one request per prompt type (the names are historical: sensitive, critical, non_sensitive, less_important) plus a streaming
one to `obs-priced-llama` (local Ollama `llama3.2:3b` with TEST prices), then checks each backend.
Last run: `results/verification.txt` (all checks passed).

Alert test (what was done to prove routing): copy `GatewayHighP95Latency` into a temporary rule file
with a 1 ms threshold, `curl -X POST http://localhost:9090/-/reload`, send a request, check
`http://localhost:9093/api/v2/alerts`, then delete the file and reload again.

## Overhead

```bash
# telemetry on (normal config)
.venv-compression/Scripts/python monitoring/scripts/measure_overhead.py --label on -n 150 --uncompressed-only
# telemetry off: every OTel/Prometheus/Langfuse/observability path disabled, same compression hook
docker compose -f docker-compose.quickstart.yml -f monitoring/overhead/no-telemetry.override.yml up -d litellm
.venv-compression/Scripts/python monitoring/scripts/measure_overhead.py --label off -n 150 --uncompressed-only
docker compose -f docker-compose.quickstart.yml up -d litellm      # restore
.venv-compression/Scripts/python monitoring/scripts/measure_overhead.py --compare
```

Needs the mock provider on the host (`obs-mock` model):
`.venv-compression/Scripts/python prompt_compression/dev/mock_openai_server.py --port 4010`.

Measured here (150 sequential uncompressed requests each, mock provider): p50 32.4 -> 37.0 ms
(+4.6 ms), mean 34.8 -> 40.2 ms (+5.4 ms), p95 53.0 -> 53.6 ms. With compression in the mix the
difference is below LLMLingua's run-to-run variance (hundreds of ms on this CPU).

## Known limits on this machine

- **Containers by id, not name**: cAdvisor cannot reach containerd under Rancher Desktop, so it reads
  `/docker/<id>` cgroups; metrics carry a 12-char `container_id` (map it with `docker ps`).
- **Host metrics are the Docker VM's**: node_exporter runs in the WSL VM that hosts the containers.
  Windows host metrics need windows_exporter installed on Windows (not done).
- **No GPU**: the DCGM exporter is defined (`--profile gpu`) but never ran here.
- **Jaeger pinned to 2.20.0**: 2.21+ dropped the legacy `/api/services` API that Grafana 13.2.5's
  Jaeger datasource uses. Jaeger storage is in memory (dev).
- **Langfuse shows the generation span only**: pipeline spans go to Jaeger; Langfuse gets the
  category as a trace tag (`prompt_category:<sensitive|general>`), plus hashed user, session and usage/cost.
- On Windows, scripts use `127.0.0.1`: `localhost` costs ~2 s per request in Python while IPv6 `::1` times out.
