# Puzzle Generator

A standalone command-line script to generate Eternity II-style puzzles with customizable parameters.

## Features

The script supports:
- **Board size**: Specify puzzle dimensions (2-16) or size ranges (e.g., 4-8)
- **Number of colors**: Configure color count or color ranges (e.g., 6-12)
- **Batch generation**: Create multiple puzzles with random configurations
- **All combinations**: Generate one puzzle for each size/color combination
- **Custom output directory**: Specify where to save the generated files
- **File format**: Follows the pattern `size_<size>_colors_<colors>_<hash>.csv`
- **Official puzzles**: Use `--official` flag for `size_<size>_official_<hash>.csv` format

## Usage Examples

```bash
# Generate a single 4x4 puzzle with 8 colors
node generate_puzzles.js --size 4 --colors 8

# Generate 5 puzzles of size 7x7 with 12 colors
node generate_puzzles.js --size 7 --colors 12 --count 5

# Generate 5 puzzles with sizes 4-8 and colors 6-12 (random combinations)
node generate_puzzles.js --size 4-8 --colors 6-12 --count 5

# Generate all combinations of sizes 4-6 and colors 8-10
node generate_puzzles.js --size 4-6 --colors 8-10 --all-combinations

# Generate 10 puzzles with size 7 and colors ranging from 10-14
node generate_puzzles.js -s 7 -c 10-14 -n 10 -o ./my_puzzles

# Generate an "official" puzzle for each size 4-8 with max colors
node generate_puzzles.js --size 4-8 --official --all-combinations

# Generate 3 puzzles and save to custom directory
node generate_puzzles.js -s 8 -c 10 -n 3 -o ./my_puzzles

# Show help
node generate_puzzles.js --help
```

## Options

- `--size, -s <number|range>`: Board size or range (e.g., 4 or 4-8) (default: 4)
- `--colors, -c <number|range>`: Number of colors or range (e.g., 8 or 6-12) (default: 8)
- `--count, -n <number>`: Number of puzzles to generate (default: 1)
  - Ignored when `--all-combinations` is used
- `--output, -o <path>`: Output directory (default: ./data/generated)
- `--official`: Mark puzzle as "official" in filename (uses max colors for each size)
- `--all-combinations`: Generate one puzzle for each size/color combination in the specified ranges
- `--help, -h`: Show help message

## How It Works

The script uses the same core logic as the frontend board generator:
1. Generates a valid Eternity II puzzle with matching edges
2. Shuffles and rotates pieces to create an unsolved puzzle
3. Exports to CSV format with proper validation
4. Adds a unique hash to each filename to prevent overwrites

## Performance

The generator is highly optimized and can create puzzles very quickly:
- Single puzzle: ~3ms
- 20 puzzles with varied sizes: ~60ms
- All combinations (size 4-6, colors 8-10): ~100ms
