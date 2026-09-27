FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

# Native libraries for OpenCV, pillow-heif, and ONNX Runtime (mirrors the root Dockerfile).
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libheif-dev \
    && rm -rf /var/lib/apt/lists/*

# Pre-create the Claude Code config dir (CLAUDE_CONFIG_DIR, so .claude.json lives there too)
# so the named volume mounted over it is owned by vscode.
RUN mkdir -p /home/vscode/.claude && chown vscode:vscode /home/vscode/.claude
