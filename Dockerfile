FROM docker.io/library/python:3.11-slim@sha256:07d4824036af339fa1b6ef769cc99d9c10a141769538b52b3b597c84f7a7b535
WORKDIR /app
# The exact context allowlist is checked against Play's startup source inventory.
COPY . .
USER 65532:65532
ENTRYPOINT ["python", "-I", "/app/scripts/play.py", "--emit-plan"]
