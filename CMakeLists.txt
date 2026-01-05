cmake_minimum_required(VERSION 3.20)

project(DASH)
include_directories(include)
include(FetchContent)

# Settings (Standard C++20)
set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED True)
set(CMAKE_CXX_EXTENSIONS OFF)

# Pass the absolute project path to C++ code.
# This ensures DASH finds 'src/py_scripts' even if you run it via an alias or from another folder.
add_compile_definitions(DASH_ROOT="${CMAKE_SOURCE_DIR}")

# Fetch pybind11
FetchContent_Declare(
  pybind11
  GIT_REPOSITORY https://github.com/pybind/pybind11.git
  GIT_TAG        v3.0.1
)
FetchContent_MakeAvailable(pybind11)

# Find python
# Relaxed version requirement slightly to ensure compatibility if you update Python later
find_package(Python 3.10 COMPONENTS Interpreter Development REQUIRED)

# THE INGREDIENTS (List every .cpp file you create here)
add_executable(DASH 
    src/main.cpp
    src/core/engine.cpp
    src/core/session.cpp
    # If you add a new file, just add a new line here
)

# Tells CMake where to find your header files (.hpp)
target_include_directories(DASH PRIVATE include)

# THE GARNISH (Libraries)
target_link_libraries(DASH PRIVATE pybind11::embed)

# Linux-Specific Linking
if(CMAKE_SYSTEM_NAME STREQUAL "Linux")
    target_link_libraries(DASH PRIVATE util pthread)
endif()

# Install the Main Executable
install(TARGETS DASH DESTINATION bin)