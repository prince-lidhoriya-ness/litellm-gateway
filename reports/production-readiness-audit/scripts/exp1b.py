import sys
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exp1 import *
import re
hooks()
r = run(cases["J_ident_in_prose"]["msgs"])
for m in r["data"]["messages"]:
    t = tk.message_text(m)
    i = t.find("tracking")
    print(m["role"], "::", t[max(0,i-60):i+260].replace("\n"," ") if i>=0 else t[:200].replace("\n"," "))
    print()
print("=== G")
r = run(cases["G_prose_doc"]["msgs"])
t = r["text"]
for k in ("IDLE", "idle", "900", "decisive"):
    for mt in re.finditer(k, t):
        print(k, "->", t[max(0,mt.start()-80):mt.start()+120].replace("\n"," "))
        break
print("=== C kept lines:")
r = run(cases["C_backend_log_identifier"]["msgs"])
body = r["data"]["messages"][0]["content"]
print(body)
print("=== H stub")
r = run(cases["H_agent_old_unref"]["msgs"])
for m in r["data"]["messages"]:
    if m["role"]=="tool" and "masked by gateway" in tk.message_text(m):
        print(tk.message_text(m)); break
