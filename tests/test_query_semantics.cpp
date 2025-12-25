#define CONFIG_CATCH_MAIN

#include <catch2/catch_all.hpp>
#include "piece/piece.h"
#include "piece_search/piece_search.h"

// These tests specifically target the bug in solver_v2 that broke constraint satisfaction
// by using POSITIVE queries instead of NEGATIVE queries for wall exclusion

TEST_CASE("Query Semantics - NEGATIVE query excludes pieces WITH walls", "[query_semantics]") {
    // Create a piece with walls on ALL edges - will be excluded in ALL rotations
    Piece wall_piece = make_piece(WALL, WALL, WALL, WALL);
    auto pieces = create_pieces_with_availability({wall_piece});

    // NEGATIVE query: exclude pieces with wall on right
    // This is what solver_v2 got WRONG - it used POSITIVE instead
    Query negative_wall = {FULLWALL, RIGHT_MASK, QueryType::NEGATIVE};
    auto results = match_piece_mask({negative_wall}, pieces);

    // Should return EMPTY - the piece has walls on all edges
    REQUIRE(results.empty());
}

TEST_CASE("Query Semantics - NEGATIVE query includes pieces WITHOUT walls", "[query_semantics]") {
    // Create a piece without a wall on the right (non-wall value)
    Piece no_wall = make_piece(1, 2, 3, 4);  // 2 is not WALL (0xFFFF)
    auto pieces = create_pieces_with_availability({no_wall});

    // NEGATIVE query: exclude pieces with wall on right
    Query negative_wall = {FULLWALL, RIGHT_MASK, QueryType::NEGATIVE};
    auto results = match_piece_mask({negative_wall}, pieces);

    // Should return the piece (in all rotations) - it doesn't have a wall on right
    REQUIRE(results.size() > 0);

    // Verify all returned pieces don't have walls on the right
    for (const auto& r : results) {
        Piece rotated = rotate_piece_right(r.piece, r.rotation);
        PiecePart right_part = get_piece_part(rotated, RIGHT_MASK);
        REQUIRE(right_part != WALL);
    }
}

TEST_CASE("Query Semantics - POSITIVE query matches exact pattern", "[query_semantics]") {
    Piece target_piece = make_piece(5, 6, 7, 8);
    auto pieces = create_pieces_with_availability({target_piece});

    // POSITIVE query: must match this exact pattern
    Query positive_match = {make_piece(5, 6, 7, 8), UP_MASK | RIGHT_MASK | DOWN_MASK | LEFT_MASK, QueryType::POSITIVE};
    auto results = match_piece_mask({positive_match}, pieces);

    // Should return exactly one result (no rotation needed)
    REQUIRE(results.size() == 1);
    REQUIRE(results[0].rotation == 0);
}

TEST_CASE("Query Semantics - Combined POSITIVE and NEGATIVE queries", "[query_semantics]") {
    // Simulate an interior cell with neighbors on all sides
    // The valid piece must:
    // 1. Match the neighbor patterns (POSITIVE query)
    // 2. NOT have walls on any edge (NEGATIVE queries)

    Piece valid_piece = make_piece(5, 6, 7, 8);       // No walls, matches pattern
    Piece invalid_wall = make_piece(5, WALL, 7, 8);   // Has wall on right - INVALID for interior
    Piece invalid_pattern = make_piece(1, 2, 3, 4);   // No walls but doesn't match pattern

    auto pieces = create_pieces_with_availability({valid_piece, invalid_wall, invalid_pattern});

    std::vector<Query> queries = {
        // POSITIVE: must match neighbor patterns
        {make_piece(5, 6, 7, 8), UP_MASK | RIGHT_MASK | DOWN_MASK | LEFT_MASK, QueryType::POSITIVE},
        // NEGATIVE: must NOT have walls (interior cell)
        {FULLWALL, UP_MASK, QueryType::NEGATIVE},
        {FULLWALL, RIGHT_MASK, QueryType::NEGATIVE},
        {FULLWALL, DOWN_MASK, QueryType::NEGATIVE},
        {FULLWALL, LEFT_MASK, QueryType::NEGATIVE}
    };

    auto results = match_piece_mask(queries, pieces);

    // Should only return valid_piece, not invalid_wall or invalid_pattern
    REQUIRE(results.size() == 1);
    REQUIRE(results[0].piece == valid_piece);
    REQUIRE(results[0].rotation == 0);
}

TEST_CASE("Query Semantics - Edge cell requires wall on boundary", "[query_semantics]") {
    // Edge cells MUST have walls on the board boundary
    Piece edge_piece = make_piece(WALL, 2, 3, 4);     // Wall on top (correct for top edge)
    Piece interior_piece = make_piece(1, 2, 3, 4);    // No wall on top (invalid for top edge)

    auto pieces = create_pieces_with_availability({edge_piece, interior_piece});

    // Edge cell: POSITIVE query requiring wall on top
    Query require_wall = {make_piece(WALL, 0, 0, 0), UP_MASK, QueryType::POSITIVE};
    auto results = match_piece_mask({require_wall}, pieces);

    // Only edge_piece should match
    bool found_edge = false;
    bool found_interior = false;
    for (const auto& r : results) {
        Piece rotated = rotate_piece_right(r.piece, r.rotation);
        PiecePart top_part = get_piece_part(rotated, UP_MASK);

        if (r.piece == edge_piece && top_part == WALL) {
            found_edge = true;
        }
        if (r.piece == interior_piece && top_part == WALL) {
            found_interior = true;
        }
    }

    REQUIRE(found_edge);
    REQUIRE_FALSE(found_interior);
}

TEST_CASE("Query Semantics - Multiple wall constraints", "[query_semantics]") {
    // Test piece with walls - will be excluded in rotations where walls align with constraints
    Piece corner_piece = make_piece(WALL, WALL, WALL, WALL);  // Walls on all sides - always excluded
    Piece edge_piece = make_piece(WALL, 5, 6, 7);             // Wall only on top
    Piece interior = make_piece(1, 2, 3, 4);                  // No walls

    auto pieces = create_pieces_with_availability({corner_piece, edge_piece, interior});

    // NEGATIVE queries: exclude pieces with walls on right and down
    std::vector<Query> queries = {
        {FULLWALL, RIGHT_MASK, QueryType::NEGATIVE},
        {FULLWALL, DOWN_MASK, QueryType::NEGATIVE}
    };

    auto results = match_piece_mask(queries, pieces);

    // corner_piece has walls everywhere - should NEVER appear
    // edge_piece has one wall - might appear in some rotations
    // interior has no walls - should appear in all rotations
    bool found_corner = false;
    bool found_interior = false;

    for (const auto& r : results) {
        if (r.piece == corner_piece) found_corner = true;
        if (r.piece == interior) found_interior = true;
    }

    REQUIRE_FALSE(found_corner);
    REQUIRE(found_interior);  // Interior piece should definitely be included
}

TEST_CASE("Query Semantics - Wall exclusion preserves rotations", "[query_semantics]") {
    // A piece might have a wall in one rotation but not another
    Piece piece_with_wall_on_top = make_piece(WALL, 1, 2, 3);
    auto pieces = create_pieces_with_availability({piece_with_wall_on_top});

    // NEGATIVE query: exclude pieces with wall on LEFT
    Query negative_left_wall = {FULLWALL, LEFT_MASK, QueryType::NEGATIVE};
    auto results = match_piece_mask({negative_left_wall}, pieces);

    // The piece has WALL on top, so:
    // - Rotation 0: top=WALL, right=1, down=2, left=3  -> left=3 (OK)
    // - Rotation 1: top=3, right=WALL, down=1, left=2  -> left=2 (OK)
    // - Rotation 2: top=2, right=3, down=WALL, left=1  -> left=1 (OK)
    // - Rotation 3: top=1, right=2, down=3, left=WALL  -> left=WALL (EXCLUDED)

    // Should have 3 valid rotations (0, 1, 2) but not rotation 3
    REQUIRE(results.size() == 3);

    for (const auto& r : results) {
        REQUIRE(r.rotation != 3);  // Rotation 3 should be excluded
        Piece rotated = rotate_piece_right(r.piece, r.rotation);
        PiecePart left_part = get_piece_part(rotated, LEFT_MASK);
        REQUIRE(left_part != WALL);
    }
}

TEST_CASE("Query Semantics - Empty mask with POSITIVE query", "[query_semantics]") {
    // Edge case: POSITIVE query with no mask should match all pieces
    Piece any_piece = make_piece(1, 2, 3, 4);
    auto pieces = create_pieces_with_availability({any_piece});

    Query positive_no_mask = {make_piece(0, 0, 0, 0), EMPTY, QueryType::POSITIVE};
    auto results = match_piece_mask({positive_no_mask}, pieces);

    // Empty mask means no constraint, so all rotations should be included
    REQUIRE(results.size() == 4);  // All 4 rotations
}

TEST_CASE("Query Semantics - Regression test for solver_v2 bug", "[query_semantics]") {
    // This is the EXACT scenario that broke in solver_v2
    // Interior position with neighbor on the right

    Piece neighbor_piece = make_piece(1, 2, 3, 4);
    Piece candidate_with_wall = make_piece(5, WALL, 7, 8);  // Invalid - has wall where neighbor exists
    Piece candidate_valid = make_piece(5, 3, 7, 8);         // Valid - matches neighbor's left edge

    auto pieces = create_pieces_with_availability({candidate_with_wall, candidate_valid});

    // This is what the CORRECT implementation does (from solver/solver.cpp:33)
    // if (neighbors.right != nullptr) {
    //     queries.emplace_back(FULLWALL, RIGHT_MASK, QueryType::NEGATIVE);
    // }

    std::vector<Query> queries = {
        // Get the neighbor's left edge value (assume it's 3)
        {make_piece(0, 3, 0, 0), RIGHT_MASK, QueryType::POSITIVE},
        // Exclude pieces with walls on the right (NEGATIVE!)
        {FULLWALL, RIGHT_MASK, QueryType::NEGATIVE}
    };

    auto results = match_piece_mask(queries, pieces);

    // Should ONLY include candidate_valid, NOT candidate_with_wall
    bool found_wall_piece = false;
    bool found_valid_piece = false;

    for (const auto& r : results) {
        if (r.piece == candidate_with_wall) found_wall_piece = true;
        if (r.piece == candidate_valid) found_valid_piece = true;
    }

    // This is the KEY test that would have caught the solver_v2 bug
    REQUIRE_FALSE(found_wall_piece);  // MUST NOT include piece with wall
    REQUIRE(found_valid_piece);       // MUST include valid piece
}
