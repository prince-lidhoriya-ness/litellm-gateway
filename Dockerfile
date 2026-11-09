# Extends the official LiteLLM image with LLMLingua-2 and the sensitivity encoder for local prompt compression
# (prompt_compression/ and observability/ are mounted into this image by docker-compose.quickstart.yml).
#
# Reproducible by construction (PROJECT_AUDIT_REPORT.md, F-19S):
#   * the base image is pinned by digest to the LiteLLM release the tests run against (1.106.0);
#   * every Python package is pinned to the versions in prompt_compression/requirements.txt (docker/requirements-image.txt);
#   * both models are downloaded at build time at pinned Hugging Face commits, and the image runs offline
#     (HF_HUB_OFFLINE=1), so a container never fetches weights at startup and never picks up a changed upstream model.
#
# Upgrade: change LITELLM_IMAGE (tag and digest) and the pins together, then rerun both test suites and the evals.
ARG LITELLM_IMAGE=litellm/litellm:v1.106.0@sha256:2e4c0371f3a8c28e4da131d77abaa8341cd3b0c2fcc4d34d7c5900431af7b9d0
FROM ${LITELLM_IMAGE}

# Model revisions: keep in sync with prompt_compression/settings.py (DEFAULT_*_REVISION).
ARG COMPRESSION_MODEL=microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank
ARG COMPRESSION_REVISION=5f0c82792b7ea14c6484e015b6a072009496b7f2
ARG ENCODER_MODEL=sentence-transformers/all-MiniLM-L6-v2
ARG ENCODER_REVISION=1110a243fdf4706b3f48f1d95db1a4f5529b4d41

# CPU-only torch wheel first, otherwise pip pulls the ~2GB CUDA build as a transitive dep.
COPY docker/requirements-image.txt /tmp/requirements-image.txt
RUN /app/.venv/bin/python3 -m ensurepip --upgrade \
    && /app/.venv/bin/python3 -m pip install --no-cache-dir "torch==2.15.0" --index-url https://download.pytorch.org/whl/cpu \
    && /app/.venv/bin/python3 -m pip install --no-cache-dir -r /tmp/requirements-image.txt \
    && rm /tmp/requirements-image.txt

# Weights live in the image, outside /root/.cache, so no volume can shadow them.
ENV HF_HOME=/opt/hf
RUN /app/.venv/bin/python3 -c "import sys; from huggingface_hub import snapshot_download; \
[snapshot_download(repo_id=r, revision=v) for r, v in zip(sys.argv[1::2], sys.argv[2::2])]" \
    "${COMPRESSION_MODEL}" "${COMPRESSION_REVISION}" "${ENCODER_MODEL}" "${ENCODER_REVISION}"

ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    TOKENIZERS_PARALLELISM=false
