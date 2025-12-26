#!/bin/bash
# Convenience script to run the benchmark tool

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Run the benchmark from the build directory
exec "$SCRIPT_DIR/build/benchmark/benchmark" "$@"
