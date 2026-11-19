-- Holdout report (reports/production-readiness-audit/STRATEGY.md, Phase 2.1): billed cost per conversation and latency,
-- holdout against treatment, per team, from LiteLLM's spend logs. The arm and the conversation key are written into
-- spend_logs_metadata.gateway_holdout by observability/measurement.py; `spend` is LiteLLM's response_cost (provider
-- price, including cached and cache-write tokens where the provider reports them).
--
--   psql "$DATABASE_URL" -v days=14 -f observability/holdout_report.sql
--
-- Read it as: usd_per_conversation (treatment) vs (holdout) is the cost effect of the optimisation; p95_seconds is its
-- latency effect. Only arms "treatment" and "holdout" are compared; "excluded" (client opt-out) and "internal" (the
-- gateway's own quality checks) are listed so their cost is visible. A conversation's requests always share one arm.

\if :{?days}
\else
  \set days 14
\endif

WITH rows AS (
    SELECT
        COALESCE(team_id, '')                                                      AS team_id,
        metadata -> 'spend_logs_metadata' -> 'gateway_holdout' ->> 'arm'          AS arm,
        metadata -> 'spend_logs_metadata' -> 'gateway_holdout' ->> 'key'          AS conversation,
        COALESCE(spend, 0)                                                         AS spend,
        COALESCE(prompt_tokens, 0)                                                 AS prompt_tokens,
        EXTRACT(EPOCH FROM ("endTime" - "startTime"))                              AS seconds
    FROM "LiteLLM_SpendLogs"
    WHERE "startTime" >= now() - make_interval(days => :days)
      AND metadata -> 'spend_logs_metadata' -> 'gateway_holdout' ->> 'arm' IS NOT NULL
)
SELECT
    team_id,
    arm,
    count(DISTINCT conversation)                                               AS conversations,
    count(*)                                                                   AS requests,
    round(sum(spend)::numeric, 6)                                              AS billed_usd,
    round((sum(spend) / NULLIF(count(DISTINCT conversation), 0))::numeric, 6)  AS usd_per_conversation,
    round(avg(prompt_tokens)::numeric, 1)                                      AS prompt_tokens_per_request,
    round(percentile_cont(0.5) WITHIN GROUP (ORDER BY seconds)::numeric, 3)    AS p50_seconds,
    round(percentile_cont(0.95) WITHIN GROUP (ORDER BY seconds)::numeric, 3)   AS p95_seconds
FROM rows
GROUP BY team_id, arm
ORDER BY team_id, arm;
