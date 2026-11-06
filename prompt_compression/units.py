"""The unit that travels through the pipeline stages: one block of one message.

  segment and classify  -> kind (segmenter.py) and sensitive (sensitivity.py) are filled in
  router                -> action, reason, selectable, compressible are filled in
  actions               -> text, dropped are changed
  reassemble            -> the units of a message part are joined back in order
"""

from dataclasses import dataclass
from typing import Optional

KEEP = "keep"
SELECT = "select"
COMPRESS = "compress"


@dataclass
class Unit:
    message: int                  # index in the request's messages list
    part: Optional[int]           # content-part index, None when the content is a plain string
    kind: str                     # code | structured | exact | prose (segmenter.py)
    subtype: str
    text: str
    sep: str = ""                 # whitespace that followed the block in the original
    sensitive: bool = False
    sensitive_source: str = ""    # "rules" | "model" | "error" | ""
    rule_hits: tuple = ()
    edge: bool = False            # first or last paragraph of the latest user message
    action: str = KEEP            # keep | select | compress (the router's decision)
    reason: str = ""              # why: sensitive, last_user, edge, code, structured, exact, route_off, passage, records, prose
    selectable: bool = False      # may be dropped whole by a select-or-drop route
    compressible: bool = False    # may be sent to LLMLingua-2
    dropped: bool = False         # removed by select-or-drop, or merged into a compressed run

    @property
    def full(self) -> str:
        return self.text + self.sep

    @property
    def filled(self) -> bool:
        return bool(self.text.strip())
