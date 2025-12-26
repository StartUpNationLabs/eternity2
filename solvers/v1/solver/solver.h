#include "board/board.h"
#include "common/constants.h"

#include <atomic>
#include <functional>
#include <vector>

/**
 * @brief Shared data structure for multi-threaded solver execution
 * 
 * This structure holds state that is shared between multiple solver threads.
 * All atomic members are thread-safe for concurrent access.
 */
struct SharedData
{
    Board &max_board;                                    ///< Best board found so far
    std::atomic_llong max_count;                         ///< Maximum number of pieces placed
    std::mutex &mutex;                                   ///< Mutex for protecting shared data
    std::unordered_set<BoardHash> &hashes;               ///< Set of board hashes for duplicate detection
    std::atomic_llong board_count{0};                    ///< Total number of boards analyzed
    std::atomic_llong hash_hit_count{0};                 ///< Number of hash table hits
    std::atomic_bool stop{false};                        ///< Flag to signal threads to stop
    std::function<void(const Board &)> on_board_update = [](const Board &board) {};  ///< Callback invoked when board is updated
    unsigned int hash_length_threshold = eternity2_constants::DEFAULT_HASH_LENGTH_THRESHOLD;  ///< Minimum board size to use hash table
    unsigned long redis_hash_count{0};                  ///< Number of hashes stored in Redis (if used)
    std::atomic_llong pieces_placed{0};                   ///< Current number of pieces placed
    std::atomic_llong milliseconds_since_start{1};      ///< Elapsed time since solver started (milliseconds)
};

/**
 * @brief Find all possible pieces that can be placed at a given index
 * 
 * @param board Current board state
 * @param pieces Available pieces with their availability information
 * @param index Position on the board to check
 * @return Vector of RotatedPiece objects that can be placed at the given index
 */
auto possible_pieces(const Board &board, const std::vector<PieceWAvailability> &pieces, Index index)
    -> std::vector<RotatedPiece>;

/**
 * @brief Solve the Eternity II puzzle using backtracking
 * 
 * This function implements the main solving algorithm. It uses backtracking
 * with constraint propagation to find a valid solution.
 * 
 * @param board Initial board state (will be modified during solving)
 * @param pieces Vector of pieces to place on the board
 * @param shared_data Shared data structure for multi-threaded coordination
 */
void solve_board(Board &board, const std::vector<Piece> &pieces, SharedData &shared_data);