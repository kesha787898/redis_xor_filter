cmake_minimum_required(VERSION 3.20)
project(xor_filter_module C)

set(CMAKE_C_STANDARD 99)

add_library(xor_filter SHARED
        src/main.c
        src/xor.c
        src/murmur3.c
        src/tools/stack.h
        src/tools/stack.c
        src/tools/pair.h
        src/tools/queue.h
        src/tools/queue.c
        src/tools/hashes.h
        src/tools/hashes.c
        src/tools/bucket.c
        src/tools/bucket.h
)

set_target_properties(xor_filter PROPERTIES POSITION_INDEPENDENT_CODE ON)

set_target_properties(xor_filter PROPERTIES PREFIX "" SUFFIX ".so")

target_link_libraries(xor_filter PRIVATE m)

target_include_directories(xor_filter PRIVATE
        ${CMAKE_CURRENT_SOURCE_DIR}
        ${CMAKE_CURRENT_SOURCE_DIR}/src
)