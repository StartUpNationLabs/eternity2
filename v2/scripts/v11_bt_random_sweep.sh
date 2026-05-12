#!/bin/bash
# Parallel sweep of random-order backtrackers with different seeds.
# Goal: see if multi-seed parallelism can reach vol-9's 308 cold-start.
set -e
cd "$(dirname "$0")/.."
mkdir -p output/v11_sp

# We need a seedable random mode. Hack: use Python random with a seed via env var.
# Actually scripts/v11_bp_backtrack.py uses 'random' mode but doesn't take a seed.
# Patch in via PYTHONHASHSEED to vary tie-breaks (insufficient — random.shuffle uses random module).
# Simpler: invoke with a seed wrapper.

cat > /tmp/v11_bt_random_seeded.py <<'EOF'
import os, sys, random
import numpy as np
seed = int(os.environ.get("RUN_SEED", "1"))
random.seed(seed); np.random.seed(seed)
sys.argv = ["v11_bp_backtrack.py", "--value-mode", "random",
            "--time-budget", "300", "--out", os.environ["OUT_PATH"]]
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "scripts"))
# Wait — scripts is relative. Make absolute.
import pathlib
root = pathlib.Path(__file__).resolve().parents[0]
sys.path.insert(0, str(root / "scripts"))
import importlib.util
spec = importlib.util.spec_from_file_location("v11_bp_backtrack", root / "scripts" / "v11_bp_backtrack.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.main()
EOF

for seed in 1 2 3 4 5 6 7 8; do
  out=output/v11_sp/bt_random_seed${seed}.json
  log=output/v11_sp/bt_random_seed${seed}.log
  rm -f "$out" "$log"
  RUN_SEED=$seed OUT_PATH=$out python3 -u /tmp/v11_bt_random_seeded.py > "$log" 2>&1 &
done
wait
echo "all seeded random runs done"
for f in output/v11_sp/bt_random_seed*.json; do
  python3 -c "
import json, sys
d = json.load(open(sys.argv[1]))
s = d['stats']
print(f'{sys.argv[1].split(chr(47))[-1]}: depth={s[\"max_depth\"]} score={s[\"max_score\"]} nodes={s[\"nodes\"]} t={d[\"elapsed_s\"]:.1f}s'
)
" "$f"
done | sort -t= -k3 -n -r
