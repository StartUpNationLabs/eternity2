
# glob all the source files
file(GLOB_RECURSE SPDLOG_SOURCES
        "**/*.hpp"
        "**/*.cpp"
        "**/*.h"
        "**/*.c"
        "*.hpp"
        "*.cpp"
        "*.h"
        "*.c"
)

# Declare the library
add_library(spdlog STATIC
        ${SPDLOG_SOURCES}
)


set_target_properties(spdlog PROPERTIES LINKER_LANGUAGE CXX)

# Specify here the include directories exported
# by this library
target_include_directories(spdlog PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}
)
