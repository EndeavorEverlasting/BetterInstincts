FROM python:3.11-slim@sha256:07d4824036af339fa1b6ef769cc99d9c10a141769538b52b3b597c84f7a7b535
WORKDIR /app
COPY bootstrap.py ./
COPY scripts/play.py scripts/first_run.py scripts/smart_start.py scripts/game_host.py scripts/launch_save_route.py scripts/launch_receipt.py ./scripts/
COPY betterinstincts/first_run.py ./betterinstincts/
USER 65532:65532
ENTRYPOINT ["python", "-I", "/app/scripts/play.py", "--emit-plan"]
