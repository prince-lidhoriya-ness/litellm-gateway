"""run_llm.py [--limit N] [--families qa,logs,code] [--arms base,ll2_2x,...]

Sends the SAME prompts (differing only in the compressed context) to the SAME local target model, one request at a time.
Target: Ollama llama3.2:3b (Q4_K_M) on CPU, temperature 0, seed 7, num_predict 24, num_ctx 4096.
 - A unique nonce is the first line of every prompt so that llama.cpp's prefix/prompt cache cannot reuse work across requests
   (the same nonce length for every arm keeps the overhead equal).
 - Arms are shuffled per item (seeded) and families are interleaved round-robin, to spread thermal/background drift.
 - Resumable: (item_id, arm) pairs already in raw/llm_runs.jsonl are skipped.
Compression is done beforehand by compress_all.py (raw/compressed.jsonl); its wall time is added to the arm's latency in analyze.py.
"""
import os, sys, json, time, random, uuid, argparse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..'))
URL = os.environ.get('OLLAMA_URL', 'http://localhost:11434') + '/api/chat'
MODEL = os.environ.get('TARGET_MODEL', 'llama3.2:3b')
INSTR = "Answer the question using only the document below. Reply with only the answer value (a name, number or identifier), nothing else."
OPTIONS = dict(temperature=0, seed=7, num_predict=24, num_ctx=4096)


def load_jsonl(p):
    return [json.loads(l) for l in open(p, encoding='utf-8') if l.strip()]


def build(ctx, question, nonce):
    return f"[req:{nonce}]\n{INSTR}\n\nDocument:\n{ctx}\n\nQuestion: {question}\nAnswer:"


def call(prompt):
    body = json.dumps(dict(model=MODEL, messages=[dict(role='user', content=prompt)], stream=False, options=OPTIONS, keep_alive='120m')).encode()
    req = urllib.request.Request(URL, data=body, headers={'Content-Type': 'application/json'})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=900) as r:
        j = json.loads(r.read())
    return j, time.perf_counter() - t0


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=None)
    ap.add_argument('--families', default='qa,logs,code')
    ap.add_argument('--arms', default='base,ll2_2x,ll2_3x,ll1_2x,sc_2x,rand_2x,qaware_2x')
    ap.add_argument('--out', default=os.path.join(ROOT, 'raw', 'llm_runs.jsonl'))
    a = ap.parse_args()
    fams, arms = a.families.split(','), a.arms.split(',')
    comp = {}
    for r in load_jsonl(os.path.join(ROOT, 'raw', 'compressed.jsonl')):
        comp[(r['item_id'], r['arm'])] = r['text']
    items = {f: load_jsonl(os.path.join(ROOT, 'data', f'{f}.jsonl'))[:a.limit] for f in fams}
    done = set()
    if os.path.exists(a.out):
        done = {(r['item_id'], r['arm']) for r in load_jsonl(a.out)}
    # warm-up (model load + first-request effects), not recorded
    for k in range(2):
        call(build("The sky is blue. Grass is green.", "What colour is grass?", uuid.uuid4().hex[:8]))
    out = open(a.out, 'a', encoding='utf-8')
    n = max(len(v) for v in items.values())
    total = sum(len(v) for v in items.values()) * len(arms)
    k = len(done)
    t_start = time.time()
    for i in range(n):
        for f in fams:
            if i >= len(items[f]):
                continue
            it = items[f][i]
            order = list(arms)
            random.Random(f"order-{it['id']}").shuffle(order)
            for pos, arm in enumerate(order):
                if (it['id'], arm) in done:
                    continue
                ctx = it['context'] if arm == 'base' else comp[(it['id'], arm)]
                nonce = uuid.uuid4().hex[:8]
                j, wall = call(build(ctx, it['question'], nonce))
                rec = dict(item_id=it['id'], family=f, arm=arm, order_pos=pos, nonce=nonce, wall_s=wall, response=j['message']['content'],
                           prompt_tokens=j.get('prompt_eval_count'), gen_tokens=j.get('eval_count'), load_ns=j.get('load_duration'),
                           prompt_eval_ns=j.get('prompt_eval_duration'), eval_ns=j.get('eval_duration'), total_ns=j.get('total_duration'),
                           ts=time.strftime('%Y-%m-%dT%H:%M:%S'))
                out.write(json.dumps(rec, ensure_ascii=False) + "\n"); out.flush()
                k += 1
            el = time.time() - t_start
            print(f"item {i + 1}/{n} {f}: {k}/{total} requests, elapsed {el / 60:.1f} min", flush=True)
