"""
DAIS Database Handler Module.

This script bridges the C++ Engine with Python's database capabilities.
It is designed to be:
1.  **Robust**: Handles large datasets via streaming to avoid OOM.
2.  **Flexible**: Uses an Adapter pattern for easy database extension.
3.  **Context-Aware**: Reads .env files from the current working directory.
"""

import sys
import os
import json
import csv
import tempfile
import sqlite3
import abc

# =============================================================================
# UTILITIES
# =============================================================================

def load_env_file(cwd):
    """
    Locates and parses the nearest .env file by traversing up the directory tree.
    Priority: 
    1. Current Directory
    2. Parent Directories (recursive)
    3. Stops at User Home or Filesystem Root
    """
    def parse_env(path):
        env_vars = {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        value = value.strip()
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            value = value[1:-1]
                        env_vars[key.strip()] = value
        except Exception:
            pass
        return env_vars

    current = os.path.abspath(cwd)
    user_home = os.path.abspath(os.path.expanduser("~"))
    root = os.path.abspath(os.sep)

    while True:
        env_path = os.path.join(current, ".env")
        if os.path.exists(env_path):
            return parse_env(env_path)
            
        # Stop guards
        if current == user_home or current == root:
            break
            
        parent = os.path.dirname(current)
        if parent == current: # Infinite loop guard for OS root
            break
        current = parent
        
    return {}

# =============================================================================
# ADAPTER INTERFACE
# =============================================================================

class DBAdapter(abc.ABC):
    @abc.abstractmethod
    def connect(self, source, **kwargs):
        """Establishes connection to the database."""
        pass

    @abc.abstractmethod
    def execute(self, query):
        """Executes a query and returns cursor."""
        pass
        
    @abc.abstractmethod
    def close(self):
        """Closes the connection."""
        pass

# =============================================================================
# ADAPTER IMPLEMENTATIONS
# =============================================================================

class SqliteAdapter(DBAdapter):
    def __init__(self):
        self.conn = None
        self.cursor = None

    def connect(self, source, **kwargs):
        self.conn = sqlite3.connect(source)
        self.cursor = self.conn.cursor()

    def execute(self, query):
        self.cursor.execute(query)
        return self.cursor

    def close(self):
        if self.conn:
            self.conn.close()

class DuckDbAdapter(DBAdapter):
    def __init__(self):
        self.conn = None
    
    def connect(self, source, **kwargs):
        try:
            import duckdb
        except ImportError:
            raise ImportError("MISSING_PKG:duckdb")
            
        self.conn = duckdb.connect(source)

    def execute(self, query):
        # DuckDB's execute returns the connection itself which acts as a cursor
        return self.conn.execute(query)

    def close(self):
        # DuckDB usually auto-closes, but we can be explicit
        if self.conn:
            self.conn.close()

class PostgresAdapter(DBAdapter):
    def __init__(self):
        self.conn = None
        self.cursor = None

    def connect(self, source, **kwargs):
        try:
            import psycopg2
        except ImportError:
            raise ImportError("MISSING_PKG:psycopg2-binary")
        
        # Map env vars DB_HOST -> host, etc.
        # Common libpq args: host, port, user, password, dbname
        connect_args = {}
        if "DB_HOST" in kwargs: connect_args["host"] = kwargs["DB_HOST"]
        if "DB_PORT" in kwargs: connect_args["port"] = kwargs["DB_PORT"]
        if "DB_USER" in kwargs: connect_args["user"] = kwargs["DB_USER"]
        if "DB_PASS" in kwargs: connect_args["password"] = kwargs["DB_PASS"]
        if "DB_NAME" in kwargs: connect_args["dbname"] = kwargs["DB_NAME"]
        
        # Fallback: if 'source' looks like a DSN "postgresql://...", use it
        if "://" in source:
             self.conn = psycopg2.connect(source)
        else:
             self.conn = psycopg2.connect(**connect_args)
             
        self.cursor = self.conn.cursor()

    def execute(self, query):
        self.cursor.execute(query)
        return self.cursor

    def close(self):
        if self.conn: self.conn.close()

class MySqlAdapter(DBAdapter):
    def __init__(self):
        self.conn = None
        self.cursor = None

    def connect(self, source, **kwargs):
        try:
            import mysql.connector
        except ImportError:
            raise ImportError("MISSING_PKG:mysql-connector-python")

        connect_args = {}
        if "DB_HOST" in kwargs: connect_args["host"] = kwargs["DB_HOST"]
        if "DB_PORT" in kwargs: connect_args["port"] = kwargs["DB_PORT"]
        if "DB_USER" in kwargs: connect_args["user"] = kwargs["DB_USER"]
        if "DB_PASS" in kwargs: connect_args["password"] = kwargs["DB_PASS"]
        if "DB_NAME" in kwargs: connect_args["database"] = kwargs["DB_NAME"]

        self.conn = mysql.connector.connect(**connect_args)
        self.cursor = self.conn.cursor()

    def execute(self, query):
        self.cursor.execute(query)
        return self.cursor

    def close(self):
        if self.conn: self.conn.close()


# Factory
def get_adapter(db_type):
    if db_type == "sqlite":
        return SqliteAdapter()
    elif db_type == "duckdb":
        return DuckDbAdapter()
    elif db_type == "postgres" or db_type == "postgresql":
        return PostgresAdapter()
    elif db_type == "mysql":
        return MySqlAdapter()
    else:
        raise ValueError(f"Unsupported DB_TYPE: {db_type}")

# =============================================================================
# CORE LOGIC
# =============================================================================

def run_query(query, db_type, db_source, adapter_kwargs={}):
    """
    Executes the query and formats the result.
    """
    flags = {
        "json": False,
        "csv": False,
        "no_limit": False
    }

    # 1. Parse Flags
    import re
    # Extract --output <filename>
    output_match = re.search(r'--output\s+([^\s]+)', query)
    if output_match:
        flags["output"] = output_match.group(1)
        query = query[:output_match.start()] + query[output_match.end():]
    else:
        flags["output"] = None

    def pop_flag(q, flag):
        if flag in q:
            return q.replace(flag, ""), True
        return q, False

    query, flags["json"] = pop_flag(query, "--json")
    query, flags["csv"] = pop_flag(query, "--csv")
    query, flags["no_limit"] = pop_flag(query, "--no-limit")

    clean_query = query.strip()
    
    # 2. Safety Limit
    if not flags["json"] and not flags["csv"] and not flags["no_limit"]:
        low_query = clean_query.lower()
        if "limit" not in low_query:
            clean_query += " LIMIT 1000"

    # 3. Execution
    adapter = None
    try:
        adapter = get_adapter(db_type)
        adapter.connect(db_source, **adapter_kwargs)
        cursor = adapter.execute(clean_query)
        
        # Extract headers
        headers = [d[0] for d in cursor.description] if cursor.description else []

        # Generator for Streaming
        def row_generator():
            while True:
                # fetchmany is standard DB-API 2.0
                batch = cursor.fetchmany(1000)
                if not batch:
                    break
                for row in batch:
                    yield row

        # --- EXPORT ACTIONS ---
        if flags["json"]:
            if flags.get("output"):
                target_path = flags["output"]
                action = "print"
                pager = None
                message = f"Saved JSON to: {target_path}"
            else:
                fd, target_path = tempfile.mkstemp(prefix="dais_db_", suffix=".json", text=True)
                os.close(fd)
                action = "page"
                pager = "cat"
                message = target_path

            with open(target_path, 'w', encoding='utf-8') as f:
                f.write("[\n")
                first = True
                for row in row_generator():
                    if not first: f.write(",\n")
                    item = dict(zip(headers, row))
                    f.write(json.dumps(item, default=str))
                    first = False
                f.write("\n]")
            
            adapter.close()
            return json.dumps({"status": "success", "action": action, "data": message, "pager": pager})

        if flags["csv"]:
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

            with open(target_path, 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(headers)
                for row in row_generator():
                    writer.writerow(row)
            
            adapter.close()
            return json.dumps({"status": "success", "action": action, "data": message, "pager": pager})

        # --- VIEW ACTION ---
        rows = cursor.fetchall()
        adapter.close()

        if not rows:
            return json.dumps({"status": "success", "action": "print", "data": "No results."})

        # Calculate widths
        widths = [len(h) for h in headers]
        str_rows = []
        for row in rows:
            s_row = [str(cell) if cell is not None else "NULL" for cell in row]
            str_rows.append(s_row)
            for i, cell in enumerate(s_row):
                widths[i] = max(widths[i], len(cell))

        def format_line(r, w_list):
            return " | ".join(f"{c:<{w}}" for c, w in zip(r, w_list))

        separator = "-+-".join("-" * w for w in widths)
        header_line = format_line(headers, widths)

        output_lines = [header_line, separator]
        for row in str_rows:
            output_lines.append(format_line(row, widths))

        full_output = "\n".join(output_lines)
        
        if len(output_lines) > 50:
            fd, path = tempfile.mkstemp(prefix="dais_db_", suffix=".txt", text=True)
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                f.write(full_output)
            user_pager = os.environ.get("PAGER", "less -S")
            return json.dumps({"status": "success", "action": "page", "data": path, "pager": user_pager})
        else:
            return json.dumps({"status": "success", "action": "print", "data": full_output})

    except ImportError as e:
        # Catch our custom missing package error or others
        msg = str(e)
        
        # RETRY MECHANISM: 
        # If import failed, it might be because the package is in the shell's python (e.g. Conda/Venv)
        # but not in our embedded python's path.
        if "MISSING_PKG" in msg and not getattr(sys, "_dais_path_synced", False):
            try:
                import subprocess
                # Ask the active shell python for its sys.path
                # We use the current shell's 'python3' command
                output = subprocess.check_output(
                    ["python3", "-c", "import sys; print(chr(10).join(sys.path))"], 
                    text=True, 
                    stderr=subprocess.DEVNULL
                )
                
                added_something = False
                for p in output.splitlines():
                    p = p.strip()
                    if p and os.path.isdir(p) and p not in sys.path:
                        sys.path.append(p)
                        added_something = True
                
                if added_something:
                    import importlib
                    importlib.invalidate_caches()
                
                # Mark as synced to prevent infinite recursion
                sys._dais_path_synced = True
                
                # RECURSIVE RETRY
                return run_query(query, db_type, db_source, adapter_kwargs)
                
            except Exception:
                # If sync fails (e.g. no python3), just proceed to error
                pass

        if "MISSING_PKG" in msg:
            pkg = msg.split(":")[1]
            return json.dumps({"status": "missing_pkg", "package": pkg})
        return json.dumps({"status": "error", "message": msg})
    except Exception as e:
        if adapter: adapter.close()
        return json.dumps({"status": "error", "message": str(e)})


def handle_command(cmd_input, cwd):
    """
    Main entry point invoked by C++ engine.
    
    Args:
        cmd_input (str): The query string.
        cwd (str): Current working directory of the shell.
    """
    try:
        # Ensure we can see newly installed packages (pip install from shell)
        import importlib
        import sys
        
        # Nuclear option: Clear the importer cache completely
        # This forces Python to re-scan directories for new packages
        sys.path_importer_cache.clear() 
        importlib.invalidate_caches()

        # Load .env from CWD if present
        env_vars = load_env_file(cwd)
        
        # Import config to get defaults
        try:
            import config
        except ImportError:
            return json.dumps({"status": "error", "message": "Configuration Error: Could not import 'config.py'."})

        query = cmd_input.strip()

        # 1. Expand Saved Queries
        if hasattr(config, "DB_QUERIES") and isinstance(config.DB_QUERIES, dict):
            if query in config.DB_QUERIES:
                query = config.DB_QUERIES[query]

        # 2. Get Connection Details
        # Priority: .env > config.py
        
        db_type = env_vars.get("DB_TYPE", getattr(config, "DB_TYPE", "sqlite"))
        db_source = env_vars.get("DB_SOURCE", getattr(config, "DB_SOURCE", ":memory:"))
        
        # Extra args for adapters (host/user/pass)
        adapter_kwargs = {}
        for k, v in env_vars.items():
            if k.startswith("DB_") and k not in ["DB_TYPE", "DB_SOURCE"]:
                # Pass DB_HOST -> host, etc. (implementation dependent)
                adapter_kwargs[k] = v

        return run_query(query, db_type, db_source.replace("_PROJECT_ROOT", cwd) if "_PROJECT_ROOT" in db_source else db_source, adapter_kwargs)

    except Exception as e:
         return json.dumps({"status": "error", "message": f"Unexpected Handler Error: {str(e)}"})
