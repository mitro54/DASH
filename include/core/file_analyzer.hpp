#pragma once
#include <string>
#include <filesystem>
#include <fstream>
#include <format>
#include <algorithm>
#include <vector>
#include <cstdint>

namespace dash::utils {
    namespace fs = std::filesystem;

    struct FileStats {
        bool is_dir = false;
        bool is_valid = false;
        
        // For Directories
        size_t item_count = 0;

        // For Files
        uintmax_t size_bytes = 0;
        size_t rows = 0;
        size_t max_cols = 0;
        bool is_text = false;
        bool is_estimated = false;
    };

    // Configuration for performance limits
    constexpr size_t MAX_SCAN_BYTES = 32 * 1024; // 32KB Limit
    constexpr size_t MAX_SCAN_LINES = 2000;      // 2000 Lines Limit

    inline FileStats analyze_path(const std::string& filename) {
        std::error_code ec;
        fs::path p(filename);
        FileStats stats;

        if (!fs::exists(p, ec)) return stats; 
        stats.is_valid = true;

        // 1. Handle Directory
        if (fs::is_directory(p, ec)) {
            stats.is_dir = true;
            try {
                auto it = fs::directory_iterator(p, fs::directory_options::skip_permission_denied, ec);
                stats.item_count = std::distance(fs::begin(it), fs::end(it));
            } catch (...) { stats.item_count = 0; }
            return stats;
        }

        // 2. Handle Regular File
        if (fs::is_regular_file(p, ec)) {
            stats.size_bytes = fs::file_size(p, ec);
            
            std::string ext = p.extension().string();
            stats.is_text = (ext == ".txt" || ext == ".cpp" || ext == ".hpp" || 
                             ext == ".py"  || ext == ".md"  || ext == ".cmake" ||
                             ext == ".json" || ext == ".csv" || ext == ".log");

            if (!stats.is_text || stats.size_bytes == 0) return stats;

            // 3. Scan Content
            std::ifstream file(p);
            if (!file.is_open()) return stats;

            size_t rows = 0;
            size_t bytes_read = 0;
            std::string line;
            
            while (bytes_read < MAX_SCAN_BYTES && rows < MAX_SCAN_LINES && std::getline(file, line)) {
                rows++;
                size_t line_bytes = line.size() + 1; 
                bytes_read += line_bytes;
                if (line.size() > stats.max_cols) stats.max_cols = line.size();
            }

            // Estimation
            if (bytes_read >= stats.size_bytes || file.eof()) {
                stats.rows = rows;
            } else {
                double ratio = (bytes_read > 0) ? (static_cast<double>(stats.size_bytes) / bytes_read) : 1.0;
                stats.rows = static_cast<size_t>(rows * ratio);
                stats.is_estimated = true;
            }
        }
        return stats;
    }
}