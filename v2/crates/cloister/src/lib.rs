// eternity2-cloister — vol-212 clean crate for the CLOISTER family:
// the 14×14 interior puzzle, standalone (free rim) or border-anchored
// (CLOISTER-II: a fixed perfect frame turns the 56 IB edges into real
// constraints from cell 1).
//
// Modules:
//   model    — interior piece model + bitset candidate tables + synthetic
//              generator for unit tests
//   frame    — a fixed border ring: placement, BB score, per-cell rim
//              color targets for the interior search
//   dfs      — break-DFS (scheduled gates, hint machinery, pluggable scan,
//              optional discrepancy bound) + exact endgame triggers
//   endgame  — exact 1-row tail B&B and 2-row column-pair B&B
//   sa       — max-(II+IB) annealer with window-LNS and exact-region moves
//   border   — exact border-attach MIP (HiGHS): given an interior, the
//              optimal 60-piece ring (also used to generate frames)
//   io       — board JSON / bucas URL / history CSV discipline
//   verify   — independent full-board verification (uniqueness, hints,
//              border legality, II/IB/BB recount; grey-grey never matches)
//
// Vol-211 results this crate must reproduce (regression gate):
//   free-rim DFS wall 174/196; unhinted breaks5+et8 30s → II≈354-356;
//   attach of the Bucas-469 interior → exactly 469.

#![forbid(unsafe_code)]

pub mod border;
pub mod dfs;
pub mod endgame;
pub mod frame;
pub mod io;
pub mod model;
pub mod rng;
pub mod sa;
pub mod verify;
