#!/bin/bash
# setup_ollama.sh
# Pulls the required model into the named volume BEFORE starting the isolated container.
# This works by running a temporary container with network access.

# Volume name depends on the directory name (ai-safety-radar) + volume name (ollama_data)
# Attempt to detect or default to standard compose naming
VOLUME_NAME="ai-safety-radar_ollama_data" 
MODEL_NAME="ministral-3:14b"

echo "🐳 Downloading $MODEL_NAME into volume $VOLUME_NAME..."

CMD="docker"
if command -v podman &> /dev/null; then
    CMD="podman"
fi

# Start ollama server in background
echo "Starting temporary Ollama server..."
$CMD run -d --name ollama_setup \
    -v ${VOLUME_NAME}:/root/.ollama \
    ollama/ollama:latest

# Wait for server to be ready (more robust check)
echo "⏳ Waiting for ollama server to initialize..."
MAX_WAIT=30
COUNTER=0
until $CMD exec ollama_setup ollama list > /dev/null 2>&1; do
    sleep 2
    COUNTER=$((COUNTER + 2))
    if [ $COUNTER -ge $MAX_WAIT ]; then
        echo "❌ ERROR: Ollama server failed to start within ${MAX_WAIT}s"
        $CMD stop ollama_setup
        $CMD rm ollama_setup
        exit 1
    fi
    echo "Still waiting... (${COUNTER}s)"
done

echo "✅ Ollama server ready!"
echo "Pulling model $MODEL_NAME (this takes 5-10 minutes)..."
$CMD exec ollama_setup ollama pull $MODEL_NAME

# Verify the model was downloaded
echo "Verifying download..."
$CMD exec ollama_setup ollama list | grep ministral
if [ $? -eq 0 ]; then
    echo "✅ Model verified successfully!"
else
    echo "⚠️  WARNING: Model may not have downloaded correctly"
fi

echo "Stopping temporary server..."
$CMD stop ollama_setup
$CMD rm ollama_setup

echo "✅ Setup complete!"
echo "Run: ${CMD}-compose up -d"
