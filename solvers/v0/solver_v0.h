#ifndef ETERNITY2_SOLVER_V0_H
#define ETERNITY2_SOLVER_V0_H

#include "v1/board/board.h"
#include <atomic>
#include <functional>
#include <vector>
#include <unordered_set>
#include <mutex>

namespace eternity2_v0 {

// Shared data structure for v0 solver (original simple backtracking)
struct SharedDataV0 {
    Board& max_board;
    std::atomic_llong max_count;
    std::mutex& mutex;
    std::unordered_set<BoardHash>& hashes;
    std::atomic_llong board_count{0};
    std::atomic_llong hash_hit_count{0};
    std::atomic_bool stop{false};
    std::function<void(const Board&)> on_board_update = [](const Board&) {};
    unsigned int hash_length_threshold = 7;
    std::atomic_llong pieces_placed{0};
};

// Solve the board using v0's simple backtracking algorithm
void solve_board(Board& board, const std::vector<Piece>& pieces, SharedDataV0& shared_data);

} // namespace eternity2_v0

#endif // ETERNITY2_SOLVER_V0_H
