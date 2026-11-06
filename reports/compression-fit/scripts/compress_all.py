"""compress_all.py --calibrate | --run [--limit N]

Run with the gateway's .venv-compression interpreter and the pinned overlay on PYTHONPATH (see REPORT.md, reproduce section):
  PYTHONPATH=reports/compression-fit/.pylib  HF_HUB_OFFLINE=1  .venv-compression/Scripts/python.exe reports/compression-fit/scripts/compress_all.py --calibrate

Arms (all compress the CONTEXT only; instruction and question are never compressed):
  ll2_2x / ll2_3x : LLMLingua-2 (microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank), question-agnostic
  ll1_2x          : LLMLingua v1 with GPT-2 small as the scoring LM (llmlingua 0.2.2, iterative_size=50), question-agnostic
  sc_2x           : Selective-Context-style: GPT-2 self-information per whitespace word, drop the lowest-information words
                    (own re-implementation of the paper's filtering step; no spaCy phrase merging) -- NOT the reference code
  rand_2x         : control, drop a random 50% of whitespace words
  qaware_2x       : control, query-aware TF-IDF block selection to ~50% of the words (stand-in for question-aware selection; not CPC)
Requested rates for ll2/ll1 are calibrated on dev items so that the achieved cl100k-token ratio is ~2x (or ~3x).
"""
import os, sys, json, time, re, random, argparse, platform
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
import numpy as np, psutil, torch, tiktoken, transformers
from llmlingua import PromptCompressor

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
GPT2 = r'C:\Users\P7120489\.cache\huggingface\hub\models--openai-community--gpt2\snapshots\607a30d783dfa663caf39e06633721c8d4cfcd7e'
LL2 = 'microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank'
ENC = tiktoken.encoding_for_model('gpt-3.5-turbo')   # cl100k_base; same counter llmlingua uses for its own ratios
ntok = lambda s: len(ENC.encode(s))
proc = psutil.Process()


def load_jsonl(p):
    return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]


def timed(fn, *a, **k):
    t0, c0 = time.perf_counter(), time.process_time()
    out = fn(*a, **k)
    return out, time.perf_counter() - t0, time.process_time() - c0


class SelCtx:
    """Selective-Context-style filter (Li et al. 2023 idea): self-information I(x)=-log p(x|x<i) from a small causal LM,
    aggregated per whitespace word, keep the highest-information words. Word units instead of spaCy noun phrases."""
    def __init__(self, path):
        from transformers import AutoTokenizer, AutoModelForCausalLM
        self.tok = AutoTokenizer.from_pretrained(path)
        self.m = AutoModelForCausalLM.from_pretrained(path).eval()

    def word_info(self, text):
        words = [(m.start(), m.end()) for m in re.finditer(r'\S+', text)]
        enc = self.tok(text, return_offsets_mapping=True, add_special_tokens=False)
        ids, offs = enc['input_ids'], enc['offset_mapping']
        win = 1000
        si = np.zeros(len(ids))
        for a in range(0, len(ids), win):            # contexts here are < 1000 GPT-2 tokens; the loop is only a safety net
            chunk = [self.tok.bos_token_id] + ids[a:a + win]
            with torch.no_grad():
                lg = self.m(torch.tensor([chunk])).logits[0, :-1].float()
            lp = torch.log_softmax(lg, -1)
            tgt = torch.tensor(chunk[1:])
            si[a:a + len(tgt)] = (-lp[torch.arange(len(tgt)), tgt]).numpy()
        wi = np.zeros(len(words))
        j = 0
        for (s, e), v in zip(offs, si):
            while j < len(words) - 1 and s >= words[j][1]:
                j += 1
            wi[j] += v
        return words, wi

    def compress(self, text, keep):
        words, wi = self.word_info(text)
        k = max(1, int(round(keep * len(words))))
        top = sorted(np.argsort(-wi, kind='stable')[:k])
        return ' '.join(text[words[i][0]:words[i][1]] for i in top)


def rand_drop(text, keep, seed):
    words = text.split()
    k = max(1, int(round(keep * len(words))))
    rng = random.Random(seed)
    idx = sorted(rng.sample(range(len(words)), k))
    return ' '.join(words[i] for i in idx)


def tfidf_select(ctx, question, keep, family):
    from sklearn.feature_extraction.text import TfidfVectorizer
    sep = '\n' if family == 'logs' else '\n\n'
    units = [u for u in ctx.split(sep) if u.strip()]
    vec = TfidfVectorizer(token_pattern=r"[A-Za-z0-9_\-\.]+", lowercase=True).fit(units + [question])
    U, Q = vec.transform(units), vec.transform([question])
    sims = (U @ Q.T).toarray().ravel()
    total = sum(len(u.split()) for u in units)
    budget = keep * total
    chosen, used = [], 0
    for i in np.argsort(-sims, kind='stable'):
        w = len(units[i].split())
        if not chosen or used + w <= budget * 1.15:
            chosen.append(int(i)); used += w
        if used >= budget:
            break
    return sep.join(units[i] for i in sorted(chosen))


class Bank:
    """Holds loaded compressors and exposes compress(arm, item) -> text."""
    def __init__(self, cfg):
        self.cfg = cfg
        self.load = {}
        for name, loader in [('ll2', lambda: PromptCompressor(model_name=LL2, use_llmlingua2=True, device_map='cpu')),
                             ('ll1', lambda: PromptCompressor(model_name=GPT2, device_map='cpu')),
                             ('sc', lambda: SelCtx(GPT2))]:
            r0 = proc.memory_info().rss
            t0, c0 = time.perf_counter(), time.process_time()
            setattr(self, name, loader())
            self.load[name] = dict(load_wall_s=time.perf_counter() - t0, load_cpu_s=time.process_time() - c0,
                                   rss_delta_mb=(proc.memory_info().rss - r0) / 2**20)
        # warm-up so that first-call overhead does not land in the timings
        w = "In 2011 the company opened an office in Osaka, followed by Lyon in 2014. Revenue reached $48.2 million in fiscal 2021."
        self.ll2.compress_prompt_llmlingua2(w, rate=0.5)
        self.ll1.compress_prompt([w], instruction='', question='', rate=0.3, iterative_size=50)
        self.sc.compress(w, 0.5)

    def compress(self, arm, item, cfg=None):
        cfg = cfg or self.cfg
        ctx, fam = item['context'], item['family']
        if arm.startswith('ll2g'):   # POST-HOC arm: the gateway's literal non_sensitive route (PROMPT_COMPRESSION_RATE_NON_SENSITIVE=0.6, force_reserve_digit=True)
            return self.ll2.compress_prompt_llmlingua2(ctx, rate=cfg.get(arm, 0.6), force_reserve_digit=True)['compressed_prompt'].strip()
        if arm.startswith('ll2d'):   # POST-HOC arm: LLMLingua-2 with force_reserve_digit=True, as the gateway's non_sensitive route sets it
            return self.ll2.compress_prompt_llmlingua2(ctx, rate=cfg[arm], force_reserve_digit=True)['compressed_prompt'].strip()
        if arm.startswith('ll2'):
            return self.ll2.compress_prompt_llmlingua2(ctx, rate=cfg[arm])['compressed_prompt'].strip()
        if arm.startswith('ll1'):
            return self.ll1.compress_prompt([ctx], instruction='', question='', rate=cfg[arm], iterative_size=50)['compressed_prompt'].strip()
        if arm.startswith('sc'):
            return self.sc.compress(ctx, cfg.get(arm, 0.5))
        if arm.startswith('rand'):
            return rand_drop(ctx, cfg.get(arm, 0.5), f"20261105-{item['id']}")
        if arm.startswith('qaware'):
            return tfidf_select(ctx, item['question'], cfg.get(arm, 0.5), fam)
        raise ValueError(arm)


def env_info():
    import llmlingua, sklearn
    return dict(python=sys.version.split()[0], platform=platform.platform(), processor=platform.processor(),
                logical_cpus=os.cpu_count(), ram_gb=round(psutil.virtual_memory().total / 2**30, 1),
                torch=torch.__version__, torch_threads=torch.get_num_threads(), transformers=transformers.__version__,
                llmlingua=getattr(llmlingua, '__version__', 'unknown'), sklearn=sklearn.__version__, numpy=np.__version__,
                tiktoken=tiktoken.__version__, ll2_model=LL2, gpt2_path=GPT2)


def calibrate(bank, only=None):
    """Calibrate every method's requested rate on DEV items so the achieved cl100k-token ratio is ~2x (ll2 also ~3x).
    --only sc,rand,qaware re-calibrates just those and merges into the existing raw/calibration.json (ll2/ll1 were done first;
    sc/rand/qaware were added after a pilot showed a nominal 50% word keep gives unequal token ratios across methods)."""
    dev = []
    for fam in ['qa', 'logs', 'code']:
        dev += load_jsonl(os.path.join(ROOT, 'data', f'dev_{fam}.jsonl'))
    grids = {'ll2': [0.6, 0.5, 0.4, 0.33, 0.28, 0.22, 0.15], 'll2d': [0.5, 0.4, 0.33, 0.28, 0.22], 'll1': [0.5, 0.4, 0.3, 0.25, 0.2, 0.15, 0.1],
             'sc': [0.5, 0.45, 0.4, 0.35, 0.3], 'rand': [0.55, 0.5, 0.45, 0.4], 'qaware': [0.5, 0.45, 0.4, 0.35, 0.3]}
    calp = os.path.join(ROOT, 'raw', 'calibration.json')
    out = json.load(open(calp)) if (only and os.path.exists(calp)) else {'dev_items': len(dev), 'grid': {}}
    if only:
        grids = {k: v for k, v in grids.items() if k in only}
    for m, rates in grids.items():
        for r in rates:
            cfg = {f'{m}_x': r}
            tin = tout = 0; wall = 0.0
            per = {}
            for it in dev:
                t0 = time.perf_counter()
                txt = bank.compress(f'{m}_x', it, cfg)
                wall += time.perf_counter() - t0
                a, b = ntok(it['context']), ntok(txt)
                tin += a; tout += b
                p = per.setdefault(it['family'], [0, 0]); p[0] += a; p[1] += b
            out['grid'][f'{m}@{r}'] = dict(model=m, requested_rate=r, achieved_ratio=tin / tout, mean_wall_s=wall / len(dev),
                                           by_family={k: v[0] / v[1] for k, v in per.items()})
            print(f"{m} rate={r}: achieved {tin / tout:.2f}x  mean {wall / len(dev):.2f}s", flush=True)
    pick = lambda m, tgt: min((v for v in out['grid'].values() if v['model'] == m), key=lambda v: abs(v['achieved_ratio'] - tgt))
    chosen = out.get('chosen', {})
    for m, key, tgt in [('ll2', 'll2_2x', 2.0), ('ll2', 'll2_3x', 3.0), ('ll2d', 'll2d_2x', 2.0), ('ll1', 'll1_2x', 2.0), ('sc', 'sc_2x', 2.0), ('rand', 'rand_2x', 2.0), ('qaware', 'qaware_2x', 2.0)]:
        if any(v['model'] == m for v in out['grid'].values()) and (not only or m in only):
            chosen[key] = pick(m, tgt)['requested_rate']
    out['chosen'] = chosen
    out['env'] = env_info(); out['load'] = bank.load
    json.dump(out, open(calp, 'w'), indent=1)
    print('chosen', out['chosen'])


def run(bank, limit):
    cal = json.load(open(os.path.join(ROOT, 'raw', 'calibration.json')))
    cfg = cal['chosen']
    cfg.setdefault('ll2g_gw', 0.6)
    arms = ['ll2_2x', 'll2_3x', 'll1_2x', 'sc_2x', 'rand_2x', 'qaware_2x', 'll2d_2x', 'll2g_gw']   # ll2d_2x and ll2g_gw were added after the main pass (post-hoc)
    path = os.path.join(ROOT, 'raw', 'compressed.jsonl')
    done = set()
    if os.path.exists(path):
        for r in load_jsonl(path):
            done.add((r['item_id'], r['arm']))
    f = open(path, 'a', encoding='utf-8')
    for fam in ['qa', 'logs', 'code', 'pii']:
        items = load_jsonl(os.path.join(ROOT, 'data', f'{fam}.jsonl'))[:limit]
        for it in items:
            for arm in arms:
                if fam == 'pii' and arm.startswith('qaware'):
                    continue
                if (it['id'], arm) in done:
                    continue
                txt, wall, cpu = timed(bank.compress, arm, it, cfg)
                rec = dict(item_id=it['id'], family=fam, arm=arm, requested_rate=cfg.get(arm, 0.5), text=txt, wall_s=wall, cpu_s=cpu,
                           tok_in=ntok(it['context']), tok_out=ntok(txt), words_in=len(it['context'].split()), words_out=len(txt.split()))
                f.write(json.dumps(rec, ensure_ascii=False) + "\n"); f.flush()
        print('done family', fam, flush=True)
    json.dump(dict(env=env_info(), load=bank.load, chosen=cfg), open(os.path.join(ROOT, 'raw', 'compressor_env.json'), 'w'), indent=1)


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--calibrate', action='store_true'); ap.add_argument('--run', action='store_true'); ap.add_argument('--limit', type=int, default=None)
    ap.add_argument('--only', default=None, help='comma list of methods to (re)calibrate: ll2,ll1,sc,rand,qaware')
    a = ap.parse_args()
    print('transformers', transformers.__version__, 'torch threads', torch.get_num_threads(), flush=True)
    bank = Bank({})
    print('loaded', json.dumps(bank.load), flush=True)
    if a.calibrate: calibrate(bank, a.only.split(',') if a.only else None)
    if a.run: run(bank, a.limit)
