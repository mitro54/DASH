#include "core/engine.hpp"
#include <filesystem>
#include <iostream>
#include <string>

namespace fs = std::filesystem;

int main() {
    dash::core::Engine engine;

    // Get the baked-in absolute path to the project root
    // This allows you to alias dash='.../build/DASH' and run it from anywhere.
    fs::path project_root = DASH_ROOT;
    
    // Construct the path to the scripts folder
    fs::path scripts_path = project_root / "src" / "py_scripts";

    // Verify it exists (Sanity check to prevent Segfaults)
    if (!fs::exists(scripts_path)) {
        std::cerr << "Error: Could not find Python scripts at: " << scripts_path << "\n";
        return 1;
    }

    std::string path_str = scripts_path.string();

    // 4. Load
    engine.load_configuration(path_str);
    engine.load_extensions(path_str);
    engine.run();

    return 0;
}