"""Local OpenAI-compatible mock provider for verifying the gateway without an API key.

POST /v1/chat/completions answers with the exact messages it received, JSON-encoded
in choices[0].message.content (or streamed as SSE chunks when stream=true), so a
client can compare what reached the "model" with what it sent. Its own log line
only prints message count, roles and a sha256 per message, never the text.

Run:  python prompt_compression/dev/mock_openai_server.py --port 4010
"""

import argparse
import hashlib
import json
import logging
import time
import uuid

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s mock-llm: %(message)s")
logger = logging.getLogger("mock-llm")
app = FastAPI()


def _fingerprint(messages: list) -> list[str]:
    return [
        f"{m.get('role')}:{hashlib.sha256(json.dumps(m.get('content'), sort_keys=True).encode()).hexdigest()[:12]}"
        for m in messages
    ]


@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    logger.info("received model=%s stream=%s messages=%s", body.get("model"), body.get("stream"), _fingerprint(messages))
    content = json.dumps({"received_messages": messages})
    completion_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
    created = int(time.time())
    usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}

    if body.get("stream"):
        def events():
            step = 64
            for start in range(0, len(content), step):
                chunk = {
                    "id": completion_id, "object": "chat.completion.chunk", "created": created, "model": body.get("model"),
                    "choices": [{"index": 0, "delta": {"role": "assistant", "content": content[start:start + step]},
                                 "finish_reason": None}],
                }
                yield f"data: {json.dumps(chunk)}\n\n"
            final = {
                "id": completion_id, "object": "chat.completion.chunk", "created": created, "model": body.get("model"),
                "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}], "usage": usage,
            }
            yield f"data: {json.dumps(final)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(events(), media_type="text/event-stream")

    return JSONResponse(
        {
            "id": completion_id, "object": "chat.completion", "created": created, "model": body.get("model"),
            "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
            "usage": usage,
        }
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=4010)
    args = parser.parse_args()
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
