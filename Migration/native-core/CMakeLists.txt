cmake_minimum_required(VERSION 3.20)
project(louis_ai_native_core VERSION 0.1.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

add_library(louis_ai_engine STATIC
    src/engine_facade.cpp
)

target_include_directories(louis_ai_engine
    PUBLIC
        ${CMAKE_CURRENT_SOURCE_DIR}/include
)
