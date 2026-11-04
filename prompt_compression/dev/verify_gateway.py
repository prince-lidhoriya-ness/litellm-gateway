"""End-to-end check against a running proxy + mock provider (see README "Verification").

Sends one request per category, a streaming request, an opt-out request and a
multi-turn request with system/tool messages. The mock provider echoes the
messages it received, so each line reports whether the model got the prompt
unchanged. Category and ratio are in the proxy log ("prompt compression: ...").

Run:  python prompt_compression/dev/verify_gateway.py [--base-url http://localhost:4000]
Needs LITELLM_MASTER_KEY in the environment (the key the proxy was started with).
"""

import argparse
import json
import os

from openai import OpenAI

PROMPTS = {
    "sensitive": (
        "Please update my customer profile. My email is jane.doe@example.com and my phone is +1 555 013 2287. "
        "I was recently diagnosed with type 2 diabetes and my insurance policy number changed, so the clinic "
        "needs the new details before my appointment next Tuesday. Keep this private."
    ),
    "critical": (
        "Write a Python function parse_order(line) that splits on ';', returns a dict with keys id, sku, qty, "
        "and raises ValueError if qty is not a positive integer. Order IDs look like ORD-2024-88731 and SKUs "
        "like BLK-4410-XL. Use only the standard library and keep the signature exactly as given."
    ),
    "non_sensitive": (
        "The city park was renovated last year. It now has a larger playground, a walking trail along the "
        "river, new benches near the pond and a small cafe that sells coffee and pastries. On weekends many "
        "families visit, and local musicians sometimes play near the entrance in the afternoon while people relax."
    ),
    "less_important": (
        "Hi there! Hope you're having a great day and a lovely week so far. Thanks so much again for all the help "
        "last time, really appreciate it, you're the best! Anyway, as I said before, just saying hello again, "
        "nothing urgent at all, have a nice evening and talk soon, cheers and kind regards!"
    ),
}


def echoed_messages(content: str) -> list:
    return json.loads(content)["received_messages"]


def describe(sent: list, received: list) -> str:
    sent_chars = sum(len(m.get("content") or "") for m in sent if isinstance(m.get("content"), str))
    received_chars = sum(len(m.get("content") or "") for m in received if isinstance(m.get("content"), str))
    return f"unchanged={sent == received} chars {sent_chars}->{received_chars}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:4000")
    parser.add_argument("--model", default="mock-echo")
    parser.add_argument("--only", choices=list(PROMPTS), nargs="*")
    args = parser.parse_args()
    client = OpenAI(base_url=args.base_url, api_key=os.environ["LITELLM_MASTER_KEY"])

    for category, text in PROMPTS.items():
        if args.only and category not in args.only:
            continue
        sent = [{"role": "user", "content": text}]
        response = client.chat.completions.create(model=args.model, messages=sent)
        received = echoed_messages(response.choices[0].message.content)
        print(f"[{category:14s}] {describe(sent, received)}")
        if category in ("non_sensitive", "less_important") and sent != received:
            print(f"    received text: {received[0]['content']!r}")
    if args.only:
        return

    sent = [{"role": "user", "content": PROMPTS["less_important"]}]
    stream = client.chat.completions.create(model=args.model, messages=sent, stream=True)
    content = "".join(chunk.choices[0].delta.content or "" for chunk in stream if chunk.choices)
    print(f"[stream        ] {describe(sent, echoed_messages(content))}")

    response = client.chat.completions.create(
        model=args.model, messages=sent, extra_body={"metadata": {"prompt_compression": False}}
    )
    print(f"[opt-out       ] {describe(sent, echoed_messages(response.choices[0].message.content))}")

    conversation = [
        {"role": "system", "content": "You are a support assistant. " + PROMPTS["less_important"]},
        {"role": "user", "content": PROMPTS["non_sensitive"]},
        {"role": "assistant", "content": None, "tool_calls": [
            {"id": "call_1", "type": "function", "function": {"name": "lookup_park", "arguments": "{\"city\": \"Lisbon\"}"}}
        ]},
        {"role": "tool", "tool_call_id": "call_1", "content": PROMPTS["less_important"]},
        {"role": "user", "content": PROMPTS["less_important"]},
    ]
    tools = [{"type": "function", "function": {"name": "lookup_park", "description": "Find a park.",
                                               "parameters": {"type": "object", "properties": {"city": {"type": "string"}}}}}]
    response = client.chat.completions.create(model=args.model, messages=conversation, tools=tools)
    received = echoed_messages(response.choices[0].message.content)
    print(f"[multi-turn    ] roles_in_order={[m['role'] for m in received] == [m['role'] for m in conversation]} "
          f"system_unchanged={received[0] == conversation[0]} tool_call_unchanged={received[2]['tool_calls'][0]['function'] == conversation[2]['tool_calls'][0]['function']} "
          f"tool_result_unchanged={received[3]['content'] == conversation[3]['content']} "
          f"user_msgs_compressed={[received[i]['content'] != conversation[i]['content'] for i in (1, 4)]}")


if __name__ == "__main__":
    main()
