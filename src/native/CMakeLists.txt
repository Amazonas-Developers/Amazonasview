cmake_minimum_required(VERSION 3.14)
project(window_native LANGUAGES CXX)


set(PYBIND11_FINDPYTHON ON)
find_package(pybind11 REQUIRED)

set(SOURCES
    capture.cpp
    bindings.cpp   # Punto de entrada pybind11
)


pybind11_add_module(window_native ${SOURCES})
target_compile_features(window_native PRIVATE cxx_std_17)