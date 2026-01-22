# Debian 13 (Trixie) Build Environment for DAIS
FROM debian:trixie

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Install build dependencies (matching README instructions)
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    python3-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Build DAIS
RUN mkdir -p build && cd build && cmake .. && make

# Default command: run tests
CMD ["./tests/test_build.sh"]
