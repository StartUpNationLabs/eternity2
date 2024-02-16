#define CONFIG_CATCH_MAIN

#include <catch2/catch_all.hpp>
#include "piece/piece.h"
#include "piece_search/piece_search.h"
#include "format/format.h"
#include "piece_loader/piece_loader.h"


TEST_CASE("PIECE load from string", "[load]") {

    std::string csv = "1,1,4,4\n1,4,4,1\n4,4,1,1\n1,1,4,4\n";
    auto pieces = load_from_csv_string(csv);
    REQUIRE(pieces.size() == 4);

};

