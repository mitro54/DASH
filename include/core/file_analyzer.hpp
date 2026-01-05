#pragma once

#include <string>
#include <filesystem>
#include <fstream>
#include <format>
#include <algorithm>
#include <vector>
#include <cstdint>

namespace dais::utils {
    namespace fs = std::filesystem;

    /**
     * @brief Container for metadata extracted from a file or directory.
     * Used by the UI handlers to display rich information in the grid layout.
     */
    struct FileStats {
        bool is_dir = false;        ///< True if path is a directory
        bool is_valid = false;      ///< True if path exists and is accessible
        
        // --- Directory Specifics ---
        size_t item_count = 0;      ///< Number of items (files/dirs) immediately inside the directory

        // --- File Specifics ---
        uintmax_t size_bytes = 0;   ///< File size on disk
        size_t rows = 0;            ///< Total number of lines (newlines)
        
        /** * @brief Dual-purpose metric:
         * - For Text/Code: The character width of the longest line.
         * - For CSV/Data: The number of data columns (comma-separated).
         */
        size_t max_cols = 0;        

        bool is_text = false;       ///< True if heuristics suggest a readable text file
        bool is_csv = false;        ///< True if extension matches .csv or .tsv
        bool is_estimated = false;  ///< True if row count is extrapolated due to file size limits
    };

    // --- Performance Configuration ---
    // Limits to prevent UI freezes when scanning large files on the main thread.
    // In a production environment, file scanning should move to a thread pool.
    constexpr size_t MAX_SCAN_BYTES = 32 * 1024; // Scan max 32KB
    constexpr size_t MAX_SCAN_LINES = 2000;      // Scan max 2000 lines

    /**
     * @brief Analyzes a path to extract metadata (size, row count, type).
     * * Uses extension-based heuristics to determine if a file is text or data.
     * Performs a partial scan to estimate row counts for large files to maintain performance.
     * * @param filename Relative or absolute path to the target.
     * @return FileStats Struct containing the analysis results.
     */
    inline FileStats analyze_path(const std::string& filename) {
        std::error_code ec;
        fs::path p(filename);
        FileStats stats;

        // 1. Validation check
        if (!fs::exists(p, ec)) return stats; 
        stats.is_valid = true;

        // 2. Directory Analysis
        if (fs::is_directory(p, ec)) {
            stats.is_dir = true;
            try {
                // std::distance is linear time; acceptable for typical local dev directories.
                // NOTE: For high-latency network drives, this may need async implementation.
                auto it = fs::directory_iterator(p, fs::directory_options::skip_permission_denied, ec);
                stats.item_count = std::distance(fs::begin(it), fs::end(it));
            } catch (...) { stats.item_count = 0; }
            return stats;
        }

        // 3. File Analysis
        if (fs::is_regular_file(p, ec)) {
            stats.size_bytes = fs::file_size(p, ec);
            
            std::string ext = p.extension().string();

            // Detect Data Files
            stats.is_csv = (ext == ".csv" || ext == ".tsv");

            // Extension-based text detection whitelist
            stats.is_text = (ext == ".txt" || ext == ".cpp" || ext == ".hpp" || 
                             ext == ".py"  || ext == ".md"  || ext == ".cmake" ||
                             ext == ".json"|| ext == ".log" || ext == ".sh" ||
                             ext == ".js"  || ext == ".ts"  || ext == ".html" ||
                             ext == ".css" || ext == ".xml" || ext == ".yml" || 
                             ext == ".ini" || ext == ".conf"|| stats.is_csv);

            // Optimization: Skip heavy I/O scanning if empty or binary
            if (!stats.is_text || stats.size_bytes == 0) return stats;

            // 4. Content Scanning
            std::ifstream file(p);
            if (!file.is_open()) return stats;

            size_t rows = 0;
            size_t bytes_read = 0;
            std::string line;

            // --- CSV/Data Column Counting ---
            // We read the first line specifically to count delimiters for data files.
            if (stats.is_csv) {
                if (std::getline(file, line)) {
                    char delimiter = (ext == ".tsv") ? '\t' : ',';
                    // Columns = Delimiters + 1
                    stats.max_cols = std::count(line.begin(), line.end(), delimiter) + 1;
                    
                    // Critical: Reset file stream state to beginning for the row counter below
                    file.clear(); 
                    file.seekg(0);
                }
            }
            
            // --- Row Counting Loop ---
            // Scan with safety caps to ensure shell responsiveness
            while (bytes_read < MAX_SCAN_BYTES && rows < MAX_SCAN_LINES && std::getline(file, line)) {
                rows++;
                size_t line_bytes = line.size() + 1; // +1 for newline approximation
                bytes_read += line_bytes;
                
                // For non-CSV text files, 'max_cols' represents the widest line width (characters)
                if (!stats.is_csv) {
                    if (line.size() > stats.max_cols) stats.max_cols = line.size();
                }
            }

            // 5. Estimation Logic
            // If we hit the read limit before EOF, extrapolate total rows based on average byte/row ratio.
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