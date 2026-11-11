"""Deterministic benchmark dataset for the four gateway configurations (baseline, compression, CE, CE + compression).

    .venv-compression/Scripts/python reports/context-engineering/scripts/dataset.py
writes reports/context-engineering/data/bench.jsonl. Same seed, same file, byte for byte.

Families (each item says whether context engineering is expected to act, `ce_expected`):
  short_chat        3-turn chats far below every threshold: nothing should change
  doc_qa            single-turn document QA from reports/compression-fit (the compression stage's home ground)
  log_lookup        single-turn log/JSON lookups from reports/compression-fit (record selection)
  code              single-turn code questions from reports/compression-fit (code must stay byte-identical)
  long_chat         10-turn chats; a fact stated early (inside the compactable span) or recently, then asked about
  agent_tools       one task, 7 tool calls with ~440-token log outputs; the question needs an old output the next
                    answer referenced, an old output nobody referenced (the risky case for masking), or a recent one
  agent_debug       like agent_tools, but the newest output is a failing test run (the error guard must keep it)
  structured_chat   multi-turn chat whose latest message carries JSON and code that must reach the model verbatim

Every multi-turn item starts with the instruction "Start every answer with 'Answer:'" in the first user message
(pinned by context engineering), which the quality run scores as instruction following.
"""

import json
import random
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GATEWAY = HERE.parents[2]
FIT = GATEWAY / "reports" / "compression-fit" / "data"
OUT = ROOT / "data" / "bench.jsonl"
SEED = 20261111

SYSTEM = "You are a precise engineering assistant for the payments platform team."
FIRST = ("We are reviewing the payments platform together. Start every answer with 'Answer:' and keep answers short. "
         "Never invent identifiers.")
FIRST_REPLY = "Answer: Understood. I will start every answer with 'Answer:' and keep it short."
INSTR = ("Answer the question using only the document below. "
         "Reply with only the answer value (a name, number or identifier), nothing else.")

TOPICS = [
    "the billing service retries failed card captures with exponential backoff",
    "the warehouse dashboard caches stock counts per region",
    "the onboarding emails are sent by a nightly batch job reading the marketing queue",
    "the search index is rebuilt on Sundays from the catalog stream",
    "the mobile app stores session tokens in the secure enclave",
    "the reporting cluster runs on spot instances with query checkpoints",
    "the support chatbot hands off to a human after two failed intents",
    "the invoice generator renders templates in a sandboxed engine",
    "the fraud model scores transactions in real time",
    "the data retention policy deletes raw event logs after ninety days",
    "the ledger service reconciles settlements every hour",
    "the notification gateway batches push messages per device",
]


def turn(i: int, rng: random.Random) -> list:
    topic = TOPICS[i % len(TOPICS)]
    details = " ".join(
        f"Point {j}: the owning team reviews {rng.choice(['alerts', 'dashboards', 'runbooks', 'capacity'])} "
        f"for this part every {rng.choice(["week", "sprint", "month"])}." for j in range(16))
    return [{"role": "user", "content": f"Topic {i}: how does it work that {topic}?"},
            {"role": "assistant", "content": f"Answer: In short, {topic}. {details}"}]


def head() -> list:
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": FIRST},
            {"role": "assistant", "content": FIRST_REPLY}]


def long_chat(n: int, rng: random.Random, where: str) -> dict:
    code = f"{rng.choice(['ZEPHYR', 'NIMBUS', 'ORCHID', 'TUNDRA'])}-{rng.randint(1000, 9999)}"
    owner = rng.choice(["Priya Raman", "Tomas Lindqvist", "Akosua Mensah", "Kenji Sato"])
    messages = head()
    turns = 10
    fact_turn = 1 if where == "old" else turns - 1
    for i in range(turns):
        pair = turn(i + n, rng)
        if i == fact_turn:
            pair[0]["content"] += f" Also note: we agreed the rollout codename is {code} and {owner} owns the rollout."
            pair[1]["content"] = (f"Answer: Noted, the rollout codename is {code}, owned by {owner}. "
                                  + pair[1]["content"].split(". ", 1)[1])
        messages += pair
    messages.append({"role": "user", "content": "What rollout codename did we agree on, and who owns the rollout?"})
    return {"messages": messages, "answers": [code], "complete": [code, owner.split()[0]], "key_strings": [code],
            "needle": "codename", "ce_expected": True}


def log_lines(rng: random.Random, n: int, service: str) -> list:
    lines = []
    for i in range(n):
        lines.append(f"2026-11-0{rng.randint(1, 9)}T1{rng.randint(0, 9)}:{rng.randint(10, 59)}:{rng.randint(10, 59)}Z "
                     f"INFO svc={service} req=req-{rng.randrange(16**6):06x} status={rng.choice([200, 200, 201, 204])} "
                     f"latency_ms={rng.randint(20, 900)} user=u-{rng.randint(10000, 99999)} region="
                     f"{rng.choice(['eu-west-1', 'us-east-2', 'ap-south-1'])}")
    return lines


def tool_round(call_id: str, name: str, arguments: dict, output: str, reply: str) -> list:
    return [{"role": "assistant", "content": None, "tool_calls": [
                {"id": call_id, "type": "function", "function": {"name": name, "arguments": json.dumps(arguments)}}]},
            {"role": "tool", "tool_call_id": call_id, "content": output},
            {"role": "assistant", "content": reply}]


def agent(n: int, rng: random.Random, where: str, debug: bool = False) -> dict:
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": FIRST + " Investigate slow cart requests using the log tools."}]
    services = ["cart", "checkout", "billing", "ledger", "search", "notify", "auth"]
    rounds = []
    for r, service in enumerate(services):
        lines = log_lines(rng, 11, service)
        rounds.append(lines)
    target_round = {"old_ref": 1, "old_unref": 0, "recent": 6}[where]
    target_line = rounds[target_round][5]
    req = target_line.split("req=")[1].split()[0]
    latency = target_line.split("latency_ms=")[1].split()[0]
    for r, service in enumerate(services):
        reply = f"Answer: {service} looks normal so far, checking the next service."
        if r == target_round and where == "old_ref":
            reply = f"Answer: request {req} in {service} is the one to watch; checking the next service."
        messages += tool_round(f"call_{n}_{r}", "read_logs", {"service": service, "window": "1h"},
                               "\n".join(rounds[r]), reply)
    answers = [latency]
    question = f"What was the latency_ms of request {req}?"
    if debug:
        failing = f"tests/test_{rng.choice(['cart', 'refunds', 'ledger'])}.py::test_case_{rng.randint(10, 99)}"
        out = "\n".join([f"tests/test_misc.py::test_{i} PASSED" for i in range(30)] +
                        [f"FAILED {failing} - AssertionError: expected 200, got 500"] +
                        ["=== 1 failed, 30 passed in 4.10s ==="])
        messages += [{"role": "assistant", "content": None, "tool_calls": [
            {"id": f"call_{n}_t", "type": "function", "function": {"name": "run_tests", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": f"call_{n}_t", "content": out},
            {"role": "assistant", "content": "Answer: One test fails; looking into it."}]
        question = "Which test is failing? Give its full test id."
        answers = [failing]
        req = failing
    messages.append({"role": "user", "content": question})
    return {"messages": messages, "answers": answers, "complete": answers, "key_strings": [req],
            "needle": req, "ce_expected": True}


def structured(n: int, rng: random.Random) -> dict:
    messages = head()
    for i in range(4):
        messages += turn(i + n, rng)
    orders = [{"order_id": f"ORD-{rng.randint(1000, 9999)}", "total": round(rng.uniform(10, 900), 2),
               "status": rng.choice(["paid", "refunded", "pending"])} for _ in range(6)]
    target = orders[3]
    code = ("```python\ndef refund_total(orders: list[dict]) -> float:\n"
            "    return round(sum(o['total'] for o in orders if o['status'] == 'refunded'), 2)\n```")
    blob = json.dumps(orders, indent=1)
    messages.append({"role": "user", "content": f"Here are the orders:\n\n{blob}\n\nAnd the helper:\n\n{code}\n\n"
                                                f"What is the total of order {target['order_id']}?"})
    return {"messages": messages, "answers": [f"{target['total']}"], "complete": [f"{target['total']}"],
            "key_strings": [target["order_id"], f"{target['total']}", "def refund_total(orders: list[dict]) -> float:"],
            "needle": target["order_id"], "ce_expected": False}


def short_chat(n: int, rng: random.Random) -> dict:
    city = rng.choice(["Lisbon", "Nairobi", "Osaka", "Quito"])
    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": f"Our next offsite is in {city}. Start every answer with 'Answer:'."},
                {"role": "assistant", "content": f"Answer: Noted, the offsite is in {city}."},
                {"role": "user", "content": "Which city is the offsite in?"}]
    return {"messages": messages, "answers": [city], "complete": [city], "key_strings": [city], "needle": city,
            "ce_expected": False}


def fit_items(family: str, count: int) -> list:
    rows = [json.loads(line) for line in (FIT / f"{family}.jsonl").read_text(encoding="utf-8").splitlines() if line]
    items = []
    for row in rows[:count]:
        prompt = f"{INSTR}\n\nDocument:\n{row['context']}\n\nQuestion: {row['question']}\nAnswer:"
        items.append({"messages": [{"role": "user", "content": prompt}], "answers": row["answers"],
                      "complete": row["answers"], "key_strings": row.get("key_strings") or row["answers"],
                      "needle": row["answers"][0], "ce_expected": False, "source": row["id"]})
    return items


def build() -> list:
    rng = random.Random(SEED)
    items = []

    def add(family, item, variant=""):
        items.append({"id": f"{family}-{sum(1 for i in items if i['family'] == family):03d}", "family": family,
                      "variant": variant, **item})
    for n in range(6):
        add("short_chat", short_chat(n, rng))
    for family, label in (("qa", "doc_qa"), ("logs", "log_lookup"), ("code", "code")):
        for item in fit_items(family, 6 if family != "code" else 4):
            add(label, item)
    for n in range(8):
        where = "old" if n % 2 == 0 else "recent"
        add("long_chat", long_chat(n, rng, where), where)
    for n, where in enumerate(["old_ref", "old_unref", "recent"] * 3):
        add("agent_tools", agent(n, rng, where), where)
    for n in range(3):
        add("agent_debug", agent(100 + n, rng, "recent", debug=True), "error_guard")
    for n in range(4):
        add("structured_chat", structured(n, rng))
    return items


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    items = build()
    OUT.write_text("".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items), encoding="utf-8")
    counts = {}
    for i in items:
        counts[i["family"]] = counts.get(i["family"], 0) + 1
    print(f"wrote {OUT} ({len(items)} items): {counts}")


if __name__ == "__main__":
    main()
