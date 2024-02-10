

# Declare the library
add_library(CLI11 STATIC
        CLI11.hpp
)


set_target_properties(CLI11 PROPERTIES LINKER_LANGUAGE CXX)

# Specify here the include directories exported
# by this library
target_include_directories(CLI11 PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}
)


