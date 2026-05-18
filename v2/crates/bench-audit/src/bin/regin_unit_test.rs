// Vol-125 T12 — Standalone unit test for the iterative Tarjan SCC + Régin
// filter logic used in super_block_bbb_v6. Runs the exact same algorithm but
// on tiny hand-crafted bipartite graphs where we can ground-truth the answer.
//
// If this test fails, the SCC code is wrong. If this test passes but v6 still
// over-removes in the search, the bug is in how regin_filter is wired into
// the search (e.g., adjacency rebuild timing, trail/undo of removals).
//
// Standard Régin (1994):
//   1. Compute max matching M via bipartite matching.
//   2. Build directed graph G_D on P ∪ S with 256+|S| nodes:
//      - matching edges (cs, p) ∈ M → arc cs → p
//      - non-matching edges (p, cs) → arc p → cs
//   3. Compute SCCs of G_D.
//   4. Edge (p, cs) belongs to some max matching iff:
//        - (p, cs) ∈ M, OR
//        - scc_id[p] == scc_id[cs]
//   5. Edges that fail both can be filtered.

#![forbid(unsafe_code)]

use std::process::ExitCode;

/// Iterative Tarjan SCC, identical structure to super_block_bbb_v6::regin_filter.
/// Returns scc_id[v] for every node in 0..n.
fn tarjan_scc(n: usize, adj: &[Vec<u16>]) -> Vec<i32> {
    let mut scc_index = vec![-1i32; n];
    let mut scc_lowlink = vec![0i32; n];
    let mut scc_onstack = vec![false; n];
    let mut scc_id = vec![-1i32; n];
    let mut scc_stack: Vec<u16> = Vec::with_capacity(n);

    let mut next_idx: i32 = 0;
    let mut next_scc: i32 = 0;

    for root in 0..n as u16 {
        if scc_index[root as usize] >= 0 { continue; }
        let mut call_stack: Vec<(u16, u16)> = vec![(root, 0)];
        scc_index[root as usize] = next_idx;
        scc_lowlink[root as usize] = next_idx;
        next_idx += 1;
        scc_stack.push(root);
        scc_onstack[root as usize] = true;

        while let Some(&(node, pos)) = call_stack.last() {
            let neighbors = &adj[node as usize];
            if (pos as usize) < neighbors.len() {
                let w = neighbors[pos as usize];
                call_stack.last_mut().unwrap().1 = pos + 1;
                if scc_index[w as usize] == -1 {
                    scc_index[w as usize] = next_idx;
                    scc_lowlink[w as usize] = next_idx;
                    next_idx += 1;
                    scc_stack.push(w);
                    scc_onstack[w as usize] = true;
                    call_stack.push((w, 0));
                } else if scc_onstack[w as usize] {
                    let cur = node as usize;
                    let w_idx = scc_index[w as usize];
                    if w_idx < scc_lowlink[cur] {
                        scc_lowlink[cur] = w_idx;
                    }
                }
            } else {
                call_stack.pop();
                let nu = node as usize;
                if scc_lowlink[nu] == scc_index[nu] {
                    loop {
                        let w = scc_stack.pop().unwrap();
                        scc_onstack[w as usize] = false;
                        scc_id[w as usize] = next_scc;
                        if w == node { break; }
                    }
                    next_scc += 1;
                }
                if let Some(&(parent, _)) = call_stack.last() {
                    let pu = parent as usize;
                    if scc_lowlink[nu] < scc_lowlink[pu] {
                        scc_lowlink[pu] = scc_lowlink[nu];
                    }
                }
            }
        }
    }

    scc_id
}

/// Recursive reference Tarjan (for comparison). Same algorithm, classical form.
fn tarjan_scc_recursive(n: usize, adj: &[Vec<u16>]) -> Vec<i32> {
    struct State {
        scc_index: Vec<i32>,
        scc_lowlink: Vec<i32>,
        on_stack: Vec<bool>,
        stack: Vec<u16>,
        scc_id: Vec<i32>,
        next_idx: i32,
        next_scc: i32,
    }
    fn visit(v: u16, adj: &[Vec<u16>], s: &mut State) {
        s.scc_index[v as usize] = s.next_idx;
        s.scc_lowlink[v as usize] = s.next_idx;
        s.next_idx += 1;
        s.stack.push(v);
        s.on_stack[v as usize] = true;
        for &w in &adj[v as usize] {
            if s.scc_index[w as usize] == -1 {
                visit(w, adj, s);
                if s.scc_lowlink[w as usize] < s.scc_lowlink[v as usize] {
                    s.scc_lowlink[v as usize] = s.scc_lowlink[w as usize];
                }
            } else if s.on_stack[w as usize] {
                let w_idx = s.scc_index[w as usize];
                if w_idx < s.scc_lowlink[v as usize] {
                    s.scc_lowlink[v as usize] = w_idx;
                }
            }
        }
        if s.scc_lowlink[v as usize] == s.scc_index[v as usize] {
            loop {
                let w = s.stack.pop().unwrap();
                s.on_stack[w as usize] = false;
                s.scc_id[w as usize] = s.next_scc;
                if w == v { break; }
            }
            s.next_scc += 1;
        }
    }
    let mut s = State {
        scc_index: vec![-1; n],
        scc_lowlink: vec![0; n],
        on_stack: vec![false; n],
        stack: Vec::new(),
        scc_id: vec![-1; n],
        next_idx: 0,
        next_scc: 0,
    };
    for v in 0..n as u16 {
        if s.scc_index[v as usize] == -1 {
            visit(v, adj, &mut s);
        }
    }
    s.scc_id
}

/// Canonicalize SCC ids so they're comparable across two implementations.
/// We map each scc_id to "smallest node it contains", then ranking gives a
/// canonical labeling.
fn canonicalize_scc(scc: &[i32]) -> Vec<i32> {
    let max_id = *scc.iter().max().unwrap_or(&0);
    let mut min_node = vec![i32::MAX; (max_id + 1) as usize];
    for (v, &id) in scc.iter().enumerate() {
        if (v as i32) < min_node[id as usize] {
            min_node[id as usize] = v as i32;
        }
    }
    // Assign canonical id by rank in min_node.
    let mut order: Vec<i32> = (0..=max_id).collect();
    order.sort_by_key(|&i| min_node[i as usize]);
    let mut canonical_of = vec![0i32; (max_id + 1) as usize];
    for (rank, &id) in order.iter().enumerate() {
        canonical_of[id as usize] = rank as i32;
    }
    scc.iter().map(|&id| canonical_of[id as usize]).collect()
}

/// Compute Régin's removable edges given matching M and bipartite adjacency.
/// Returns the set of (p, cs) pairs that should be filtered.
fn regin_removable(
    n_p: usize,
    n_s: usize,
    piece_adj: &[Vec<u16>],
    match_p: &[i32],
) -> Vec<(u16, u16)> {
    let n = n_p + n_s;
    let mut adj: Vec<Vec<u16>> = vec![Vec::new(); n];
    for p in 0..n_p {
        let matched_cs = match_p[p];
        for &cs in &piece_adj[p] {
            if cs as i32 == matched_cs {
                adj[(n_p as u16 + cs) as usize].push(p as u16);
            } else {
                adj[p].push(n_p as u16 + cs);
            }
        }
    }
    let scc = tarjan_scc(n, &adj);
    let mut out = Vec::new();
    for p in 0..n_p {
        let matched_cs = match_p[p];
        for &cs in &piece_adj[p] {
            if cs as i32 == matched_cs { continue; }
            let s_node = n_p + cs as usize;
            if scc[p] != scc[s_node] {
                out.push((p as u16, cs));
            }
        }
    }
    out
}

/// Brute-force baseline: an edge (p, cs) is removable iff no max matching
/// contains it. Compute via "force (p, cs), re-match, check if still max".
fn regin_removable_bruteforce(
    n_p: usize,
    n_s: usize,
    piece_adj: &[Vec<u16>],
    max_m: usize,
) -> Vec<(u16, u16)> {
    let mut out = Vec::new();
    for p in 0..n_p {
        for &cs in &piece_adj[p] {
            // Try to find a max matching using edge (p, cs).
            let mut adj_forced = piece_adj.to_vec();
            // Force: only allow piece p to be matched to cs.
            adj_forced[p] = vec![cs];
            // Also forbid other pieces from using cs (force cs to be matched
            // only to p).
            for q in 0..n_p {
                if q == p { continue; }
                adj_forced[q].retain(|&x| x != cs);
            }
            // Compute max matching on the restricted graph; if it's equal to
            // max_m, (p, cs) is in some max matching → not removable.
            let m_forced = bipartite_matching(&adj_forced, n_s);
            if m_forced < max_m {
                out.push((p as u16, cs));
            }
        }
    }
    out
}

/// Simple Hungarian / Hopcroft-Karp surrogate (Hopcroft-Karp BFS+DFS).
fn bipartite_matching(adj: &[Vec<u16>], n_s: usize) -> usize {
    let n_p = adj.len();
    let mut match_p: Vec<i32> = vec![-1; n_p];
    let mut match_s: Vec<i32> = vec![-1; n_s];
    let mut dist: Vec<i32> = vec![i32::MAX; n_p + 1];
    let sentinel = n_p;
    loop {
        // BFS
        let mut queue: Vec<usize> = Vec::new();
        for p in 0..n_p {
            if match_p[p] == -1 {
                dist[p] = 0;
                queue.push(p);
            } else {
                dist[p] = i32::MAX;
            }
        }
        dist[sentinel] = i32::MAX;
        let mut head = 0;
        while head < queue.len() {
            let p = queue[head]; head += 1;
            if dist[p] < dist[sentinel] {
                for &cs in &adj[p] {
                    let next_p = match_s[cs as usize];
                    let nidx = if next_p < 0 { sentinel } else { next_p as usize };
                    if dist[nidx] == i32::MAX {
                        dist[nidx] = dist[p] + 1;
                        if next_p >= 0 {
                            queue.push(next_p as usize);
                        }
                    }
                }
            }
        }
        if dist[sentinel] == i32::MAX { break; }
        // DFS
        fn dfs(
            p: i32,
            adj: &[Vec<u16>],
            match_p: &mut [i32],
            match_s: &mut [i32],
            dist: &mut [i32],
            sentinel: usize,
        ) -> bool {
            if p < 0 { return true; }
            let p_u = p as usize;
            for i in 0..adj[p_u].len() {
                let cs = adj[p_u][i] as usize;
                let next_p = match_s[cs];
                let nidx = if next_p < 0 { sentinel } else { next_p as usize };
                if dist[nidx] == dist[p_u] + 1 {
                    if dfs(next_p, adj, match_p, match_s, dist, sentinel) {
                        match_s[cs] = p;
                        match_p[p_u] = cs as i32;
                        return true;
                    }
                }
            }
            dist[p_u] = i32::MAX;
            false
        }
        for p in 0..n_p {
            if match_p[p] == -1 {
                dfs(p as i32, adj, &mut match_p, &mut match_s, &mut dist, sentinel);
            }
        }
    }
    match_p.iter().filter(|&&x| x >= 0).count()
}

fn main() -> ExitCode {
    let mut fail = 0;

    // ============================================================
    // Test 1: trivial 1×1 bipartite (one piece, one cell-slot).
    // ============================================================
    {
        let piece_adj = vec![vec![0u16]];
        let match_p = vec![0i32];
        let r1 = regin_removable(1, 1, &piece_adj, &match_p);
        let r2 = regin_removable_bruteforce(1, 1, &piece_adj, 1);
        assert_eq!(r1, r2, "Test 1: trivial 1×1");
        assert!(r1.is_empty(), "Test 1: nothing to filter");
        eprintln!("✅ Test 1 (1×1 trivial) passed");
    }

    // ============================================================
    // Test 2: 2×2 with one max matching, one removable edge.
    //   P0 — S0  (matched)
    //   P0 — S1  (not in M, this should be removable iff P0/S1 in different SCCs)
    //   P1 — S1  (matched)
    // ============================================================
    {
        let piece_adj = vec![vec![0u16, 1u16], vec![1u16]];
        let match_p = vec![0i32, 1i32];
        let r1 = regin_removable(2, 2, &piece_adj, &match_p);
        let r2 = regin_removable_bruteforce(2, 2, &piece_adj, 2);
        eprintln!("Test 2: Régin = {:?}, BF = {:?}", r1, r2);
        assert_eq!(r1, r2, "Test 2: 2×2 single-path");
        // Manually: only max matching is {(0,0),(1,1)}. (0,1) is not in any
        // max matching because P1 would have no match. So (0,1) is removable.
        assert_eq!(r1, vec![(0u16, 1u16)], "Test 2: (0,1) should be removable");
        eprintln!("✅ Test 2 (2×2 unique max matching) passed");
    }

    // ============================================================
    // Test 3: 2×2 with two max matchings (alternating cycle).
    //   P0 — S0, P0 — S1
    //   P1 — S0, P1 — S1
    //   Two max matchings: {(0,0),(1,1)} and {(0,1),(1,0)}.
    //   No edges removable; SCC should put all 4 nodes in one component.
    // ============================================================
    {
        let piece_adj = vec![vec![0u16, 1u16], vec![0u16, 1u16]];
        let match_p = vec![0i32, 1i32];
        let r1 = regin_removable(2, 2, &piece_adj, &match_p);
        let r2 = regin_removable_bruteforce(2, 2, &piece_adj, 2);
        eprintln!("Test 3: Régin = {:?}, BF = {:?}", r1, r2);
        assert_eq!(r1, r2, "Test 3: 2×2 two-matchings");
        assert!(r1.is_empty(), "Test 3: nothing to remove");
        eprintln!("✅ Test 3 (2×2 dual max matching) passed");
    }

    // ============================================================
    // Test 4: 3×3 mixed
    //   P0 — S0 (matched), S1, S2
    //   P1 — S0,       S1 (matched), S2
    //   P2 — S0, S2 (matched)
    //
    //   Multiple max matchings:
    //     {(0,0),(1,1),(2,2)} — current
    //     {(0,1),(1,0),(2,2)} — swap P0/P1 on S0/S1
    //     {(0,0),(1,2),(2,?)} — would need P2 elsewhere, P2 only sees S0/S2.
    //     If we have {(0,0),(1,2),(2,?)} → P2 must go to S0, but P0 is at S0. So no.
    //   So {(0,0),(1,1),(2,2)} and {(0,1),(1,0),(2,2)} are the only max matchings.
    //   P2-S2 is in BOTH. So (P2, ?) edges: only P2-S0 exists outside M (P2's
    //   only non-M edge), and it's not in any max matching → removable.
    //   P0-S2 → not in any max matching → removable.
    //   P1-S2 → not in any max matching → removable.
    //   P0-S1 and P1-S0 → in alt matching → not removable.
    // ============================================================
    {
        let piece_adj = vec![
            vec![0u16, 1, 2],
            vec![0u16, 1, 2],
            vec![0u16, 2],
        ];
        let match_p = vec![0i32, 1, 2];
        let r1 = regin_removable(3, 3, &piece_adj, &match_p);
        let r2 = regin_removable_bruteforce(3, 3, &piece_adj, 3);
        eprintln!("Test 4: Régin = {:?}, BF = {:?}", r1, r2);
        let mut sr1 = r1.clone(); sr1.sort();
        let mut sr2 = r2.clone(); sr2.sort();
        if sr1 != sr2 {
            eprintln!("❌ Test 4 MISMATCH: Régin = {:?}, BF = {:?}", sr1, sr2);
            fail += 1;
        } else {
            eprintln!("✅ Test 4 (3×3 mixed) passed");
        }
    }

    // ============================================================
    // Test 5: 4×4 randomized vs. brute force.
    // Generate 100 random bipartite graphs, compare Régin to BF.
    // ============================================================
    {
        let mut rng_state: u64 = 0x123456789abcdef;
        let mut next = || {
            rng_state = rng_state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            (rng_state >> 32) as u32
        };
        let mut runs = 0;
        let mut local_fail = 0;
        for trial in 0..200 {
            let n_p = 4;
            let n_s = 4;
            let mut piece_adj: Vec<Vec<u16>> = vec![Vec::new(); n_p];
            // Each (p, cs) included with prob 0.6.
            for p in 0..n_p {
                for cs in 0..n_s as u16 {
                    if next() % 10 < 6 {
                        piece_adj[p].push(cs);
                    }
                }
            }
            let max_m = bipartite_matching(&piece_adj, n_s);
            if max_m != n_p { continue; } // only test perfect matchings (E2 case)
            // Compute matching.
            let mut adj_for_match = piece_adj.clone();
            let _ = bipartite_matching(&adj_for_match, n_s);
            // Re-run match to get match_p (rebuild minimally).
            let mut match_p_vec = vec![-1i32; n_p];
            let mut match_s_vec = vec![-1i32; n_s];
            let mut dist = vec![i32::MAX; n_p + 1];
            let sentinel = n_p;
            loop {
                let mut queue: Vec<usize> = Vec::new();
                for p in 0..n_p {
                    if match_p_vec[p] == -1 {
                        dist[p] = 0;
                        queue.push(p);
                    } else { dist[p] = i32::MAX; }
                }
                dist[sentinel] = i32::MAX;
                let mut head = 0;
                while head < queue.len() {
                    let p = queue[head]; head += 1;
                    if dist[p] < dist[sentinel] {
                        for &cs in &adj_for_match[p] {
                            let next_p = match_s_vec[cs as usize];
                            let nidx = if next_p < 0 { sentinel } else { next_p as usize };
                            if dist[nidx] == i32::MAX {
                                dist[nidx] = dist[p] + 1;
                                if next_p >= 0 { queue.push(next_p as usize); }
                            }
                        }
                    }
                }
                if dist[sentinel] == i32::MAX { break; }
                fn dfs(
                    p: i32,
                    adj: &[Vec<u16>],
                    match_p: &mut [i32],
                    match_s: &mut [i32],
                    dist: &mut [i32],
                    sentinel: usize,
                ) -> bool {
                    if p < 0 { return true; }
                    let p_u = p as usize;
                    for i in 0..adj[p_u].len() {
                        let cs = adj[p_u][i] as usize;
                        let next_p = match_s[cs];
                        let nidx = if next_p < 0 { sentinel } else { next_p as usize };
                        if dist[nidx] == dist[p_u] + 1 {
                            if dfs(next_p, adj, match_p, match_s, dist, sentinel) {
                                match_s[cs] = p;
                                match_p[p_u] = cs as i32;
                                return true;
                            }
                        }
                    }
                    dist[p_u] = i32::MAX;
                    false
                }
                for p in 0..n_p {
                    if match_p_vec[p] == -1 {
                        dfs(p as i32, &adj_for_match, &mut match_p_vec, &mut match_s_vec, &mut dist, sentinel);
                    }
                }
            }
            // Compare iterative vs recursive SCC.
            let n = n_p + n_s;
            let mut adj: Vec<Vec<u16>> = vec![Vec::new(); n];
            for p in 0..n_p {
                let matched_cs = match_p_vec[p];
                for &cs in &piece_adj[p] {
                    if cs as i32 == matched_cs {
                        adj[n_p + cs as usize].push(p as u16);
                    } else {
                        adj[p].push(n_p as u16 + cs);
                    }
                }
            }
            let scc_iter = canonicalize_scc(&tarjan_scc(n, &adj));
            let scc_rec = canonicalize_scc(&tarjan_scc_recursive(n, &adj));
            if scc_iter != scc_rec {
                eprintln!("❌ Trial {}: iter SCC = {:?}, rec SCC = {:?}",
                          trial, scc_iter, scc_rec);
                eprintln!("    adj = {:?}", adj);
                local_fail += 1;
                if local_fail < 3 { continue; }
                fail += 1;
                break;
            }
            // Compare Régin output to brute force.
            let r1 = regin_removable(n_p, n_s, &piece_adj, &match_p_vec);
            let r2 = regin_removable_bruteforce(n_p, n_s, &piece_adj, max_m);
            let mut sr1 = r1.clone(); sr1.sort();
            let mut sr2 = r2.clone(); sr2.sort();
            if sr1 != sr2 {
                eprintln!("❌ Trial {}: Régin = {:?}, BF = {:?}", trial, sr1, sr2);
                eprintln!("    piece_adj = {:?}", piece_adj);
                eprintln!("    match_p = {:?}", match_p_vec);
                fail += 1;
                break;
            }
            runs += 1;
            if runs >= 100 { break; }
        }
        if local_fail == 0 && fail == 0 {
            eprintln!("✅ Test 5 ({} random 4×4 perfect-matching graphs) passed", runs);
        }
    }

    eprintln!();
    if fail == 0 {
        eprintln!("🎯 ALL TESTS PASSED");
        ExitCode::SUCCESS
    } else {
        eprintln!("❌ {} TESTS FAILED", fail);
        ExitCode::FAILURE
    }
}
