"""
DAIS Database Handler Module.

This script bridges the C++ Engine with Python's database capabilities.
It is designed to be:
1.  **Robust**: Handles large datasets via streaming to avoid OOM.
2.  **Flexible**: Supports SQLite and DuckDB (expandable to others).
3.  **User-Centric**: Respects user's PAGER preferences and supports exports.

Protocol:
- Input: Receives a raw query string from C++.
- Output: Returns a JSON string with {"status", "action", "data", "pager"}.
"""

import sys
import os
import json
import csv
import tempfile
import sqlite3

# Optional: DuckDB Support
try:
    import duckdb
    HAS_DUCKDB = True
except ImportError:
    HAS_DUCKDB = False


def get_connection(db_type, db_source):
    """
    Factory method to establish a database connection.
    
    Args:
        db_type (str): 'sqlite' or 'duckdb'.
        db_source (str): Path to the database file or connection string.
        
    Returns:
        Connection object (PEP-249 compliant).
        
    Raises:
        ImportError: If required driver is missing.
    """
    if db_type == "duckdb":
        if not HAS_DUCKDB:
            raise ImportError(
                "DuckDB is configured but not installed. "
                "Please run 'pip install duckdb' to use this feature."
            )
        return duckdb.connect(db_source)
    else:
        # Default to SQLite
        # Note: We rely on sqlite3 standard library which is always available.
        return sqlite3.connect(db_source)


def run_query(query, db_type, db_source):
    """
    Executes the query and formats the result for the specific action type.
    
    Why Streaming?
    Loading 1M rows into memory with fetchall() creates huge latency and 
    Risk of OOM. We use a generator to stream rows when writing to files.
    """
    flags = {
        "json": False,
        "csv": False,
        "no_limit": False
    }

    # 1. Parse Flags via Regex/Replacement
    # This allows flags to appear in any order.
    import re
    
    # Extract --output <filename> first
    output_match = re.search(r'--output\s+([^\s]+)', query)
    if output_match:
        flags["output"] = output_match.group(1)
        # Flatten the query by removing the matched substring
        query = query[:output_match.start()] + query[output_match.end():]
    else:
        flags["output"] = None

    # Helper to pop boolean flags anywhere in string
    def pop_flag(q, flag):
        if flag in q:
            return q.replace(flag, ""), True
        return q, False

    query, flags["json"] = pop_flag(query, "--json")
    query, flags["csv"] = pop_flag(query, "--csv")
    query, flags["no_limit"] = pop_flag(query, "--no-limit")

    clean_query = query.strip()
    
    # 2. Safety Limit
    # If no explicit limit override is provided, we force a LIMIT to prevent
    # accidental valid queries from freezing the terminal.
    if not flags["json"] and not flags["csv"] and not flags["no_limit"]:
        low_query = clean_query.lower()
        if "limit" not in low_query:
            clean_query += " LIMIT 1000"

    try:
        conn = get_connection(db_type, db_source)
        cursor = conn.cursor()
        cursor.execute(clean_query)
        
        # Extract headers if available
        headers = [d[0] for d in cursor.description] if cursor.description else []

        # 3. Generator for Streaming
        # This keeps memory usage constant (O(1)) regardless of result size.
        def row_generator():
            while True:
                # Fetch in batches of 1000 to reduce IPC overhead
                batch = cursor.fetchmany(1000)
                if not batch:
                    break
                for row in batch:
                    yield row

        # --- EXPORT ACTIONS ---
        
        if flags["json"]:
            # Action: Export to JSON
            # Decide target: User file OR Temp file
            if flags.get("output"):
                target_path = flags["output"]
                action = "print"
                pager = None
                message = f"Saved JSON to: {target_path}"
            else:
                fd, target_path = tempfile.mkstemp(prefix="dais_db_", suffix=".json", text=True)
                os.close(fd) # Close handle, open as needed below
                action = "page"
                pager = "cat"
                message = target_path # Data for page action is the path

            # Write Data
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write("[\n")
                first = True
                for row in row_generator():
                    if not first:
                        f.write(",\n")
                    item = dict(zip(headers, row))
                    f.write(json.dumps(item, default=str))
                    first = False
                f.write("\n]")
            
            conn.close()
            return json.dumps({
                "status": "success", 
                "action": action, 
                "data": message, 
                "pager": pager
            })

        if flags["csv"]:
            # Action: Export to CSV
            if flags.get("output"):
                target_path = flags["output"]
                action = "print"
                pager = None
                message = f"Saved CSV to: {target_path}"
            else:
                fd, target_path = tempfile.mkstemp(prefix="dais_db_", suffix=".csv", text=True)
                os.close(fd)
                action = "page"
                pager = "cat"
                message = target_path

            # Write Data
            with open(target_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for row in row_generator():
                    writer.writerow(row)
            
            conn.close()
            return json.dumps({
                "status": "success", 
                "action": action, 
                "data": message, 
                "pager": pager
            })

        # --- VIEW ACTION (Table) ---
        
        # For the interactive table view, we revert to fetchall() currently.
        # Why? Aligning columns (Pretty Printing) requires global knowledge of max width.
        # Since we enforce LIMIT 1000 by default, this is safe in memory (kB size).
        # If user passes --no-limit, they accept the memory/latency cost.
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            return json.dumps({
                "status": "success", 
                "action": "print", 
                "data": "No results."
            })

        # Calculate column widths
        widths = [len(h) for h in headers]
        str_rows = [] # Cache stringified version
        
        for row in rows:
            # Handle NULLs gracefully
            s_row = [str(cell) if cell is not None else "NULL" for cell in row]
            str_rows.append(s_row)
            for i, cell in enumerate(s_row):
                widths[i] = max(widths[i], len(cell))

        # Formatter
        def format_line(r, w_list):
            return " | ".join(f"{c:<{w}}" for c, w in zip(r, w_list))

        separator = "-+-".join("-" * w for w in widths)
        header_line = format_line(headers, widths)

        output_lines = [header_line, separator]
        for row in str_rows:
            output_lines.append(format_line(row, widths))

        full_output = "\n".join(output_lines)
        
        # Decision: Print vs Page
        # If the output is longer than standard terminal height (~50),
        # or if the user requests it, we use the PAGER.
        if len(output_lines) > 50:
            fd, path = tempfile.mkstemp(prefix="dais_db_", suffix=".txt", text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(full_output)
            
            # Detect User Preference
            # Default to 'less -S' (chop long lines) for best table viewing experience.
            user_pager = os.environ.get("PAGER", "less -S")
            
            return json.dumps({
                "status": "success", 
                "action": "page", 
                "data": path, 
                "pager": user_pager
            })
        else:
            return json.dumps({
                "status": "success", 
                "action": "print", 
                "data": full_output
            })

    except Exception as e:
        return json.dumps({
            "status": "error", 
            "message": str(e)
        })


def handle_command(cmd_input):
    """
    Main entry point invoked by C++ engine.
    
    Args:
        cmd_input (str): The string following ':db ' typed by the user.
        
    Returns:
        str: JSON string response.
    """
    try:
        # Import config dynamically to allow hot-ish reloading (if supported by Python logic)
        # and to access the user's settings.
        try:
            import config
        except ImportError:
            return json.dumps({
                "status": "error", 
                "message": "Configuration Error: Could not import 'config.py'."
            })

        query = cmd_input.strip()

        # 1. Expand Saved Queries
        # This allows users to alias complex SQL to simple keys.
        if hasattr(config, "DB_QUERIES") and isinstance(config.DB_QUERIES, dict):
            if query in config.DB_QUERIES:
                query = config.DB_QUERIES[query]

        # 2. Get Connection Details
        db_type = getattr(config, "DB_TYPE", "sqlite")
        db_source = getattr(config, "DB_SOURCE", ":memory:")

        return run_query(query, db_type, db_source)

    except Exception as e:
         return json.dumps({
            "status": "error", 
            "message": f"Unexpected Handler Error: {str(e)}"
        })
