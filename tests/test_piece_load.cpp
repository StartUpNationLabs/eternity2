#define CONFIG_CATCH_MAIN

#include <catch2/catch_all.hpp>
#include "solvers/common/types.h"
#include "solvers/common/piece_utils.h"
#include "solvers/v1/piece_search/piece_search.h"
#include "solvers/v1/format/format.h"
#include "solvers/common/piece_loader.h"

using namespace eternity2_common;

TEST_CASE("Piece load from string", "[load]") {

    std::string csv = "1,1,4,4\n1,4,4,1\n4,4,1,1\n1,1,4,4\n";
    auto pieces = load_from_csv_string(csv);
    REQUIRE(pieces.size() == 4);

};

