"""metric_check.py -- does the lenient 'answer-contains' metric hide anything?  Compares it with a boundary-aware match
(answer must not be embedded inside a longer alphanumeric token) and with strict exact match, per family and arm.
Writes raw/results/metric_check.txt."""
import os, re, json, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
def L(p): return [json.loads(l) for l in open(os.path.join(ROOT, p), encoding='utf-8') if l.strip()]
norm = lambda s: re.sub(r'\s+', ' ', s.lower()).strip()
data = {f: {r['id']: r for r in L(f'data/{f}.jsonl')} for f in ['qa', 'logs', 'code']}
runs = L('raw/llm_runs.jsonl')
if os.path.exists(os.path.join(ROOT, 'raw', 'llm_runs_posthoc.jsonl')):
    runs += [dict(r, arm='base_rep' if r['arm'] == 'base' else r['arm']) for r in L('raw/llm_runs_posthoc.jsonl')]
print(runs[0].keys() if runs else 'no runs')
def contains(it, resp): return int(any(norm(a) in norm(resp) for a in it['answers']))
def bound(it, resp):
    r = norm(resp)
    return int(any(re.search(r'(?<![A-Za-z0-9_.\-])' + re.escape(norm(a)) + r'(?![A-Za-z0-9_\-]|\.\d)', r) for a in it['answers']))
def exact(it, resp): return int(any(norm(a) == norm(resp).strip(' .`\'"*') for a in it['answers']))
agg = {}
for r in runs:
    fam = r['item_id'].split('-')[0]
    if fam not in data: continue
    it = data[fam][r['item_id']]; resp = r.get('response') or r.get('text') or r.get('answer') or ''
    k = (fam, r['arm']); a = agg.setdefault(k, [0, 0, 0, 0, 0])
    a[0] += 1; a[1] += contains(it, resp); a[2] += bound(it, resp); a[3] += exact(it, resp); a[4] += len(resp)
lines = ["family | arm | n | contains | boundary-aware | exact | mean response chars", "---|---|---|---|---|---|---"]
maxdiff = 0
for (fam, arm), (n, c, b, e, ch) in sorted(agg.items()):
    lines.append(f"{fam} | {arm} | {n} | {c/n:.3f} | {b/n:.3f} | {e/n:.3f} | {ch/n:.0f}"); maxdiff = max(maxdiff, c - b)
lines.append(f"\nlargest number of items (of 40) credited by 'contains' but not by the boundary-aware match, any family/arm: {maxdiff}")
open(os.path.join(ROOT, 'raw', 'results', 'metric_check.txt'), 'w', encoding='utf-8').write("\n".join(lines) + "\n")
print("\n".join(lines))
