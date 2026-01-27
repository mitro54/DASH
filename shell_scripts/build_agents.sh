#!/bin/bash
set -e

# Directories
PROJECT_ROOT=$(pwd)
SRC_REMOTE="$PROJECT_ROOT/src/remote"
OUTPUT_Header="$PROJECT_ROOT/include/core/dais_agents.hpp"
BUILD_ARTIFACTS="$SRC_REMOTE/build_artifacts"

echo "[1/4] Cleaning previous artifacts..."
rm -rf "$BUILD_ARTIFACTS"
mkdir -p "$BUILD_ARTIFACTS"

echo "[2/4] Building cross-compilation Docker image..."
# Use -f to specify the Dockerfile explicitly
docker build -f "$SRC_REMOTE/Dockerfile.agents" -t dais-agents .

echo "[3/4] Extracting compiled agents..."
# We run the container briefly to copy files out
docker run --rm -v "$BUILD_ARTIFACTS:/output" dais-agents sh -c "cp /build/agent_* /output/ && chmod 777 /output/agent_*"

echo "[4/4] Generating C++ Header..."
python3 "$SRC_REMOTE/generate_header.py" "$BUILD_ARTIFACTS" "$OUTPUT_Header"

echo "Success! Agents updated in $OUTPUT_Header"
echo "You can now run 'make' to rebuild DAIS with the new agents."
