#pragma once
#include "core/file_analyzer.hpp"
#include <string>
#include <string_view>
#include <vector>
#include <sstream>
#include <filesystem>
#include <algorithm>
#include <format>
#include <sys/ioctl.h>
#include <unistd.h>
#include <cctype> 

namespace dash::core::handlers {

    // --- THEME CONFIGURATION ---
    struct Theme {
        static constexpr auto RESET     = "\x1b[0m";
        static constexpr auto STRUCTURE = "\x1b[38;5;240m"; // Dark Gray (Borders, Parens)
        static constexpr auto UNIT      = "\x1b[38;5;109m"; // Sage Blue (KB, MB, DIR)
        static constexpr auto VALUE     = "\x1b[0m";        // Default White (Numbers)
        static constexpr auto ESTIMATE  = "\x1b[38;5;139m"; // Muted Purple (~)
    };

    // --- HELPERS ---

    inline int get_terminal_width() {
        struct winsize w;
        if (ioctl(STDOUT_FILENO, TIOCGWINSZ, &w) == -1) return 80;
        return w.ws_col;
    }

    inline size_t get_visible_length(std::string_view s) {
        size_t len = 0;
        bool in_esc_seq = false;
        for (char c : s) {
            if (c == '\x1b') in_esc_seq = true;
            else if (in_esc_seq) {
                if (std::isalpha(c)) in_esc_seq = false;
            } else {
                len++;
            }
        }
        return len;
    }

    inline std::string strip_ansi(std::string_view s) {
        std::string result;
        result.reserve(s.size());
        bool in_esc_seq = false;
        for (char c : s) {
            if (c == '\x1b') in_esc_seq = true;
            else if (in_esc_seq) {
                if (std::isalpha(c)) in_esc_seq = false;
            } else {
                result += c;
            }
        }
        return result;
    }

    // --- FORMATTERS ---
    
    inline std::string fmt_size(uintmax_t bytes) {
        if (bytes < 1024) 
            return std::format("{}{}{}{}", Theme::VALUE, bytes, Theme::UNIT, "B");
        if (bytes < 1024 * 1024) 
            return std::format("{}{:.1f}{}{}", Theme::VALUE, bytes/1024.0, Theme::UNIT, "KB");
        return std::format("{}{:.1f}{}{}", Theme::VALUE, bytes/(1024.0*1024.0), Theme::UNIT, "MB");
    }

    inline std::string fmt_rows(size_t rows, bool estimated) {
        std::string tilde = estimated ? std::string(Theme::ESTIMATE) + "~" : "";
        if (rows > 1000000) 
            return std::format("{}{}{:.1f}{}{}", tilde, Theme::VALUE, rows/1000000.0, Theme::UNIT, "M R");
        if (rows > 1000) 
            return std::format("{}{}{:.1f}{}{}", tilde, Theme::VALUE, rows/1000.0, Theme::UNIT, "k R");
        return std::format("{}{}{}{}{}", tilde, Theme::VALUE, rows, Theme::UNIT, "R");
    }

    // --- HANDLERS ---

    inline std::string handle_generic(std::string_view raw_output) {
        return std::string(raw_output);
    }

    inline std::string handle_ls(std::string_view raw_output, const std::filesystem::path& cwd) {
        std::stringstream ss{std::string(raw_output)};
        std::string token;
        std::vector<std::string> original_items;
        
        while (ss >> token) original_items.push_back(token);
        if (original_items.empty()) return "";

        struct GridItem {
            std::string display_string;
            size_t visible_len;
        };
        std::vector<GridItem> grid_items;
        bool first_token = true;

        for (const auto& item_raw : original_items) {
            std::string clean_name = strip_ansi(item_raw);
            
            if (first_token && clean_name == "ls") { first_token = false; continue; }
            first_token = false;
            if (clean_name.empty() || clean_name == "." || clean_name == "..") continue;

            std::filesystem::path full_path = cwd / clean_name;
            auto stats = dash::utils::analyze_path(full_path.string());

            std::string display;

            if (stats.is_valid) {
                if (stats.is_dir) {
                    // DIRECTORY: "Name (DIR: 5 items)"
                    // Fixed: Literal ')' is now embedded in format string after the color code
                    display = std::format("{} {}({}{}: {}{} {}{}{})", 
                        item_raw, 
                        Theme::STRUCTURE, // Color for '('
                        Theme::UNIT, "DIR", 
                        Theme::VALUE, stats.item_count, 
                        Theme::UNIT, "items", 
                        Theme::STRUCTURE // Color for ')'
                    ); 
                } else {
                    // FILE: "Name (10KB, 50R, 80C)"
                    std::string info;
                    std::string size_str = fmt_size(stats.size_bytes);

                    if (stats.is_text) {
                        std::string row_str = fmt_rows(stats.rows, stats.is_estimated);
                        info = std::format("{}{}, {}{}, {}{}{}{}", 
                            size_str, 
                            Theme::STRUCTURE, 
                            row_str,
                            Theme::STRUCTURE,
                            Theme::VALUE, stats.max_cols, Theme::UNIT, "C");
                    } else {
                        info = size_str;
                    }

                    // Fixed: Literal ')' embedded in format string
                    display = std::format("{} {}({}{})", 
                        item_raw, 
                        Theme::STRUCTURE, // Color for '('
                        info, 
                        Theme::STRUCTURE // Color for ')'
                    );
                }
            } else {
                display = item_raw;
            }

            display += Theme::RESET;
            size_t vlen = get_visible_length(display);
            grid_items.push_back({display, vlen});
        }

        if (grid_items.empty()) return "";

        int term_width = get_terminal_width() - 2; 
        if (term_width < 10) term_width = 10; 

        std::string final_output;
        final_output.reserve(raw_output.size() * 5); 

        int current_line_len = 0;

        for (const auto& item : grid_items) {
            size_t cell_len = item.visible_len + 4; 
            int gap = (current_line_len > 0) ? 1 : 0;

            if (current_line_len + gap + cell_len > (size_t)term_width) {
                if (current_line_len > 0) final_output += "\r\n";
                // Box borders
                final_output += std::format("{}|{} {} {}|{}", Theme::STRUCTURE, Theme::RESET, item.display_string, Theme::STRUCTURE, Theme::RESET);
                current_line_len = cell_len;
            } 
            else {
                if (current_line_len > 0) {
                    final_output += " "; 
                    current_line_len += 1;
                }
                final_output += std::format("{}|{} {} {}|{}", Theme::STRUCTURE, Theme::RESET, item.display_string, Theme::STRUCTURE, Theme::RESET);
                current_line_len += cell_len;
            }
        }

        return final_output;
    }
}