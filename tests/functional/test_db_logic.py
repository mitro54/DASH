import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Add src/py_scripts to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src/py_scripts')))

import db_handler

class TestDBHandler(unittest.TestCase):
    def setUp(self):
        # Create a temp directory structure for env testing
        # /tmp/
        #   - parent/
        #       - .env (DB_NAME=ParentDB)
        #       - child/
        #           - (empty)
        self.test_dir = tempfile.mkdtemp()
        self.parent_dir = os.path.join(self.test_dir, "parent")
        self.child_dir = os.path.join(self.parent_dir, "child")
        os.makedirs(self.child_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_recursive_env_loading(self):
        """Verify we can find .env in a parent directory."""
        env_path = os.path.join(self.parent_dir, ".env")
        with open(env_path, "w") as f:
            f.write("DB_NAME=ParentDB\nTEST_KEY=FoundIt")

        # Run from child
        env = db_handler.load_env_file(self.child_dir)
        self.assertEqual(env.get("TEST_KEY"), "FoundIt")
        self.assertEqual(env.get("DB_NAME"), "ParentDB")

    def test_env_priority(self):
        """Verify CWD .env overrides Parent .env."""
        # Parent
        with open(os.path.join(self.parent_dir, ".env"), "w") as f:
            f.write("VAR=Parent")
        
        # Child
        with open(os.path.join(self.child_dir, ".env"), "w") as f:
            f.write("VAR=Child")

        env = db_handler.load_env_file(self.child_dir)
        self.assertEqual(env.get("VAR"), "Child")

    def test_config_key_mapping(self):
        """Verify DB_N maps to DB_NAME etc."""
        # Mock env vars
        env_vars = {"DB_N": "my_db", "DB_H": "localhost", "DB_T": "postgres"}
        
        # Mock Config 
        mock_config = MagicMock()
        mock_config.DB_KEY_MAPPING = {
            "DB_TYPE": ["DB_T"],
            "DB_HOST": ["DB_H"],
            "DB_NAME": ["DB_N"]
        }

        resolved = db_handler._resolve_connection_config(env_vars, mock_config)
        
        self.assertEqual(resolved["DB_NAME"], "my_db")
        self.assertEqual(resolved["DB_HOST"], "localhost")
        self.assertEqual(resolved["DB_TYPE"], "postgres")

    def test_system_env_fallback(self):
        """Verify we check os.environ if .env is missing."""
        with patch.dict(os.environ, {"DB_TYPE": "mysql", "DB_NAME": "sys_db"}):
            resolved = db_handler._resolve_connection_config({}, None)
            self.assertEqual(resolved["DB_TYPE"], "mysql")
            self.assertEqual(resolved["DB_NAME"], "sys_db")

    def test_adapter_factory(self):
        """Verify get_adapter returns correct classes."""
        self.assertIsInstance(db_handler.get_adapter("sqlite"), db_handler.SqliteAdapter)
    
    
    def _verify_connection(self, db_type, env_prefix):
        """Helper to verify connection for a specific DB type using env vars."""
        host = os.environ.get(f"DB_HOST_{env_prefix}")
        if not host:
            if os.environ.get("CI") == "true":
                self.fail(f"CI Error: DB_HOST_{env_prefix} not set. {db_type} service expected in CI.")
            print(f"Skipping {db_type} test (DB_HOST_{env_prefix} not set)")
            return

        try:
            print(f"Testing {db_type} Connection...")
            env_mock = {
                "DB_TYPE": db_type.lower(),
                "DB_HOST": host,
                "DB_PORT": os.environ.get(f"DB_PORT_{env_prefix}", "5432" if db_type == "Postgres" else "3306"),
                "DB_USER": os.environ.get(f"DB_USER_{env_prefix}", "test_user"), 
                "DB_PASS": os.environ.get(f"DB_PASS_{env_prefix}", "test_password"),
                "DB_NAME": os.environ.get(f"DB_NAME_{env_prefix}", "test_db")
            }
            
            # Mock config and resolve
            mock_config = MagicMock()
            mock_config.DB_KEY_MAPPING = None
            resolved = db_handler._resolve_connection_config(env_mock, mock_config)
            
            adapter = db_handler.get_adapter(db_type.lower())
            adapter.connect(None, **resolved)
            
            # Run simple query
            cursor = adapter.execute("SELECT 1")
            result = cursor.fetchone()
            self.assertEqual(result[0], 1)
            adapter.close()
            print(f"  {db_type} PASS")
        except Exception as e:
            self.fail(f"{db_type} Connection Failed: {e}")

    def test_live_connections(self):
        """
        Verify real connections to CI Service Containers if configured.
        We check for DB_HOST_PG and DB_HOST_MY environment variables.
        """
        self._verify_connection("Postgres", "PG")
        self._verify_connection("MySQL", "MY")

if __name__ == '__main__':
    unittest.main()

