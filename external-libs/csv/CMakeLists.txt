

# Declare the library
add_library(csv STATIC
        csv.h
)


set_target_properties(csv PROPERTIES LINKER_LANGUAGE CXX)

# Specify here the include directories exported
# by this library
target_include_directories(csv PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}
)
