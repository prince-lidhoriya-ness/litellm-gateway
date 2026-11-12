"""Recover a masked observation or a compacted turn by its ref (obs_<12 hex> or turn_<12 hex>).

    python -m context_engineering.recover obs_3f9a1c2b7d10            # CONTEXT_STORE=redis (shared store)
    python -m context_engineering.recover obs_3f9a1c2b7d10 --json

The in-memory store lives inside each proxy worker, so from outside the proxy only the Redis store can be read. Inside
the proxy, mentioning a ref in a message restores the original on the next request (masking.requested_refs), and the
client always holds the original in its own copy of the conversation: the report in metadata["context_engineering"]
maps every ref to the original message index.
"""

import argparse
import json
import sys
from pathlib import Path

_GATEWAY_DIR = str(Path(__file__).resolve().parent.parent)
if _GATEWAY_DIR not in sys.path:
    sys.path.insert(0, _GATEWAY_DIR)

from context_engineering.settings import ContextSettings  # noqa: E402
from context_engineering.store import build_store  # noqa: E402


def recover(ref: str, store=None):
    store = store or build_store(ContextSettings.from_env())
    return store.get(ref)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("ref")
    parser.add_argument("--json", action="store_true", help="print the stored entry as JSON")
    args = parser.parse_args(argv)
    entry = recover(args.ref)
    if entry is None:
        print(f"{args.ref}: not found (expired, never stored, or a per-worker memory store)", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(entry, indent=1, ensure_ascii=False))
    elif entry.get("kind") == "observation":
        content = entry.get("content")
        print(content if isinstance(content, str) else json.dumps(content, ensure_ascii=False))
    else:
        print(json.dumps(entry.get("messages", entry), indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
