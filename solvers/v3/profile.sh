#!/bin/bash
#
# Profile script for Eternity II Solver v3
# Builds with profiling flags and generates performance reports
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BUILD_DIR="${BUILD_DIR:-$PROJECT_ROOT/build}"
PROFILE_OUTPUT_DIR="${PROFILE_OUTPUT_DIR:-$PROJECT_ROOT/profiles}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
PUZZLE_FILE=""
PROFILE_DURATION=30  # seconds
PROFILE_METHOD="auto"  # auto, sample, perf, gprof, instruments
VERBOSE=false

usage() {
    cat << EOF
Usage: $0 [OPTIONS] <puzzle_file>

Profile the v3 solver to identify hotpaths and performance bottlenecks.

Options:
    -d, --duration SECONDS    Profile duration in seconds (default: 30)
    -m, --method METHOD       Profiling method: auto, sample, perf, gprof, instruments (default: auto)
    -o, --output DIR          Output directory for profile reports (default: ./profiles)
    -v, --verbose             Verbose output
    -h, --help                Show this help message

Profiling Methods:
    auto       - Automatically detect best available method
    sample     - Use macOS 'sample' command (macOS only)
    perf       - Use Linux 'perf' tool (Linux only)
    gprof      - Use gprof (requires -pg flag, GCC only)
    instruments - Use macOS Instruments (requires Xcode)

Examples:
    $0 data/puzzles/puzzle.csv
    $0 -d 60 -m sample data/puzzles/puzzle.csv
    $0 -o ./my_profiles data/puzzles/puzzle.csv

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--duration)
            PROFILE_DURATION="$2"
            shift 2
            ;;
        -m|--method)
            PROFILE_METHOD="$2"
            shift 2
            ;;
        -o|--output)
            PROFILE_OUTPUT_DIR="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        -*)
            echo -e "${RED}Error: Unknown option $1${NC}" >&2
            usage
            exit 1
            ;;
        *)
            if [[ -z "$PUZZLE_FILE" ]]; then
                PUZZLE_FILE="$1"
            else
                echo -e "${RED}Error: Multiple puzzle files specified${NC}" >&2
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

if [[ -z "$PUZZLE_FILE" ]]; then
    echo -e "${RED}Error: Puzzle file is required${NC}" >&2
    usage
    exit 1
fi

if [[ ! -f "$PUZZLE_FILE" ]]; then
    echo -e "${RED}Error: Puzzle file not found: $PUZZLE_FILE${NC}" >&2
    exit 1
fi

# Convert puzzle file to absolute path (needed because we'll change directories)
if [[ "$PUZZLE_FILE" != /* ]]; then
    # Relative path - make it absolute
    PUZZLE_FILE="$(cd "$(dirname "$PUZZLE_FILE")" && pwd)/$(basename "$PUZZLE_FILE")"
fi

# Detect OS
OS="$(uname -s)"
case "$OS" in
    Darwin)
        DETECTED_OS="macos"
        ;;
    Linux)
        DETECTED_OS="linux"
        ;;
    *)
        DETECTED_OS="unknown"
        ;;
esac

# Auto-detect profiling method
if [[ "$PROFILE_METHOD" == "auto" ]]; then
    if [[ "$DETECTED_OS" == "macos" ]]; then
        if command -v sample &> /dev/null; then
            PROFILE_METHOD="sample"
        elif command -v instruments &> /dev/null; then
            PROFILE_METHOD="instruments"
        else
            PROFILE_METHOD="sample"  # sample is usually available on macOS
        fi
    elif [[ "$DETECTED_OS" == "linux" ]]; then
        if command -v perf &> /dev/null; then
            PROFILE_METHOD="perf"
        elif command -v gprof &> /dev/null; then
            PROFILE_METHOD="gprof"
        else
            echo -e "${YELLOW}Warning: No profiling tool found. Install 'perf' or 'gprof'${NC}" >&2
            exit 1
        fi
    else
        echo -e "${RED}Error: Unsupported OS: $OS${NC}" >&2
        exit 1
    fi
fi

echo -e "${GREEN}=== Eternity II Solver v3 Profiling ===${NC}"
echo "Puzzle file: $PUZZLE_FILE"
echo "Profile method: $PROFILE_METHOD"
echo "Duration: ${PROFILE_DURATION}s"
echo "Output directory: $PROFILE_OUTPUT_DIR"
echo ""

# Create output directory
mkdir -p "$PROFILE_OUTPUT_DIR"

# Build with Profile configuration
echo -e "${GREEN}Building solver with Profile configuration...${NC}"
cd "$BUILD_DIR"
if [[ "$VERBOSE" == "true" ]]; then
    cmake -DCMAKE_BUILD_TYPE=Profile "$PROJECT_ROOT"
    cmake --build . --target SolverV3 -j$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4)
else
    cmake -DCMAKE_BUILD_TYPE=Profile "$PROJECT_ROOT" > /dev/null 2>&1
    cmake --build . --target SolverV3 -j$(sysctl -n hw.ncpu 2>/dev/null || nproc 2>/dev/null || echo 4) > /dev/null 2>&1
fi

SOLVER_BIN="$BUILD_DIR/solvers/v3/SolverV3"
if [[ ! -f "$SOLVER_BIN" ]]; then
    echo -e "${RED}Error: Solver binary not found: $SOLVER_BIN${NC}" >&2
    exit 1
fi

echo -e "${GREEN}Build complete. Starting profiling...${NC}"

# Generate timestamp for output files
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
PUZZLE_NAME=$(basename "$PUZZLE_FILE" .csv)

# Run profiling based on method
case "$PROFILE_METHOD" in
    sample)
        # macOS sample command
        echo "Profiling with 'sample' (macOS)..."
        SAMPLE_OUTPUT="$PROFILE_OUTPUT_DIR/profile_${PUZZLE_NAME}_${TIMESTAMP}.txt"
        
        # Change to project root so relative paths work correctly
        cd "$PROJECT_ROOT"
        
        # Start solver in background
        "$SOLVER_BIN" "$PUZZLE_FILE" --timeout $((PROFILE_DURATION * 1000)) > /tmp/solver_output.log 2>&1 &
        SOLVER_PID=$!
        
        # Wait a moment for solver to start
        sleep 1
        
        # Check if process is still running
        if ! kill -0 "$SOLVER_PID" 2>/dev/null; then
            echo -e "${YELLOW}Warning: Solver process ended before profiling could start${NC}" >&2
            cat /tmp/solver_output.log
            exit 1
        fi
        
        # Sample the process (sample interval in ms, typically 1ms for detailed profiling)
        # Use a background process to kill sample after duration
        (
            sleep "$PROFILE_DURATION"
            pkill -P $$ sample 2>/dev/null || true
        ) &
        KILLER_PID=$!
        
        # Run sample (1ms interval for detailed sampling)
        sample "$SOLVER_PID" 1 -f "$SAMPLE_OUTPUT" 2>/dev/null || true
        
        # Clean up killer process
        kill "$KILLER_PID" 2>/dev/null || true
        
        # Wait for solver to finish or kill it
        wait "$SOLVER_PID" 2>/dev/null || kill "$SOLVER_PID" 2>/dev/null || true
        
        echo -e "${GREEN}Profile saved to: $SAMPLE_OUTPUT${NC}"
        echo ""
        if [[ -f "$SAMPLE_OUTPUT" ]] && [[ -s "$SAMPLE_OUTPUT" ]]; then
            echo "Top functions (showing first 30 lines):"
            head -30 "$SAMPLE_OUTPUT" | grep -E "^[0-9]+\s+[0-9]+\.[0-9]+%" || head -30 "$SAMPLE_OUTPUT"
        else
            echo -e "${YELLOW}Warning: Profile output file is empty or missing${NC}" >&2
        fi
        ;;
        
    perf)
        # Linux perf tool
        echo "Profiling with 'perf' (Linux)..."
        PERF_DATA="$PROFILE_OUTPUT_DIR/perf_${PUZZLE_NAME}_${TIMESTAMP}.data"
        PERF_REPORT="$PROFILE_OUTPUT_DIR/perf_${PUZZLE_NAME}_${TIMESTAMP}.txt"
        
        # Change to project root so relative paths work correctly
        cd "$PROJECT_ROOT"
        
        perf record -o "$PERF_DATA" --call-graph dwarf -- \
            timeout "$PROFILE_DURATION" "$SOLVER_BIN" "$PUZZLE_FILE" --timeout $((PROFILE_DURATION * 1000)) || true
        
        perf report -i "$PERF_DATA" > "$PERF_REPORT" 2>&1 || {
            echo -e "${YELLOW}Warning: perf report failed, trying with different options...${NC}"
            perf report --stdio -i "$PERF_DATA" > "$PERF_REPORT" 2>&1 || true
        }
        
        echo -e "${GREEN}Profile data saved to: $PERF_DATA${NC}"
        echo -e "${GREEN}Profile report saved to: $PERF_REPORT${NC}"
        echo ""
        echo "Top functions:"
        head -30 "$PERF_REPORT" || echo "No profile data found"
        ;;
        
    gprof)
        # gprof (requires -pg flag)
        echo "Profiling with 'gprof'..."
        GPROF_OUTPUT="$PROFILE_OUTPUT_DIR/gprof_${PUZZLE_NAME}_${TIMESTAMP}.txt"
        
        # Change to project root so relative paths work correctly
        cd "$PROJECT_ROOT"
        
        timeout "$PROFILE_DURATION" "$SOLVER_BIN" "$PUZZLE_FILE" --timeout $((PROFILE_DURATION * 1000)) || true
        
        if [[ -f gmon.out ]]; then
            gprof "$SOLVER_BIN" gmon.out > "$GPROF_OUTPUT" 2>&1
            mv gmon.out "$PROFILE_OUTPUT_DIR/gmon_${PUZZLE_NAME}_${TIMESTAMP}.out"
            echo -e "${GREEN}Profile saved to: $GPROF_OUTPUT${NC}"
            echo ""
            echo "Top functions (flat profile):"
            sed -n '/flat profile:/,/^$/p' "$GPROF_OUTPUT" | head -30
        else
            echo -e "${YELLOW}Warning: gmon.out not found. Make sure solver was built with -pg flag.${NC}" >&2
        fi
        ;;
        
    instruments)
        # macOS Instruments (requires Xcode)
        echo "Profiling with 'instruments' (macOS)..."
        INSTRUMENTS_OUTPUT="$PROFILE_OUTPUT_DIR/instruments_${PUZZLE_NAME}_${TIMESTAMP}.trace"
        
        # Change to project root so relative paths work correctly
        cd "$PROJECT_ROOT"
        
        instruments -t "Time Profiler" -D "$INSTRUMENTS_OUTPUT" \
            "$SOLVER_BIN" "$PUZZLE_FILE" --timeout $((PROFILE_DURATION * 1000)) || true
        
        echo -e "${GREEN}Instruments trace saved to: $INSTRUMENTS_OUTPUT${NC}"
        echo "Open with: open $INSTRUMENTS_OUTPUT"
        ;;
        
    *)
        echo -e "${RED}Error: Unknown profiling method: $PROFILE_METHOD${NC}" >&2
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}=== Profiling Complete ===${NC}"
echo "Output directory: $PROFILE_OUTPUT_DIR"

