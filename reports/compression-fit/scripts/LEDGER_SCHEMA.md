# Evidence ledger schema (one JSON object per line, file raw/ledger/<name>.jsonl)

Every number or fact that will appear in REPORT.md must exist here first, with a verbatim quote that a script can find on the stated page.

Fields
- id        : short unique id, e.g. "LL1-007"
- method    : one of LLMLingua | LLMLingua-2 | LongLLMLingua | SelectiveContext | GistTokens | AutoCompressor | 500xCompressor | CPC | SCOPE | EHPC | H2O | SnapKV | RateDistortion | ARTICLE
- field     : mechanism | io | compression_ratio | context_loss | latency_compute | cost | limitation | reproducibility | tasks_tested | hardware | disagreement
- claim     : one plain sentence saying what the quote establishes (your words, no new numbers that are not in the quote)
- value     : the number(s) exactly as printed, or "" if the fact is qualitative
- metric    : metric name (EM, F1, ROUGE-1, accuracy, ...) or ""
- task      : dataset/task or ""
- conditions: target LLM, compression ratio/constraint, hardware, shots, query-aware or agnostic, whatever the number depends on
- source_file: path RELATIVE to reports/compression-fit/ of the raw-mode text file the quote came from (see below), or an https URL (for license / code release facts only), or an absolute path to a repo article .md
- page      : 1-based PDF page number (integer) for paper text files; null for URLs and article files
- locator   : "Table 3", "Sec. 5.2", "Abstract", "Appendix I", ...
- quote     : VERBATIM substring (<= 220 chars, one line) copied from that page of the raw-mode text. For table rows copy the row exactly as it appears in the raw text (e.g. "LLMLingua-2 79.08 457 5x 77.79 178 14x 70.02 269 3x 61.94 176 5x"). Do not retype from memory.

Page convention: raw-mode text files split pages with the form-feed character; page N = Nth chunk. Use scripts/pshow.py and scripts/pgrep.py (they print "p.N" / "PDF page N") so page numbers match what the verifier checks:
    python scripts/pshow.py <file> <first> [last]      # print pages
    python scripts/pgrep.py <file> <regex> [ctx]       # find lines, with page numbers
Raw-mode text files (use ONLY these as source_file):
    raw/papers_repo_raw/{llmlingua,500x-compressor,rate-distortion-framework}.txt
    raw/papers_fetched_raw/<name>-<arxivid>.txt   (llmlingua-2, gist-tokens, selective-context, autocompressor, cpc, scope, ehpc, h2o, snapkv, longllmlingua)

Rules
1. If a number is not printed in the source, do NOT write it. Record the gap as a limitation entry with value "not reported" and a quote from the nearest section that shows the topic is discussed (or skip it and list it in the notes file under "Not reported").
2. Tables extract badly in two-column PDFs: confirm every table row against raw-mode text, and confirm which column is which from the header row. If you cannot be sure of the column mapping, say so in `claim`.
3. Report the conditions with each number (target LLM, ratio, query-aware vs agnostic, shots). A number without conditions is useless.
4. Quote the paper's own limitations / failure analysis verbatim where it exists.
5. When the repo article (path given in your task) says something the paper contradicts or cannot support, add a ledger line with method "ARTICLE" and field "disagreement": quote = the article sentence (verbatim from the .md file, page null, source_file = the absolute article path); claim = what the paper says instead, citing the id of the paper line that shows it.
