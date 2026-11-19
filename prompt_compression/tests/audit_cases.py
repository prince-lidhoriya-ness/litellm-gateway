"""The production-readiness audit's workloads, rebuilt for the regression tests (identical text to
reports/production-readiness-audit/scripts/exp1.py, exp2.py, exp7.py and exp8.py, so a failure here is the audit's
failure case coming back)."""

import random

SENT = [
    "The team reviewed the rollout plan and agreed that the migration should happen in stages across the regions.",
    "Customers have reported intermittent slowness when the dashboard loads large result sets during peak hours.",
    "An earlier incident showed that retry storms can amplify load when the downstream service starts to degrade.",
    "Several engineers pointed out that the documentation for the internal tooling is outdated and often misleading.",
    "The vendor confirmed that the fix will ship in the next maintenance window, although no exact date was given.",
    "It was noted that the staging environment differs from production in how it handles connection pooling.",
    "Finance asked for a breakdown of the monthly spend so that the budget review can be completed on time.",
    "Support leadership wants a clearer escalation path when a ticket remains unresolved for more than two days.",
]


def prose(n_sent, seed):
    r = random.Random(seed)
    return " ".join(r.choice(SENT) for _ in range(n_sent))


def case_c_log() -> str:
    """exp1 case C: 160-line checkout-service log, root cause (DB pool exhausted) 3 lines from the ord-7731 line."""
    logs = [f"2026-11-17T10:{i // 60:02d}:{i % 60:02d}Z INFO checkout-service req=req-{i:05d} user=u-{i % 37} "
            f"path=/v1/cart latency_ms={80 + i % 50}" for i in range(160)]
    logs[70] = "2026-11-17T10:01:10Z INFO checkout-service req=req-07731 order=ord-7731 path=/v1/checkout started"
    logs[71] = "2026-11-17T10:01:11Z INFO checkout-service req=req-07732 user=u-12 path=/v1/cart latency_ms=91"
    logs[72] = "2026-11-17T10:01:11Z INFO checkout-service req=req-07733 user=u-13 path=/v1/cart latency_ms=95"
    logs[73] = ("2026-11-17T10:01:12Z ERROR db-pool pool exhausted: max=20 active=20 waiting=41 "
                "(leaked connections in InventoryRepo.reserve)")
    logs[74] = "2026-11-17T10:01:12Z INFO checkout-service req=req-07734 user=u-14 path=/v1/cart latency_ms=99"
    logs[75] = "2026-11-17T10:01:13Z INFO checkout-service req=req-07735 user=u-15 path=/v1/cart latency_ms=97"
    logs[90] = "2026-11-17T10:01:30Z WARN checkout-service order=ord-7731 payment authorization timed out after 30000ms"
    logs[91] = "2026-11-17T10:01:31Z ERROR checkout-service order=ord-7731 returned 503 to client"
    return "\n".join(logs)


CASE_C_NEEDLES = ["pool exhausted", "max=20 active=20", "leaked connections", "InventoryRepo.reserve",
                  "timed out after 30000ms"]


def case_c(question="Why did order ord-7731 fail?") -> list:
    return [{"role": "user", "content": "Service logs from the checkout-service:\n\n" + case_c_log() + "\n\n" + question}]


def case_d() -> list:
    """exp1 case D: 220-line CI log, one failed step, a question without an identifier."""
    ci = [f"[{i:03d}] step=build-{i % 12} cache=hit duration={i % 9}.{i % 7}s status=ok" for i in range(220)]
    ci[140] = ("[140] step=deploy-canary status=FAILED: kubectl rollout status timed out; pod web-7f9c still "
               "CrashLoopBackOff (OOMKilled, limit 256Mi)")
    return [{"role": "user", "content": "CI pipeline output:\n\n" + "\n".join(ci) + "\n\nWhich step failed and why?"}]


CASE_D_NEEDLES = ["OOMKilled", "limit 256Mi", "CrashLoopBackOff"]


def exp2_log(root_cause_position: int, id_position: int = 80, n: int = 160) -> str:
    """exp2: the matched ord-7731 line and a root-cause line at a chosen distance."""
    lines = [f"2026-11-17T10:{i // 60:02d}:{i % 60:02d}Z INFO checkout-service req=req-{i:05d} user=u-{i % 37} "
             f"path=/v1/cart latency_ms={80 + i % 50}" for i in range(n)]
    lines[id_position] = "2026-11-17T10:01:20Z ERROR checkout-service order=ord-7731 returned 503 to client"
    lines[root_cause_position] = "2026-11-17T10:01:19Z ERROR db-pool pool exhausted: max=20 active=20 (ROOT-CAUSE-MARKER)"
    return "\n".join(lines)


EXP2_DISTANCES = (1, 2, 3, 5, 10, 30, -1, -2, -5, -30)
EXP2_QUESTIONS = ("Why did order ord-7731 fail?", "Why did the checkout fail?", "What went wrong with the 503 errors?",
                  "Why did req-00080 fail? (the order is ord-7731)", "What is the status of order ord-7731?",
                  "Review these logs and tell me why ord-7731 failed.", "Why did every order ord-7731 request fail?")

SUBJECTS = ["billing", "login", "search", "export", "mobile app", "onboarding", "alerts", "reports", "permissions",
            "audit log"]


def meeting_notes(repeat: int = 2) -> str:
    """exp7 (repeat=2) and exp8 (repeat=1): ten sections, each with an owner team-<x> and a deadline 2026-12-<d>."""
    paras = []
    for i, s in enumerate(SUBJECTS):
        paras.append(f"Section {i + 1} ({s}). The {s} module has an owner named team-{s.replace(' ', '-')}. "
                     f"Action item {i + 1}: the owner must deliver the {s} fix by 2026-12-{10 + i:02d}. "
                     + (f"Background: the {s} work was delayed because of dependency churn, staffing gaps and unclear "
                        f"requirements in the previous quarter, and the steering group asked for weekly updates until "
                        f"the milestone is reached. ") * repeat)
    return "\n\n".join(paras)


MEETING_DATES = [f"2026-12-{10 + i:02d}" for i in range(10)]
MEETING_OWNERS = ["team-" + s.replace(" ", "-") for s in SUBJECTS]
EXP7_QUESTIONS = ("Extract the action items and their owners.", "What are the deadlines?",
                  "List the owners and dates for billing, login and search.", "Extract all action items and owners.")


def case_g() -> tuple:
    """exp1 case G: a 12-paragraph memo with one decisive configuration value."""
    paras = [prose(6, 300 + i) for i in range(12)]
    paras[6] += " The decisive configuration value is IDLE_TIMEOUT_SECONDS=1800 and it must never be lowered below 900."
    messages = [{"role": "user", "content": "Read this design memo:\n\n" + "\n\n".join(paras)
                 + "\n\nWhat is the minimum allowed idle timeout?"}]
    return messages, ["IDLE_TIMEOUT_SECONDS=1800", "900"]


def case_j() -> tuple:
    """exp1 case J: identifiers inside long prose, in a user turn and in assistant history."""
    ident = (prose(4, 900) + " The tracking code for the incident is NIMBUS-5044 and it was opened against RFC-9110 "
             "section 5.2 on port 8443 running version 3.11.4 of the proxy. " + prose(4, 901))
    messages = [
        {"role": "user", "content": "Please remember the incident details below.\n\n" + ident + "\n\n" + prose(5, 902)},
        {"role": "assistant", "content": ident + "\n\n" + prose(6, 903)},
        {"role": "user", "content": "What was the tracking code and which port was in use?"},
    ]
    return messages, ["NIMBUS-5044", "RFC-9110", "section 5.2", "8443", "3.11.4"]
