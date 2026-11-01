import tempfile
import unittest
from pathlib import Path

from code321.runtime import run_file


class RuntimeTests(unittest.TestCase):
    def test_missing_file_returns_error(self):
        self.assertEqual(run_file(Path("this-file-does-not-exist.321")), 1)

    def test_simple_program(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "hello.321"
            source.write_text('let name = "Ala"\nprint "Hej, " + name\n', encoding="utf-8")
            self.assertEqual(run_file(source), 0)


if __name__ == "__main__":
    unittest.main()
