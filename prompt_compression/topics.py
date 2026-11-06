"""Sensitive-topic lexicon: deterministic check for private health, money, legal and identity matters.

Why this exists: the zero-shot NLI model (typeform/distilbert-base-uncased-mnli) cannot tell sensitive text from ordinary
text. Its P("sensitive") over the four candidate labels is 0.38-0.67 for real sensitive prompts and 0.35-0.57 for chat
filler, code questions and company prose (eval/results/sensitivity_*.md and reports/playground-ab/), so every threshold
either misses sensitive text or flags most ordinary prompts. What the sensitive prompts that rules.py misses have in
common is their topic: a diagnosis or a medication, someone's salary or debt, a settlement or an investigation, a home
address or a security answer. Those are words, so they are matched as words.

A hit protects the block (kept verbatim), exactly like a rules.py hit; it never redacts, because a topic word is not a
span of personal data. Terms are matched case-insensitively on word boundaries. Company finance ("revenue", "operating
costs", "price") is deliberately absent: it is not private information about a person.
"""

import re

TOPICS = {
    "health": (
        r"diagnos\w*", r"symptoms?", r"medications?", r"medicines?", r"prescri(?:bed|ption)s?", r"\d+\s?mg",
        r"dosage", r"allerg(?:y|ies|ic)", r"blood (?:test|pressure|sugar|work)", r"therap(?:y|ist)", r"psychiatr\w*",
        r"depress(?:ed|ion)", r"anxiety", r"antidepressants?", r"panic attacks?", r"cancer", r"tumou?r", r"diabet\w*",
        r"insulin", r"chemo\w*", r"pregnan\w*", r"miscarriage", r"surgery", r"hospitali[sz]ed", r"illness",
        r"disorder", r"mental health", r"suicid\w*", r"self[- ]harm", r"alcoholic", r"addict\w*",
        r"rehab", r"overdose", r"liver enzymes?", r"medical (?:record|history|condition|leave)s?", r"sick leave",
        r"disabilit(?:y|ies)", r"abortion", r"fertility", r"ivf", r"genetic\w*", r"dna test\w*", r"brca\d?",
        r"mutations?", r"stds?", r"sti", r"hiv",
    ),
    "abuse": (
        r"restraining order", r"domestic (?:violence|abuse)", r"abus(?:e|ed|ive)", r"threatened me", r"stalk(?:s|ed|ing)",
    ),
    "employment": (
        r"performance improvement plan", r"fired", r"terminated", r"laid off", r"dui", r"dwi", r"background check",
        r"employee review",
    ),
    "non_public": (
        r"not (?:yet )?public", r"not public yet", r"before the (?:public )?announcement", r"keep (?:this|it) internal",
        r"internal only", r"insider",
    ),
    "personal_finance": (
        r"salary", r"salaries", r"my (?:income|wages?|pay|paycheck|savings|pension)", r"bank account", r"credit cards?",
        r"credit score", r"debts?", r"i owe", r"owe(?:s|d)? \$", r"(?:my|student|personal|car|payday) loans?",
        r"loan (?:payments?|balance|repayments?)", r"mortgage", r"bankrupt\w*", r"tax returns?",
        r"agi", r"net worth", r"overdraft", r"payslips?", r"wire \$", r"inheritance",
    ),
    "legal": (
        r"lawsuits?", r"sued", r"suing", r"settlement", r"nda", r"non-disclosure", r"attorney", r"lawyer",
        r"court (?:case|hearing|order|date)", r"custody", r"divorce", r"arrest(?:ed)?", r"criminal record",
        r"convicted", r"conviction", r"investigation", r"harass\w*", r"misconduct", r"disciplinary", r"whistleblow\w*",
        r"confidential", r"under investigation", r"grievance", r"probation",
    ),
    "identity": (
        r"home address", r"maiden name", r"security (?:question|answer)", r"date of birth", r"born (?:on )?\d",
        r"social security", r"passport", r"driver'?s licen[cs]e", r"my password", r"pin (?:code|number)",
        r"religio(?:n|us beliefs)", r"sexual orientation", r"ethnicity", r"immigration status", r"visa status",
        r"home phone", r"my (?:daughter|son|wife|husband|partner|mother|father|mom|dad)'?s? (?:name|address|school)",
    ),
}

_PATTERNS = {topic: re.compile(r"\b(?:" + "|".join(terms) + r")\b", re.IGNORECASE) for topic, terms in TOPICS.items()}


def topic_hits(text: str) -> list[str]:
    """Names of the sensitive topics the text mentions, e.g. ["health"]; [] when none."""
    if not text:
        return []
    return [topic for topic, pattern in _PATTERNS.items() if pattern.search(text)]
