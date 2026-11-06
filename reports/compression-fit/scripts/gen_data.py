"""gen_data.py  -- deterministic synthetic benchmark items for the local compression check.

Writes data/{qa,logs,code,pii}.jsonl (test, SEED_TEST) and data/dev_{qa,logs,code}.jsonl (dev, SEED_DEV; used only to
calibrate each compressor's requested rate to a common achieved ratio -- never to score methods).

Why synthetic: every answer is a rare string (invented names, random hex ids, random identifiers), so the target model cannot
answer from prior knowledge and every item has an exact reference answer. Cost: templated text is more regular than real
documents, so absolute accuracies are NOT comparable to the papers' numbers; only the within-run comparison between arms is.

Item schema: {id, family, context, question, answers:[acceptable substrings], key_strings:[strings that must survive
compression for the item to be answerable], meta:{...}}
"""
import json, random, os, string, sys

SEED_TEST, SEED_DEV = 20261105, 777
HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, '..', 'data')

SYL_A = ['Vel', 'Kes', 'Mor', 'Tal', 'Zen', 'Bri', 'Cal', 'Dor', 'Fen', 'Gal', 'Hal', 'Jor', 'Lum', 'Nor', 'Pry', 'Quo', 'Ras', 'Sol', 'Tur', 'Wex']
SYL_B = ['trix', 'dyne', 'ford', 'vance', 'line', 'works', 'tek', 'nova', 'mark', 'core', 'wave', 'gate', 'spire', 'forge']
FIRST = ['Marta', 'Jonas', 'Ilse', 'Tomas', 'Priya', 'Oskar', 'Lena', 'Mateo', 'Yara', 'Felix', 'Nadia', 'Bruno', 'Elif', 'Rurik', 'Sana', 'Dmitri', 'Inge', 'Kofi', 'Alma', 'Hugo']
LAST = ['Quillfeather', 'Brandt', 'Okonkwo', 'Varga', 'Lindqvist', 'Moreau', 'Haldane', 'Petrov', 'Castellan', 'Ibsen', 'Marlowe', 'Zielinski', 'Abernathy', 'Tanaka', 'Roux', 'Delacroix', 'Voss', 'Nakamura', 'Fairweather', 'Grimaldi']
CITIES = ['Osaka', 'Lyon', 'Porto', 'Gdansk', 'Leeds', 'Turin', 'Tampere', 'Ghent', 'Brno', 'Cork', 'Malmo', 'Seville', 'Utrecht', 'Bergen', 'Graz', 'Split']
PRODUCTS = ['precision bearings', 'marine sensors', 'solar inverters', 'hydraulic valves', 'cold-chain loggers', 'rail couplings', 'turbine blades', 'optical encoders']
MONTHS = ['January', 'March', 'May', 'July', 'September', 'November']
FILLER = [
    "The global market for industrial components has been shaped by supply chain disruptions, changing regulations and rising demand for sustainable materials across many sectors.",
    "Industry observers often note that mid-sized manufacturers adapt faster to new standards than their larger competitors, mainly because decisions pass through fewer layers of management.",
    "Trade associations in the region have repeatedly called for clearer export rules, arguing that unpredictable paperwork adds weeks to delivery times and discourages smaller suppliers.",
    "Analysts described the cost discipline as unusual for a business of this size and age, pointing to long-term contracts with suppliers and a conservative approach to borrowing.",
    "Recruitment has been a persistent challenge, with employers competing for engineers who combine mechanical training with experience in data analysis and automation tools.",
    "Environmental reporting requirements have expanded in recent years, and several firms now publish detailed accounts of energy use, water consumption and waste handling at each site.",
    "Customers frequently cite reliability and after-sales support as the deciding factors when choosing between suppliers whose prices differ only by a few percentage points.",
    "A number of universities have launched joint programmes with local employers, offering placements that allow students to work on real production problems during their studies.",
]


def mkname(r):
    return r.choice(SYL_A) + r.choice(SYL_B)


def mkperson(r):
    return f"{r.choice(FIRST)} {r.choice(LAST)}"


def distinct_years(r, n, lo=1988, hi=2024):
    return r.sample(range(lo, hi), n)


# ---------------------------------------------------------------- family 1: long-document QA (prose)
def make_qa(r, i):
    co = mkname(r)
    founders = r.sample(FIRST, 2)
    surnames = r.sample(LAST, 4)
    p1, p2, ceo, prev = f"{founders[0]} {surnames[0]}", f"{founders[1]} {surnames[1]}", f"{r.choice(FIRST)} {surnames[2]}", f"{r.choice(FIRST)} {surnames[3]}"
    cities = r.sample(CITIES, 4)
    yrs = distinct_years(r, 8)
    founded, y1, y2, y3, ceo_y, rev_y, launch_y, tenure = yrs[0], yrs[1], yrs[2], yrs[3], yrs[4], yrs[5], yrs[6], r.randint(6, 19)
    rev, cost, pct = round(r.uniform(12, 96), 1), round(r.uniform(8, 70), 1), r.randint(3, 29)
    product = r.choice(PRODUCTS)
    pname = f"{mkname(r)}-{r.randint(100, 999)}"
    price, units, days = r.randint(120, 940), r.randint(1100, 9800), r.randint(11, 60)
    employees = r.randint(8, 59) * 100
    facts = {
        'founding': [f"{co} was founded in {founded} by {p1} and {p2} in {cities[0]}, initially producing {product} for regional customers.",
                     f"The story of {co} began in {cities[0]} in {founded}, when {p1} and {p2} set up a small workshop making {product}."],
        'offices': [f"In {y1} the company opened an office in {cities[1]}, followed by {cities[2]} in {y2} and {cities[3]} in {y3}, and it now employs about {employees} people.",
                    f"Expansion came in stages: an office in {cities[1]} in {y1}, one in {cities[2]} in {y2}, and one in {cities[3]} in {y3}; headcount is now roughly {employees}."],
        'leadership': [f"{ceo} became chief executive in {ceo_y}, succeeding {prev}, who had led the company for {tenure} years.",
                       f"After {tenure} years under {prev}, leadership passed to {ceo} in {ceo_y}, who remains chief executive."],
        'financials': [f"Revenue reached ${rev} million in fiscal {rev_y}, up {pct} percent from the previous year, while operating costs totalled ${cost} million.",
                       f"For fiscal {rev_y} {co} reported revenue of ${rev} million, a rise of {pct} percent, against operating costs of ${cost} million."],
        'product': [f"The {pname} line launched in {r.choice(MONTHS)} {launch_y} at a price of ${price}, and the first batch sold {units} units in {days} days.",
                    f"{pname}, the flagship {product} model, went on sale in {launch_y} for ${price}; {units} units were sold within {days} days."],
    }
    qtypes = [
        ('offices', f"In which year did {co} open its office in {cities[2]}?", [str(y2)], [cities[2], str(y2)]),
        ('offices', f"In which year did {co} open its office in {cities[3]}?", [str(y3)], [cities[3], str(y3)]),
        ('leadership', f"Who was chief executive of {co} before {ceo}?", [prev.split()[1]], [prev]),
        ('financials', f"What was the revenue of {co} in fiscal {rev_y}, in millions of dollars?", [str(rev)], [str(rev)]),
        ('product', f"How many units of {pname} were sold in the first batch?", [str(units)], [str(units)]),
        ('founding', f"Who founded {co} together with {p1}?", [p2.split()[1]], [p2]),
        ('product', f"What was the launch price of {pname}, in dollars?", [str(price)], [str(price)]),
        ('financials', f"By how many percent did the revenue of {co} rise in fiscal {rev_y}?", [str(pct)], [str(pct)]),
    ]
    topic, q, ans, keys = r.choice(qtypes)
    paras = [r.choice(v) for v in facts.values()]
    paras += r.sample(FILLER, 4)
    r.shuffle(paras)
    return dict(id=f"qa-{i:03d}", family='qa', context="\n\n".join(paras), question=q, answers=ans, key_strings=keys, meta=dict(topic=topic, company=co))


# ---------------------------------------------------------------- family 2: structured logs / JSON
SERVICES = ['billing-api', 'inventory-sync', 'auth-gateway', 'search-index', 'email-relay', 'report-builder', 'cart-service', 'geo-lookup']
LEVELS = ['INFO', 'INFO', 'INFO', 'WARN', 'ERROR']
STATUSES = [200, 200, 201, 204, 301, 400, 404, 409, 500, 502, 503]
REGIONS = ['eu-west-1', 'us-east-2', 'ap-south-1', 'eu-central-1']


def hex6(r, used):
    while True:
        h = ''.join(r.choice('0123456789abcdef') for _ in range(6))
        if h not in used:
            used.add(h)
            return h


def make_logs(r, i):
    if i % 2 == 0:  # log lines
        used = set()
        lines, recs = [], []
        h, m, s = r.randint(0, 22), r.randint(0, 59), r.randint(0, 59)
        for k in range(12):
            s += r.randint(1, 40)
            m += s // 60; s %= 60; h += m // 60; m %= 60
            rec = dict(ts=f"2026-03-14T{h:02d}:{m:02d}:{s:02d}Z", lvl=r.choice(LEVELS), svc=r.choice(SERVICES), req=f"req-{hex6(r, used)}",
                       status=r.choice(STATUSES), lat=r.randint(12, 2900), user=f"u-{r.randint(10000, 99999)}", reg=r.choice(REGIONS))
            recs.append(rec)
            lines.append(f"{rec['ts']} {rec['lvl']:<5} svc={rec['svc']} req={rec['req']} status={rec['status']} latency_ms={rec['lat']} user={rec['user']} region={rec['reg']}")
        t = r.choice(recs)
        # make the asked value unique among the lines so containment is unambiguous
        others = [x for x in recs if x is not t]
        qs = [("status code", str(t['status']), 'status', all(x['status'] != t['status'] for x in others)),
              ("latency_ms value", str(t['lat']), 'lat', True),
              ("service name", t['svc'], 'svc', all(x['svc'] != t['svc'] for x in others)),
              ("user id", t['user'], 'user', True)]
        qs = [q for q in qs if q[3]]
        name, ans, _, _ = r.choice(qs)
        q = f"What was the {name} of request {t['req']}?"
        return dict(id=f"logs-{i:03d}", family='logs', context="\n".join(lines), question=q, answers=[ans], key_strings=[t['req'], ans], meta=dict(kind='log', asked=name))
    # json records
    used = set()
    objs = []
    for k in range(8):
        objs.append(dict(order_id=f"ORD-{r.randint(1000, 9999)}", customer=f"c-{r.randint(1000, 9999)}", items=r.randint(1, 9), total=round(r.uniform(9, 990), 2),
                         currency=r.choice(['EUR', 'GBP', 'USD']), status=r.choice(['shipped', 'pending', 'returned', 'delivered']), carrier=r.choice(['DHL', 'UPS', 'FedEx', 'DPD'])))
    ids = [o['order_id'] for o in objs]
    if len(set(ids)) < len(ids):
        return make_logs(r, i)
    t = r.choice(objs)
    ctx = "[\n" + ",\n".join("  " + json.dumps(o) for o in objs) + "\n]"
    fld, nm = r.choice([('total', 'total'), ('customer', 'customer id'), ('carrier', 'carrier')])
    ans = json.dumps(t[fld]) if fld == 'total' else str(t[fld])   # exactly as printed in the JSON context
    q = f"What is the {nm} of order {t['order_id']}?"
    return dict(id=f"logs-{i:03d}", family='logs', context=ctx, question=q, answers=[ans], key_strings=[t['order_id'], ans], meta=dict(kind='json', asked=nm))


# ---------------------------------------------------------------- family 3: code
VERBS = ['sync', 'load', 'merge', 'filter', 'encode', 'build', 'check', 'flush', 'parse', 'route']
NOUNS = ['orders', 'tokens', 'records', 'events', 'shards', 'quotas', 'batches', 'frames']


def ident(r, used):
    while True:
        n = f"{r.choice(VERBS)}_{r.choice(NOUNS)}_{''.join(r.choice(string.ascii_lowercase) for _ in range(2))}"
        if n not in used:
            used.add(n)
            return n


def make_code(r, i):
    used = set()
    n = 7
    fn = [ident(r, used) for _ in range(n)]
    consts = [(f"MAX_{r.choice(['BATCH', 'RETRY', 'WINDOW', 'LIMIT'])}_{''.join(r.choice(string.ascii_uppercase) for _ in range(2))}", r.randint(20, 990)) for _ in range(3)]
    while len({c[0] for c in consts}) < 3:
        consts = [(f"MAX_{r.choice(['BATCH', 'RETRY', 'WINDOW', 'LIMIT'])}_{''.join(r.choice(string.ascii_uppercase) for _ in range(2))}", r.randint(20, 990)) for _ in range(3)]
    params = ['retry_limit', 'page_size', 'timeout_s', 'max_items', 'backoff_ms', 'chunk_len']
    # call graph: each function k>0 is called by exactly one earlier function
    callers = {k: r.randrange(0, k) for k in range(1, n)}
    defaults = {}
    out = ['import logging', '', 'log = logging.getLogger(__name__)', '']
    for c, v in consts:
        out.append(f"{c} = {v}")
    out.append('')
    docs = ['Synchronise pending entries.', 'Load the next window.', 'Merge partial results.', 'Drop invalid items.', 'Encode a payload for transport.', 'Build the request body.', 'Check limits before sending.']
    for k in range(n):
        p = r.choice(params)
        d = r.randint(2, 480)
        defaults[k] = (p, d)
        body = [f"    \"\"\"{docs[k]}\"\"\"", f"    limit = min({p}, {r.choice(consts)[0]})"]
        callees = [fn[j] for j, c in callers.items() if c == k]
        for ce in callees:
            body.append(f"    result = {ce}(data, {p}={p})" if False else f"    result = {ce}(data)")
        if not callees:
            body.append("    result = [x for x in data if x]")
        body.append(f"    log.info(\"%s done\", \"{fn[k]}\")")
        body.append("    return result[:limit]")
        out += [f"def {fn[k]}(data, {p}={d}):"] + body + ['']
    k = r.randrange(0, n)
    qk = r.choice(['default', 'const', 'caller'])
    if qk == 'caller' and n > 1:
        callee = r.randrange(1, n)
        q, ans, keys = f"Which function calls `{fn[callee]}`?", [fn[callers[callee]]], [fn[callee], fn[callers[callee]]]
    elif qk == 'const':
        c, v = r.choice(consts)
        q, ans, keys = f"What is the value of the constant `{c}`?", [str(v)], [c, str(v)]
    else:
        p, d = defaults[k]
        q, ans, keys = f"In the function `{fn[k]}`, what is the default value of the parameter `{p}`?", [str(d)], [fn[k], p, str(d)]
    return dict(id=f"code-{i:03d}", family='code', context="\n".join(out).rstrip(), question=q, answers=ans, key_strings=keys, meta=dict(qtype=qk))


# ---------------------------------------------------------------- family 4: PII retention (no LLM needed)
STREETS = ['Alder Way', 'Mill Lane', 'Kestrel Road', 'Harbour Street', 'Birch Court', 'Station Approach']
DIAG = ['type 2 diabetes', 'chronic migraine', 'asthma', 'hypertension', 'an anxiety disorder', 'a torn meniscus']


def make_pii(r, i):
    fn, ln = r.choice(FIRST), r.choice(LAST)
    name = f"{fn} {ln}"
    email = f"{fn.lower()}.{ln.lower()}{r.randint(1, 99)}@{r.choice(['example.org', 'mailtest.net', 'sample.co'])}"
    phone = f"+44 7{r.randint(100, 999)} {r.randint(100000, 999999)}"
    nino = ''.join(r.choice('ABCEGHJKLMNPRSTWXYZ') for _ in range(2)) + f" {r.randint(10, 99)} {r.randint(10, 99)} {r.randint(10, 99)} " + r.choice('ABCD')
    iban = f"GB{r.randint(10, 99)}TEST{r.randint(10**13, 10**14 - 1)}"
    dob = f"{r.randint(1, 28):02d}/{r.randint(1, 12):02d}/{r.randint(1950, 2004)}"
    addr = f"{r.randint(1, 240)} {r.choice(STREETS)}, {r.choice(CITIES)}"
    diag = r.choice(DIAG)
    ref = f"CASE-{r.randint(100000, 999999)}"
    text = (f"Case note {ref}. The caller, {name}, born {dob}, contacted support about a delayed reimbursement. "
            f"They confirmed their address as {addr} and asked that updates be sent to {email} or by phone on {phone}. "
            f"For identity verification the caller gave national insurance number {nino}. Payment should go to account {iban}. "
            f"During the call they mentioned being treated for {diag}, which is why the claim was marked as urgent. "
            f"The agent explained the review process, apologised for the wait, and promised a written reply within five working days.")
    return dict(id=f"pii-{i:03d}", family='pii', context=text, question='', answers=[], key_strings=[name, dob, addr, email, phone, nino, iban, diag, ref],
                meta=dict(fields=['name', 'dob', 'address', 'email', 'phone', 'national_id', 'iban', 'diagnosis', 'case_ref']))


def write(fn, rows):
    os.makedirs(DATA, exist_ok=True)
    with open(os.path.join(DATA, fn), 'w', encoding='utf-8') as f:
        for x in rows:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")


if __name__ == '__main__':
    n_test = {'qa': 40, 'logs': 40, 'code': 40, 'pii': 50}
    for fam, mk in [('qa', make_qa), ('logs', make_logs), ('code', make_code), ('pii', make_pii)]:
        r = random.Random(f"{SEED_TEST}-{fam}")
        write(f"{fam}.jsonl", [mk(r, i) for i in range(n_test[fam])])
        if fam != 'pii':
            r = random.Random(f"{SEED_DEV}-{fam}")
            write(f"dev_{fam}.jsonl", [mk(r, i) for i in range(10)])
    print('written to', os.path.abspath(DATA))
