# Extends the official LiteLLM image with LLMLingua-2 for local prompt compression
# (see ai-features/compression.py, mounted into this image via docker-compose).
FROM docker.litellm.ai/berriai/litellm:main-stable

# CPU-only torch wheel first, otherwise pip pulls the ~2GB CUDA build as a transitive dep.
# transformers is pinned <5: llmlingua 0.2.2 only requires >=4.26.0, so pip otherwise
# installs the just-released transformers 5.x, which crashes loading the llmlingua-2 model.
RUN /app/.venv/bin/python3 -m ensurepip --upgrade \
    && /app/.venv/bin/python3 -m pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu \
    && /app/.venv/bin/python3 -m pip install --no-cache-dir llmlingua "transformers<5"
