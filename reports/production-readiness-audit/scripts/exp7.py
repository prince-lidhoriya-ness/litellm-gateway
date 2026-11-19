"""Intent-gate probe: whole-document tasks phrased without the gate's keywords still allow passage dropping."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from h import *
hooks()
import random
SUBJ = ["billing", "login", "search", "export", "mobile app", "onboarding", "alerts", "reports", "permissions", "audit log"]
paras = []
for i, s in enumerate(SUBJ):
    paras.append(f"Section {i+1} ({s}). The {s} module has an owner named team-{s.replace(' ', '-')}. "
                 f"Action item {i+1}: the owner must deliver the {s} fix by 2026-12-{10+i:02d}. "
                 f"Background: the {s} work was delayed because of dependency churn, staffing gaps and unclear requirements in the previous quarter, "
                 f"and the steering group asked for weekly updates until the milestone is reached. " * 2)
doc = "\n\n".join(paras)
for q in ("Extract the action items and their owners.", "What are the deadlines?", "List the owners and dates for billing, login and search.",
          "Extract all action items and owners."):
    r = run([{"role": "user", "content": "Meeting notes:\n\n" + doc + "\n\n" + q}], ce=False)
    kept = sum(1 for i in range(10) if f"2026-12-{10+i:02d}" in r["text"]); owners = sum(1 for s_ in SUBJ if "team-" + s_.replace(" ", "-") in r["text"])
    print(f"{q!r:70} intent={r['pc'].get('intent')} tokens {r['tok_before']}->{r['tok_after']} dates_kept={kept}/10 owners_kept={owners}/10 actions={[m.get('action') for m in r['pc']['messages']]}")
