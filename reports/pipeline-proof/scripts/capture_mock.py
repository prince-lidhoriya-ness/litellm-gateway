"""Capture mock provider: echoes the exact messages and tools the gateway sent, as JSON content.

Serves the gateway's `obs-mock` model (MOCK_LLM_API_BASE=http://host.docker.internal:4010/v1).
Used to see the post-pipeline prompt byte for byte. Logs only counts, never text.

    .venv-compression/Scripts/python reports/pipeline-proof/scripts/capture_mock.py --port 4010
"""

import argparse
import json
import logging
import time
import uuid

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

logging.basicConfig(level=logging.INFO, format="%(asctime)s capture-mock: %(message)s")
app = FastAPI()


@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def chat(request: Request):
    body = await request.json()
    content = json.dumps({"received_messages": body.get("messages", []), "received_tools": body.get("tools")})
    logging.info("messages=%d tools=%d stream=%s", len(body.get("messages", [])), len(body.get("tools") or []), body.get("stream"))
    base = {"id": f"chatcmpl-{uuid.uuid4().hex[:12]}", "created": int(time.time()), "model": body.get("model")}
    usage = {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}
    if body.get("stream"):
        def events():
            for start in range(0, len(content), 256):
                chunk = {**base, "object": "chat.completion.chunk",
                         "choices": [{"index": 0, "delta": {"role": "assistant", "content": content[start:start + 256]}, "finish_reason": None}]}
                yield f"data: {json.dumps(chunk)}\n\n"
            yield f"data: {json.dumps({**base, 'object': 'chat.completion.chunk', 'choices': [{'index': 0, 'delta': {}, 'finish_reason': 'stop'}], 'usage': usage})}\n\n"
            yield "data: [DONE]\n\n"
        return StreamingResponse(events(), media_type="text/event-stream")
    return JSONResponse({**base, "object": "chat.completion", "usage": usage,
                         "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}]})


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=4010)
    uvicorn.run(app, host="127.0.0.1", port=parser.parse_args().port, log_level="warning")
