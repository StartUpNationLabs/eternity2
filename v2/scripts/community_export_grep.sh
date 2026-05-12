#!/usr/bin/env bash
# Run the vol-8 community-corpus mining battery.
#
# Reads:  output/v8_grep/corpus.txt           (built by community_build_corpus.py)
# Writes: output/v8_grep/hits/<pattern>.txt   (one file per query bucket)
#
# Each output line keeps the [source:id|date|author|subject] prefix from the
# corpus so the provenance is visible without re-joining indexes.

set -euo pipefail

CORPUS="${CORPUS:-output/v8_grep/corpus.txt}"
OUT="output/v8_grep/hits"
mkdir -p "$OUT"

if [[ ! -f "$CORPUS" ]]; then
  echo "missing $CORPUS — run scripts/community_build_corpus.py first" >&2
  exit 1
fi

run() {
  local name="$1"; shift
  # remaining args are passed to grep
  local target="$OUT/${name}.txt"
  if grep -EHn "$@" "$CORPUS" > "$target" 2>/dev/null; then
    : # ok
  fi
  local n
  n=$(wc -l < "$target" | tr -d ' ')
  printf '  %-32s %6d hits → %s\n' "$name" "$n" "$target"
}

echo "== scores =="
# Canonical "<score>/480" mentions, 5-clue regime above 459
run scores_460_479         '\b(46[0-9]|47[0-9])/480\b'
run scores_460_479_loose   -i 'score[d]?[:= ]+(46[0-9]|47[0-9])\b'
run scores_above_454       '\b4(5[5-9]|6[0-9]|7[0-9])/480\b'
run scores_slash_480       '\b4[0-9][0-9][ ]?/[ ]?480\b'

echo "== bucas URLs (the standard E2 visualiser) =="
run bucas_urls             -i -- 'e2\.bucas\.name'
run bucas_board_param      -i -- 'board_pieces=|board_edges='

echo "== algorithm vocabulary not in academic papers =="
run x_method               -i '\bX[- ]?method\b'
run z_method               -i '\bZ[- ]?method\b'
run anchor_pieces          -i 'anchor piece(s)?'
run border_family          -i 'border famil(y|ies)'
run stripe_corridor        -i '(\bstripe(s|d)?\b|corridor)'
run useless_precious       -i '\b(useless|precious|good piece|bad piece)\b'
run tileability_2x3        -i '(2 ?x ?3|2-by-3|tilab(le|ility))'
run frame_first            -i '(frame[- ]first|border[- ]first|frame solv(ing|ed))'
run interior_first         -i '(interior[- ]first|center[- ]first|middle[- ]first)'
run diagonal_spiral        -i '(\bdiagonal\b|\bspiral\b)'
run rare_color             -i '(rare colou?rs?|abundant colou?rs?)'
run mismatch_budget        -i 'mismatch(es)?'
run conflicts_allowed      -i '(conflict[s]? allowed|allow[a-z]* conflict|partial fit|allow[a-z]* mismatch)'
run motif_pattern          -i '(\bmotif(s)?\b|\bpattern[- ]?count)'
run scheduled_relaxation   -i '(scheduled relax|relax(ed|ation)|forced backtrack|jump back)'

echo "== sub-puzzle decompositions =="
run subpuzzle_5x5          -i '(\b5 ?x ?5\b|\b5-by-5\b)'
run subpuzzle_8x8          -i '\b8 ?x ?8\b'
run subpuzzle_6x6          -i '\b6 ?x ?6\b'
run subpuzzle_12x6         -i '(\b12 ?x ?6\b|\b6 ?x ?12\b)'
run quadrant               -i '(\bquadrant|quarter board\b)'

echo "== named hobbyists =="
run verhaard               -i 'verhaard'
run blackwood              -i 'blackwood'
run selby                  -i '\bselby\b'
run riordan                -i '\briordan\b'
run jfbucas                -i '(jfbucas|jf bucas|jean.?francois bucas)'
run kotrla                 -i 'kotrla'
run wauters                -i '(wauters|salassa|munera)'

echo "== solver names / tools =="
run eii_solver             -i '(\beii\b|shortestpath\.se)'
run libblackwood           -i 'libblackwood'
run dlx                    -i '(\bdlx\b|dancing links)'
run sat                    -i '(\bsat\b|maxsat)'
run ga                     -i '(genetic algorithm|\bGA\b|crossover)'
run sa_ts                  -i '(simulated annealing|tabu)'

echo "== suggestive 'I tried / I noticed / the trick' phrases =="
run i_tried                -i "(I tried|I've tried)"
run i_noticed              -i '(I noticed|I observ(ed|e)|I found|I realised|I realized)'
run what_about             -i '(what about|have you tried|consider(ed)?)'
run the_trick              -i '(the trick is|the key is|the secret)'

echo "== piece-set / generator statistics chatter =="
run piece_statistics       -i 'piece (statistics|distribution|frequenc|count)'
run color_balance          -i '(colou?r balance|colou?r distribution|colou?r frequenc)'
run hint_pieces            -i '(hint piece|clue piece|fixed piece)'
run rare_edges             -i '(rare edge|rare colou?r|gray edge|grey edge)'

echo "== attachments / artifacts =="
run attachments            -i 'ATTACH:'
run github_links           -i 'github\.com'
run gist_links             -i 'gist\.github'
run pastebin               -i '(pastebin|paste\.ee)'

echo
echo "done. browse with: ls -la $OUT"
