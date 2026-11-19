"""Exact-string survival of ISO dates and hyphenated names after LLMLingua-2 (prose, no selection)."""
import sys, os, re; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
hooks()
SUBJ = ["billing", "login", "search", "export", "mobile app", "onboarding", "alerts", "reports", "permissions", "audit log"]
paras = [f"Section {i+1} ({s}). The {s} module has an owner named team-{s.replace(' ', '-')}. Action item {i+1}: the owner must deliver the {s} fix by 2026-12-{10+i:02d}. "
         f"Background: the {s} work was delayed because of dependency churn, staffing gaps and unclear requirements in the previous quarter, and the steering group asked for weekly updates until the milestone is reached." for i, s in enumerate(SUBJ)]
r = run([{"role": "user", "content": "Meeting notes:\n\n" + "\n\n".join(paras) + "\n\nWhat are the deadlines?"}], ce=False)
t = r["text"]
dates = [f"2026-12-{10+i:02d}" for i, s in enumerate(SUBJ)]
owners = ["team-" + s.replace(" ", "-") for s in SUBJ]
print("tokens", r["tok_before"], "->", r["tok_after"], "actions", [m.get("action") for m in r["pc"]["messages"]])
print("ISO dates exact:", sum(d in t for d in dates), "/10;  hyphenated owners exact:", sum(o in t for o in owners), "/10")
print("sample:", re.findall(r"2026\s*-?\s*12\s*-?\s*\d\d", t)[:4], re.findall(r"team\s*-\s*[\w-]+", t)[:3])
