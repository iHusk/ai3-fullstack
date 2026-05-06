#!/usr/bin/env bash
# Northbrook QA — Docker launcher (macOS / Linux)
# Usage: ./scripts/run.sh [-r|--rebuild] [-h|--help]
#
# Run from the repo root. Builds the image on first run, then starts
# the app on http://localhost:8501. Press Ctrl+C to stop.

set -euo pipefail

IMAGE_NAME="northbrook-qa"
CONTAINER_NAME="northbrook-qa-app"
PORT="${PORT:-8501}"
REBUILD=false

for arg in "$@"; do
    case "$arg" in
        -r|--rebuild) REBUILD=true ;;
        -h|--help)
            echo "Usage: ./scripts/run.sh [-r|--rebuild] [-h|--help]"
            echo "App will start on http://localhost:${PORT}"
            echo "Override port: PORT=8502 ./scripts/run.sh"
            exit 0 ;;
        *) echo "Unknown option: $arg"; exit 1 ;;
    esac
done

if ! command -v docker >/dev/null 2>&1; then
    echo "ERROR: Docker is not installed. Install Docker Desktop:"
    echo "       https://www.docker.com/products/docker-desktop/"
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "ERROR: Cannot reach the Docker daemon. Start Docker Desktop."
    echo "       (Linux: confirm your user is in the 'docker' group.)"
    exit 1
fi

if lsof -iTCP:${PORT} -sTCP:LISTEN >/dev/null 2>&1; then
    echo "ERROR: Port ${PORT} is in use."
    echo "       Stop the other process or run: PORT=8502 ./scripts/run.sh"
    exit 1
fi

# Clean any stale container from a prior crashed run
docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true

if $REBUILD || ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
    echo "Building image '${IMAGE_NAME}'... (first build takes 5-10 min)"
    docker build -t "$IMAGE_NAME" .
fi

cleanup() {
    if docker ps -q -f "name=^${CONTAINER_NAME}$" | grep -q .; then
        echo ""
        echo "Stopping container..."
        docker stop "$CONTAINER_NAME" >/dev/null 2>&1 || true
    fi
}
trap cleanup INT TERM

echo ""
echo "Starting app..."
echo "Open http://localhost:${PORT} in your browser."
echo "Press Ctrl+C to stop."
echo ""

mkdir -p data

# If a local .env exists, pass it so Phoenix env vars (and anthropic/voyage)
# reach the container. Community Cloud uses its Secrets dashboard for the
# Phoenix triple — but locally we read from .env to mirror "real" tracing.
ENV_FLAG=()
if [ -f .env ]; then
    ENV_FLAG=(--env-file .env)
fi

docker run --rm \
    --name "$CONTAINER_NAME" \
    -p "${PORT}:${PORT}" \
    "${ENV_FLAG[@]}" \
    -v "$(pwd)/data:/app/data" \
    "$IMAGE_NAME"
