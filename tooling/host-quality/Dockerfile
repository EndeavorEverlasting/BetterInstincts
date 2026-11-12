# Build only in a reviewed, operator-controlled environment; never auto-pull from the quality runner.
FROM python:3.11-slim-bookworm
RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir 'Pillow==11.3.0'
WORKDIR /work
USER 65534:65534
