import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from code321.runtime import run_file


class RuntimeTests(unittest.TestCase):
    def test_missing_file_returns_error(self):
        self.assertEqual(run_file(Path("this-file-does-not-exist.321")), 1)

    def test_variables_and_strings(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "hello.321"
            source.write_text('let name = "Ala"\nprint "Hej, " + name\n', encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(run_file(source), 0)
            self.assertEqual(output.getvalue(), "Hej, Ala\n")

    def test_if_else_and_loop(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "flow.321"
            source.write_text(
                'let n = 0\nwhile n < 3:\n    set n = n + 1\n'
                'if n == 3:\n    print "OK"\nelse:\n    print "NIE"\n'
                'for i in range(2):\n    print i\n', encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(run_file(source), 0)
            self.assertEqual(output.getvalue(), "OK\n0\n1\n")

    def test_function_and_return(self):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "functions.321"
            source.write_text(
                'def greet(name):\n    print "Hej " + name\n    return 7\n'
                'greet("Ola")\n', encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(run_file(source), 0)
            self.assertEqual(output.getvalue(), "Hej Ola\n")

    def test_import_inside_project(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "module.321").write_text('print "modul"\n', encoding="utf-8")
            main = root / "main.321"
            main.write_text('import "module.321"\n', encoding="utf-8")
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(run_file(main), 0)
            self.assertEqual(output.getvalue(), "modul\n")


if __name__ == "__main__":
    unittest.main()
