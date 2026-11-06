"""Candidate labels of the zero-shot sensitivity model, and the dataset the model was selected on.

The pipeline decides nothing from these labels except SENSITIVE (sensitivity.py reads that one probability). The
other three are kept because the zero-shot model scores a text against all of them at once (a softmax over four
hypotheses), which is how the model was selected on eval/classifier_*.jsonl; dropping them would change the
probabilities and invalidate the measured threshold. They no longer route anything: what happens to a block of text
is decided by what kind of text it is (segmenter.py) and by the router (router.py), not by an importance label.
"""

SENSITIVE = "sensitive"
CRITICAL = "critical"
NON_SENSITIVE = "non_sensitive"
LESS_IMPORTANT = "less_important"

LABELS = (SENSITIVE, CRITICAL, NON_SENSITIVE, LESS_IMPORTANT)

# "plain" format: short label words fed to the NLI hypothesis template.
PLAIN_LABELS = {
    SENSITIVE: "sensitive",
    CRITICAL: "critical",
    NON_SENSITIVE: "non-sensitive",
    LESS_IMPORTANT: "less important",
}
PLAIN_TEMPLATE = "This text is {}."

# "descriptive" format: the full natural-language description of each label.
DESCRIPTIONS = {
    SENSITIVE: "personal data, credentials, secrets, health, financial, or private legal information",
    CRITICAL: "instructions, code, numbers, identifiers, or facts whose alteration would change the correct answer",
    NON_SENSITIVE: "ordinary content with no privacy or security concern",
    LESS_IMPORTANT: "greetings, filler, repetition, chit-chat, or redundant context",
}
DESCRIPTIVE_TEMPLATE = "This text contains {}."

LABEL_FORMATS = {
    "plain": (PLAIN_LABELS, PLAIN_TEMPLATE),
    "descriptive": (DESCRIPTIONS, DESCRIPTIVE_TEMPLATE),
}
