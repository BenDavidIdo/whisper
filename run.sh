#!/usr/bin/env bash
# run.sh — Development automation for Whisper Flow
set -e

VENV_DIR=".venv"
PYTHON="python3"

_setup_venv() {
    if [ ! -d "$VENV_DIR" ]; then
        echo "Creating virtual environment..."
        $PYTHON -m venv "$VENV_DIR"
    fi
    # shellcheck source=/dev/null
    source "$VENV_DIR/bin/activate"
    echo "Installing dependencies..."
    pip install --quiet --upgrade pip
    pip install --quiet -r requirements.txt
    pip install --quiet -e .
}

_format() {
    echo "Formatting with black..."
    black whisperflow/ tests/
}

_lint() {
    echo "Linting with pylint..."
    pylint whisperflow/ --fail-under=9.9
}

_test() {
    echo "Running tests..."
    pytest tests/ \
        --cov=whisperflow \
        --cov-report=term-missing \
        --cov-fail-under=95 \
        -v \
        --ignore=tests/benchmark
}

_run_server() {
    echo "Starting Whisper Flow server on port 8181..."
    python -m uvicorn whisperflow.fast_server:app \
        --host 0.0.0.0 \
        --port 8181 \
        --reload
}

_benchmark() {
    echo "Running benchmarks (requires server on port 8181)..."
    pytest tests/benchmark/ \
        --benchmark-only \
        -v
}

case "$1" in
    -local)
        _setup_venv
        _format
        _lint
        _test
        ;;
    -test)
        source "$VENV_DIR/bin/activate" 2>/dev/null || true
        _format
        _lint
        _test
        ;;
    -run-server)
        source "$VENV_DIR/bin/activate" 2>/dev/null || true
        _run_server
        ;;
    -benchmark)
        source "$VENV_DIR/bin/activate" 2>/dev/null || true
        _benchmark
        ;;
    -docker-build)
        docker build -t whisperflow .
        ;;
    -docker-test)
        docker build -f Dockerfile.test -t whisperflow-test .
        ;;
    -docker-run)
        docker run --rm -p 8181:8181 \
            -v "$(pwd)/whisperflow/models:/app/whisperflow/models" \
            whisperflow
        ;;
    *)
        echo "Usage: $0 {-local|-test|-run-server|-benchmark|-docker-build|-docker-test|-docker-run}"
        echo ""
        echo "  -local        Setup venv, install deps, format, lint, test"
        echo "  -test         Format, lint, and test (uses existing venv)"
        echo "  -run-server   Start FastAPI server on port 8181"
        echo "  -benchmark    Run performance benchmarks"
        echo "  -docker-build Build production Docker image"
        echo "  -docker-test  Build and run tests in Docker"
        echo "  -docker-run   Run server in Docker container"
        exit 1
        ;;
esac
