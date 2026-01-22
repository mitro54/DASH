# Fedora 40 Build Environment for DAIS
FROM fedora:40

# Install build dependencies (matching README instructions)
RUN dnf install -y \
    gcc-c++ \
    cmake \
    make \
    python3-devel \
    git \
    && dnf clean all

# Set working directory
WORKDIR /app

# Copy project files
COPY . .

# Build DAIS
RUN mkdir -p build && cd build && cmake .. && make

# Default command: run tests
CMD ["./tests/test_build.sh"]
