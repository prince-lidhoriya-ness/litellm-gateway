"""Label set shared by the classifier, router and benchmark.

To add or change a label, edit LABELS, PRIORITY, PLAIN_LABELS and DESCRIPTIONS
here, then add a routing entry in router.ROUTES (see README.md).
"""

SENSITIVE = "sensitive"
CRITICAL = "critical"
NON_SENSITIVE = "non_sensitive"
LESS_IMPORTANT = "less_important"

LABELS = (SENSITIVE, CRITICAL, NON_SENSITIVE, LESS_IMPORTANT)

# Most restrictive first. Used when merging chunk labels or message labels.
PRIORITY = {SENSITIVE: 0, CRITICAL: 1, NON_SENSITIVE: 2, LESS_IMPORTANT: 3}

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


def most_restrictive(labels):
    """Return the highest-priority label from an iterable of labels."""
    return min(labels, key=PRIORITY.__getitem__)
