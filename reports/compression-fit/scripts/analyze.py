"""analyze.py -- turns raw/compressed.jsonl + raw/llm_runs.jsonl into raw/results/*.json|csv|md (every number in REPORT.md section 6
that is labelled 'local' comes from these files).  Run with the gateway venv (needs numpy, scipy):
  .venv-compression/Scripts/python.exe reports/compression-fit/scripts/analyze.py
"""
import os, sys, json, re, itertools, math, csv
import numpy as np
from scipy import stats

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
RES = os.path.join(ROOT, 'raw', 'results')
os.makedirs(RES, exist_ok=True)
ARMS = ['base', 'll2_2x', 'll2_3x', 'll2d_2x', 'll2g_gw', 'll1_2x', 'sc_2x', 'rand_2x', 'qaware_2x']   # ll2d_2x and ll2g_gw = post-hoc arms (added after the main results were seen)
LABEL = {'base': 'uncompressed', 'll2_2x': 'LLMLingua-2 (~2x)', 'll2_3x': 'LLMLingua-2 (~3x)', 'll2d_2x': 'LLMLingua-2 + digit protection (~2x, post-hoc)', 'll2g_gw': 'LLMLingua-2 at the gateway non_sensitive setting (rate 0.6 + digits, post-hoc)', 'll1_2x': 'LLMLingua v1/GPT-2 (~2x)',
         'sc_2x': 'Selective-Context-style (2x)', 'rand_2x': 'random word drop (2x)', 'qaware_2x': 'query-aware TF-IDF (2x)'}
FAMS = ['qa', 'logs', 'code']
RNG = np.random.default_rng(20261105)
B = int(os.environ.get('BOOT', '10000'))


def load_jsonl(p):
    return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]


def norm(s):
    return re.sub(r'\s+', ' ', s.lower()).strip()


def nows(s):
    return re.sub(r'\s+', '', s.lower())


def wilson(k, n, z=1.96):
    if n == 0:
        return (float('nan'), float('nan'))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def boot_ci(x, f, b=B):
    x = np.asarray(x, float)
    idx = np.random.default_rng(20261105).integers(0, len(x), size=(b, len(x)))   # fresh generator per call: intervals do not depend on call order or on which arms exist
    v = np.array([f(x[i]) for i in idx])
    return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


def pct(x, q):
    return float(np.percentile(np.asarray(x, float), q))


def mcnemar(a, b):
    """a,b: 0/1 arrays (paired). returns (b_only, a_only, exact p)."""
    a, b = np.asarray(a), np.asarray(b)
    n10, n01 = int(((a == 1) & (b == 0)).sum()), int(((a == 0) & (b == 1)).sum())
    n = n10 + n01
    p = 1.0 if n == 0 else float(stats.binomtest(min(n10, n01), n, 0.5).pvalue)
    return n10, n01, p


data = {f: {r['id']: r for r in load_jsonl(os.path.join(ROOT, 'data', f'{f}.jsonl'))} for f in FAMS + ['pii']}
comp = {(r['item_id'], r['arm']): r for r in load_jsonl(os.path.join(ROOT, 'raw', 'compressed.jsonl'))}
runs = {(r['item_id'], r['arm']): r for r in load_jsonl(os.path.join(ROOT, 'raw', 'llm_runs.jsonl'))} if os.path.exists(os.path.join(ROOT, 'raw', 'llm_runs.jsonl')) else {}
out = {'arms': LABEL}
# post-hoc run: a repeat of the baseline (kept apart as 'base_rep') and the post-hoc arm, sent in a later session (raw/llm_runs_posthoc.jsonl)
posthoc_base = {}
_ph = os.path.join(ROOT, 'raw', 'llm_runs_posthoc.jsonl')
if os.path.exists(_ph):
    for _r in load_jsonl(_ph):
        if _r['arm'] == 'base':
            posthoc_base[_r['item_id']] = _r
        else:
            runs[(_r['item_id'], _r['arm'])] = _r


def correct(item, resp):
    r = norm(resp)
    return int(any(norm(a) in r for a in item['answers']))


def exact(item, resp):
    r = norm(resp).strip(' .`\'"*')
    return int(any(norm(a) == r for a in item['answers']))


# ------------------------------------------------------------------ 1. quality, ratio, latency per family x arm
rows = []
per_item = {}   # (fam, arm) -> dict(id -> correct)
for fam in FAMS:
    ids = [i for i in data[fam] if all((i, a) in runs for a in ARMS)]
    out.setdefault('n_items', {})[fam] = len(ids)
    for arm in ARMS:
        c = np.array([correct(data[fam][i], runs[(i, arm)]['response']) for i in ids])
        em = np.array([exact(data[fam][i], runs[(i, arm)]['response']) for i in ids])
        per_item[(fam, arm)] = dict(zip(ids, c))
        llm = np.array([runs[(i, arm)]['wall_s'] for i in ids])
        cw = np.array([comp[(i, arm)]['wall_s'] if arm != 'base' else 0.0 for i in ids])
        cc = np.array([comp[(i, arm)]['cpu_s'] if arm != 'base' else 0.0 for i in ids])
        e2e = llm + cw
        ptok = np.array([runs[(i, arm)]['prompt_tokens'] for i in ids], float)
        btok = np.array([runs[(i, 'base')]['prompt_tokens'] for i in ids], float)
        tin = np.array([comp[(i, arm)]['tok_in'] for i in ids], float) if arm != 'base' else None
        tout = np.array([comp[(i, arm)]['tok_out'] for i in ids], float) if arm != 'base' else None
        lo, hi = wilson(int(c.sum()), len(c))
        row = dict(family=fam, arm=arm, n=len(ids), acc=c.mean(), acc_lo=lo, acc_hi=hi, em=em.mean(),
                   ratio_ctx_cl100k=(tin.sum() / tout.sum()) if arm != 'base' else 1.0,
                   ratio_prompt_target=float(btok.sum() / ptok.sum()), prompt_tokens_mean=float(ptok.mean()), tokens_saved_mean=float((btok - ptok).mean()),
                   e2e_p50=pct(e2e, 50), e2e_p90=pct(e2e, 90), e2e_p50_ci=boot_ci(e2e, lambda v: np.percentile(v, 50)), e2e_p90_ci=boot_ci(e2e, lambda v: np.percentile(v, 90)),
                   llm_p50=pct(llm, 50), llm_p90=pct(llm, 90), comp_wall_p50=pct(cw, 50), comp_wall_p90=pct(cw, 90), comp_cpu_mean=float(cc.mean()), comp_cpu_p90=pct(cc, 90))
        if arm != 'base':
            d = c - np.array([per_item[(fam, 'base')][i] for i in ids])
            row['d_acc_vs_base'] = float(d.mean()); row['d_acc_ci'] = boot_ci(d, np.mean)
            n10, n01, p = mcnemar([per_item[(fam, 'base')][i] for i in ids], c)
            row.update(base_only_right=n10, arm_only_right=n01, mcnemar_p=p)
            d_e2e = e2e - np.array([runs[(i, 'base')]['wall_s'] for i in ids])
            row['d_e2e_mean'] = float(d_e2e.mean()); row['d_e2e_ci'] = boot_ci(d_e2e, np.mean)
        rows.append(row)
out['rows'] = rows

# pooled across the three families
pool = []
for arm in ARMS:
    c = np.concatenate([[per_item[(f, arm)][i] for i in per_item[(f, arm)]] for f in FAMS])
    b = np.concatenate([[per_item[(f, 'base')][i] for i in per_item[(f, 'base')]] for f in FAMS])
    lo, hi = wilson(int(c.sum()), len(c))
    r = dict(arm=arm, n=len(c), acc=float(c.mean()), acc_lo=lo, acc_hi=hi)
    if arm != 'base':
        n10, n01, p = mcnemar(b, c); r.update(d_acc=float((c - b).mean()), d_ci=boot_ci(c - b, np.mean), mcnemar_p=p)
    pool.append(r)
out['pooled'] = pool

# ------------------------------------------------------------------ 2. pairwise separability between compressors (per family and pooled)
pair = []
for fam in FAMS + ['pooled']:
    for a1, a2 in itertools.combinations([x for x in ARMS if x != 'base'], 2):
        if fam == 'pooled':
            x = np.concatenate([[per_item[(f, a1)][i] for i in per_item[(f, a1)]] for f in FAMS]); y = np.concatenate([[per_item[(f, a2)][i] for i in per_item[(f, a2)]] for f in FAMS])
        else:
            ids = list(per_item[(fam, a1)]); x = np.array([per_item[(fam, a1)][i] for i in ids]); y = np.array([per_item[(fam, a2)][i] for i in ids])
        n10, n01, p = mcnemar(x, y)
        pair.append(dict(family=fam, a=a1, b=a2, a_only=n10, b_only=n01, diff=float(x.mean() - y.mean()), p=p, separable=bool(p < 0.05)))
out['pairwise'] = pair

# ------------------------------------------------------------------ 3. evidence retention (no LLM; all items; much higher power)
ret = []
for fam in FAMS:
    for arm in ARMS[1:]:
        ids = list(data[fam])
        ans_v = [int(all(a in comp[(i, arm)]['text'] for a in data[fam][i]['answers'][:1])) for i in ids]
        ans_w = [int(all(nows(a) in nows(comp[(i, arm)]['text']) for a in data[fam][i]['answers'][:1])) for i in ids]
        key_v = [int(all(k in comp[(i, arm)]['text'] for k in data[fam][i]['key_strings'])) for i in ids]
        key_w = [int(all(nows(k) in nows(comp[(i, arm)]['text']) for k in data[fam][i]['key_strings'])) for i in ids]
        for nm, v in [('answer_verbatim', ans_v), ('answer_ws_insensitive', ans_w), ('all_keys_verbatim', key_v), ('all_keys_ws_insensitive', key_w)]:
            lo, hi = wilson(sum(v), len(v))
            ret.append(dict(family=fam, arm=arm, metric=nm, rate=sum(v) / len(v), lo=lo, hi=hi, n=len(v)))
out['retention'] = ret

# PII fields
pii = []
fields = data['pii'][next(iter(data['pii']))]['meta']['fields']
for arm in ARMS[1:]:
    if arm.startswith('qaware'):
        continue
    ids = list(data['pii'])
    allv = allw = 0
    for k, fld in enumerate(fields):
        v = [int(data['pii'][i]['key_strings'][k] in comp[(i, arm)]['text']) for i in ids]
        w = [int(nows(data['pii'][i]['key_strings'][k]) in nows(comp[(i, arm)]['text'])) for i in ids]
        lo, hi = wilson(sum(v), len(v))
        pii.append(dict(arm=arm, field=fld, verbatim=sum(v) / len(v), verbatim_lo=lo, verbatim_hi=hi, ws_insensitive=sum(w) / len(w), n=len(v)))
    av = [int(all(s in comp[(i, arm)]['text'] for s in data['pii'][i]['key_strings'])) for i in ids]
    aw = [int(all(nows(s) in nows(comp[(i, arm)]['text']) for s in data['pii'][i]['key_strings'])) for i in ids]
    lo, hi = wilson(sum(av), len(av))
    pii.append(dict(arm=arm, field='ALL_FIELDS_INTACT', verbatim=sum(av) / len(av), verbatim_lo=lo, verbatim_hi=hi, ws_insensitive=sum(aw) / len(aw), n=len(av)))
    pr = [comp[(i, arm)] for i in ids]
    pii.append(dict(arm=arm, field='_ratio_cl100k', verbatim=sum(r['tok_in'] for r in pr) / sum(r['tok_out'] for r in pr), n=len(pr)))
out['pii'] = pii

# ------------------------------------------------------------------ 4. failure attribution: lost evidence vs present-but-wrong
fa = []
for fam in FAMS:
    for arm in ARMS[1:]:
        ids = list(per_item[(fam, arm)])
        wrong = [i for i in ids if per_item[(fam, arm)][i] == 0]
        lost = [i for i in wrong if not all(nows(a) in nows(comp[(i, arm)]['text']) for a in data[fam][i]['answers'][:1])]
        base_ok_wrong = [i for i in wrong if per_item[(fam, 'base')][i] == 1]
        fa.append(dict(family=fam, arm=arm, wrong=len(wrong), wrong_and_evidence_lost=len(lost), wrong_but_evidence_present=len(wrong) - len(lost),
                       wrong_where_base_right=len(base_ok_wrong)))
out['failure_attribution'] = fa

# ------------------------------------------------------------------ 5. latency model + break-even (derived from the local runs)
lat = {}
b_rows = [r for k, r in runs.items() if k[1] == 'base']
pf = [r['prompt_eval_ns'] / 1e6 / r['prompt_tokens'] for r in b_rows if r['prompt_tokens']]
lat['prefill_ms_per_token_median'] = float(np.median(pf)); lat['prefill_ms_per_token_p10_p90'] = [pct(pf, 10), pct(pf, 90)]
gen = [r['eval_ns'] / 1e6 / max(r['gen_tokens'], 1) for r in b_rows]
lat['decode_ms_per_token_median'] = float(np.median(gen))
for arm in ARMS[1:]:
    xs = np.array([comp[(i, arm)]['tok_in'] for i in data['qa'] | data['logs'] | data['code'] if (i, arm) in comp], float)
    ys = np.array([comp[(i, arm)]['wall_s'] for i in data['qa'] | data['logs'] | data['code'] if (i, arm) in comp], float)
    if len(xs) > 3:
        slope, icpt = np.polyfit(xs, ys, 1)
        ratios = np.array([comp[(i, arm)]['tok_in'] / comp[(i, arm)]['tok_out'] for i in data['qa'] | data['logs'] | data['code'] if (i, arm) in comp])
        ratio = float(np.mean(ratios))
        # robust cost per input token: total compressor wall / total input tokens (the linear fit has negative intercepts, so it is kept only in the json)
        cpt_ms = float(ys.sum() / xs.sum() * 1000)
        cpu_s = np.array([comp[(i, arm)]['cpu_s'] for i in data['qa'] | data['logs'] | data['code'] if (i, arm) in comp], float)
        saved_frac = 1 - 1 / ratio
        be_prefill_ms = cpt_ms / saved_frac if cpt_ms > 0.05 else None   # target prefill speed (ms/token) at which compression stops saving wall time
        lat[arm] = dict(compress_wall_intercept_s=float(icpt), compress_wall_slope_s_per_tok=float(slope), mean_ratio=ratio,
                        wall_ms_per_input_token=cpt_ms, cpu_s_per_1k_input_tokens=float(cpu_s.sum() / xs.sum() * 1000),
                        breakeven_target_prefill_ms_per_token=be_prefill_ms,
                        note='compression saves wall time only if the target prefills slower than breakeven_target_prefill_ms_per_token (ignores decode effects)')
out['latency_model'] = lat

_env = os.path.join(ROOT, 'raw', 'compressor_env_main_pass.json')
if not os.path.exists(_env):
    _env = os.path.join(ROOT, 'raw', 'compressor_env.json')
if os.path.exists(_env):
    _names = {'ll2': 'LLMLingua-2 (mBERT)', 'll1': 'LLMLingua v1 (GPT-2)', 'sc': 'Selective-Context-style (GPT-2)'}
    open(os.path.join(RES, 'load_costs.txt'), 'w', encoding='utf-8').write("\n".join(
        f"{_names.get(k, k)} model load: {v['load_wall_s']:.2f} s wall, {v['load_cpu_s']:.2f} s CPU, {v['rss_delta_mb']:.0f} MB resident memory added"
        for k, v in json.load(open(_env, encoding='utf-8'))['load'].items()) + "\n")
cal = os.path.join(ROOT, 'raw', 'calibration.json')
if os.path.exists(cal):
    _g = json.load(open(cal, encoding='utf-8'))['grid']
    open(os.path.join(RES, 'calibration_summary.txt'), 'w', encoding='utf-8').write("\n".join(
        f"{v['model']} requested rate {v['requested_rate']}: achieved {v['achieved_ratio']:.2f}x on the 30 dev items (" +
        ", ".join(f"{a} {b:.2f}x" for a, b in v['by_family'].items()) + ")" for v in _g.values()) + "\n")
if os.path.exists(cal):
    c = json.load(open(cal)); out['calibration_chosen'] = c['chosen']; out['compressor_load'] = c.get('load')
json.dump(out, open(os.path.join(RES, 'results.json'), 'w'), indent=1, default=float)

# ------------------------------------------------------------------ markdown tables
def f2(x, d=2):
    return f"{x:.{d}f}"


def pf(p):
    return '<0.001' if p < 0.0005 else f"{p:.3f}"


md = []
md.append("### A. Quality, compression and latency per family (local; n items per family in header)\n")
for fam in FAMS:
    n = out['n_items'][fam]
    md.append(f"**{fam}** (n={n} items, {len(ARMS)} arms, same prompts, llama3.2:3b on CPU)\n")
    md.append("| arm | answer-contains acc [95% Wilson] | Δ vs base [95% boot CI] | McNemar p | ctx ratio (cl100k) | prompt ratio (target tok) | e2e p50 s [CI] | e2e p90 s [CI] | compressor wall p50/p90 s | compressor CPU mean s |")
    md.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in [x for x in rows if x['family'] == fam]:
        d = '-' if r['arm'] == 'base' else f"{r['d_acc_vs_base']:+.3f} [{r['d_acc_ci'][0]:+.3f}, {r['d_acc_ci'][1]:+.3f}]"
        p = '-' if r['arm'] == 'base' else pf(r['mcnemar_p'])
        md.append(f"| {LABEL[r['arm']]} | {r['acc']:.3f} [{r['acc_lo']:.3f}, {r['acc_hi']:.3f}] | {d} | {p} | {f2(r['ratio_ctx_cl100k'])}x | {f2(r['ratio_prompt_target'])}x | "
                  f"{f2(r['e2e_p50'])} [{f2(r['e2e_p50_ci'][0])}, {f2(r['e2e_p50_ci'][1])}] | {f2(r['e2e_p90'])} [{f2(r['e2e_p90_ci'][0])}, {f2(r['e2e_p90_ci'][1])}] | "
                  f"{f2(r['comp_wall_p50'])}/{f2(r['comp_wall_p90'])} | {f2(r['comp_cpu_mean'])} |")
    md.append("")
md.append("### B. Pooled over the three families\n")
md.append("| arm | n | acc [95% Wilson] | Δ vs base [95% boot CI] | McNemar p |\n|---|---|---|---|---|")
for r in pool:
    d = '-' if r['arm'] == 'base' else f"{r['d_acc']:+.3f} [{r['d_ci'][0]:+.3f}, {r['d_ci'][1]:+.3f}]"
    p = '-' if r['arm'] == 'base' else pf(r['mcnemar_p'])
    md.append(f"| {LABEL[r['arm']]} | {r['n']} | {r['acc']:.3f} [{r['acc_lo']:.3f}, {r['acc_hi']:.3f}] | {d} | {p} |")
md.append("\n### C. Evidence retention in the compressed context (all items, no LLM involved)\n")
md.append("| family | arm | answer string verbatim | answer ws-insensitive | all key strings verbatim | n |\n|---|---|---|---|---|---|")
for fam in FAMS:
    for arm in ARMS[1:]:
        g = {r['metric']: r for r in ret if r['family'] == fam and r['arm'] == arm}
        md.append(f"| {fam} | {LABEL[arm]} | {g['answer_verbatim']['rate']:.2f} [{g['answer_verbatim']['lo']:.2f}, {g['answer_verbatim']['hi']:.2f}] | {g['answer_ws_insensitive']['rate']:.2f} | {g['all_keys_verbatim']['rate']:.2f} | {g['answer_verbatim']['n']} |")
md.append("\n### D. PII / sensitive-field survival (50 synthetic records; verbatim string present after compression)\n")
fl = fields + ['ALL_FIELDS_INTACT']
md.append("| arm | ctx ratio | " + " | ".join(fl) + " |\n|---|---|" + "---|" * len(fl))
for arm in ARMS[1:]:
    if arm.startswith('qaware'):
        continue
    g = {r['field']: r for r in pii if r['arm'] == arm}
    md.append(f"| {LABEL[arm]} | {g['_ratio_cl100k']['verbatim']:.2f}x | " + " | ".join(f"{g[f]['verbatim']:.2f}" + (f" (ws {g[f]['ws_insensitive']:.2f})" if abs(g[f]['ws_insensitive'] - g[f]['verbatim']) > 1e-9 else '') for f in fl) + " |")
md.append("\n### E. Failure attribution (wrong answers: evidence lost in compression vs evidence present but still wrong)\n")
md.append("| family | arm | wrong | evidence lost | evidence present | wrong where base was right |\n|---|---|---|---|---|---|")
for r in fa:
    md.append(f"| {r['family']} | {LABEL[r['arm']]} | {r['wrong']} | {r['wrong_and_evidence_lost']} | {r['wrong_but_evidence_present']} | {r['wrong_where_base_right']} |")
md.append("\n### F. Pairs of compressors that the sample cannot separate (exact McNemar p >= 0.05)\n")
md.append("| family | A | B | A-only right | B-only right | acc diff A-B | p |\n|---|---|---|---|---|---|---|")
for r in pair:
    if not r['separable']:
        md.append(f"| {r['family']} | {LABEL[r['a']]} | {LABEL[r['b']]} | {r['a_only']} | {r['b_only']} | {r['diff']:+.3f} | {r['p']:.3f} |")
md.append("\n### G. Latency model fitted on this machine (CPU target)\n")
md.append(f"Uncached prefill (baseline prompts): median {lat['prefill_ms_per_token_median']:.1f} ms/token (p10-p90 {lat['prefill_ms_per_token_p10_p90'][0]:.1f}-{lat['prefill_ms_per_token_p10_p90'][1]:.1f}); decode median {lat['decode_ms_per_token_median']:.1f} ms/token.\n")
md.append("Compression saves wall time only if the target's own prefill is slower than the break-even column (ms per prompt token); on this CPU the target prefills at the median above. Compressor cost is total wall time divided by total input tokens over all 120 test items.\n")
md.append("| arm | compressor wall, ms per input token | compressor CPU-s per 1k input tokens | mean ratio | break-even target prefill, ms/token |\n|---|---|---|---|---|")
for arm in ARMS[1:]:
    if arm in lat:
        l = lat[arm]
        be = ('%.1f' % l['breakeven_target_prefill_ms_per_token']) if l['breakeven_target_prefill_ms_per_token'] else 'none (compressor cost about 0)'
        md.append(f"| {LABEL[arm]} | {l['wall_ms_per_input_token']:.2f} | {l['cpu_s_per_1k_input_tokens']:.2f} | {l['mean_ratio']:.2f}x | {be} |")

# ---- H. structure survival (no LLM): how many structural tokens of the original survive verbatim in the compressed text
LOGK = ['svc=', 'req=', 'status=', 'latency_ms=', 'user=', 'region=']
CODEK = ['def ', 'return', 'MAX_']
struct = []
for arm in ARMS[1:]:
    rec = dict(arm=arm)
    for k in LOGK:
        o = sum(data['logs'][i]['context'].count(k) for i in data['logs'])
        c = sum(min(comp[(i, arm)]['text'].count(k), data['logs'][i]['context'].count(k)) for i in data['logs'] if (i, arm) in comp)
        rec['logs:' + k] = c / o if o else float('nan')
    for k in CODEK:
        o = sum(data['code'][i]['context'].count(k) for i in data['code'])
        c = sum(min(comp[(i, arm)]['text'].count(k), data['code'][i]['context'].count(k)) for i in data['code'] if (i, arm) in comp)
        rec['code:' + k] = c / o if o else float('nan')
    rec['code:spurious_space_underscore_space_per_file'] = float(np.mean([comp[(i, arm)]['text'].count(' _ ') for i in data['code'] if (i, arm) in comp]))
    struct.append(rec)
out['structure_survival'] = struct
md.append("\n### H. Structure survival (no LLM involved): share of the original's structural strings that appear verbatim in the compressed text\n")
cols = ['logs:' + k for k in LOGK] + ['code:' + k for k in CODEK]
md.append("| arm | " + " | ".join(f"`{c}`" for c in cols) + " | spurious ` _ ` per code file |\n|---|" + "---|" * (len(cols) + 1))
for r in struct:
    md.append(f"| {LABEL[r['arm']]} | " + " | ".join(f"{r[c]:.2f}" for c in cols) + f" | {r['code:spurious_space_underscore_space_per_file']:.1f} |")

# ---- I. structured family split by record type
kind_of = {i: data['logs'][i]['meta']['kind'] for i in data['logs']}
split = []
md.append("\n### I. Structured family split by record type (20 plain-text log items, 20 JSON items; accuracy with Wilson 95% interval)\n")
md.append("| arm | log lines (n=20) | JSON records (n=20) |\n|---|---|---|")
for arm in ARMS:
    cells = []
    for kd in ['log', 'json']:
        ids = [i for i in per_item[('logs', arm)] if kind_of[i] == kd]
        k = sum(per_item[('logs', arm)][i] for i in ids); lo, hi = wilson(k, len(ids))
        split.append(dict(arm=arm, kind=kd, n=len(ids), correct=int(k), acc=k / len(ids), lo=lo, hi=hi))
        cells.append(f"{k / len(ids):.2f} [{lo:.2f}, {hi:.2f}]")
    md.append(f"| {LABEL[arm]} | {cells[0]} | {cells[1]} |")
out['logs_by_kind'] = split

# ---- J. repeat check of the uncompressed baseline: same prompts, later session, fresh nonce
rep = []
for fam in FAMS:
    ids = [i for i in data[fam] if i in posthoc_base and (i, 'base') in runs]
    if not ids:
        continue
    same = sum(norm(posthoc_base[i]['response']) == norm(runs[(i, 'base')]['response']) for i in ids)
    same_ok = sum(correct(data[fam][i], posthoc_base[i]['response']) == correct(data[fam][i], runs[(i, 'base')]['response']) for i in ids)
    w1 = np.array([runs[(i, 'base')]['wall_s'] for i in ids]); w2 = np.array([posthoc_base[i]['wall_s'] for i in ids])
    rep.append(dict(family=fam, n=len(ids), identical_responses=int(same), same_correctness=int(same_ok), main_llm_p50=pct(w1, 50), repeat_llm_p50=pct(w2, 50),
                    repeat_over_main_median=float(np.median(w2) / np.median(w1))))
out['baseline_repeat'] = rep
if rep:
    md.append("\n### J. Repeat of the uncompressed baseline in the later (post-hoc) session: same prompts, new nonce, temperature 0\n")
    md.append("| family | items | identical responses | same right/wrong verdict | LLM wall p50, main run s | LLM wall p50, repeat s | repeat / main |\n|---|---|---|---|---|---|---|")
    for r in rep:
        md.append(f"| {r['family']} | {r['n']} | {r['identical_responses']} | {r['same_correctness']} | {f2(r['main_llm_p50'])} | {f2(r['repeat_llm_p50'])} | {f2(r['repeat_over_main_median'])}x |")
json.dump(out, open(os.path.join(RES, 'results.json'), 'w'), indent=1, default=float)
open(os.path.join(RES, 'results.md'), 'w', encoding='utf-8').write("\n".join(md) + "\n")
_ex = []
for _iid, _fam in [('pii-000', 'pii'), ('logs-002', 'logs'), ('code-000', 'code')]:
    _ex.append(f"=== {_iid} original (first 400 characters)\n{data[_fam][_iid]['context'][:400]}")
    for _arm in ARMS[1:]:
        if (_iid, _arm) in comp:
            _ex.append(f"--- {_iid}, {LABEL[_arm]} (first 400 characters)\n{comp[(_iid, _arm)]['text'][:400]}")
open(os.path.join(RES, 'examples.txt'), 'w', encoding='utf-8').write("\n\n".join(_ex) + "\n")
with open(os.path.join(RES, 'rows.csv'), 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=sorted({k for r in rows for k in r})); w.writeheader(); [w.writerow(r) for r in rows]
print("\n".join(md))
