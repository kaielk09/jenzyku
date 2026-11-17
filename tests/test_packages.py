import json
import tempfile
import unittest
import zipfile
from pathlib import Path

from code321.packages import PackageError, install, list_packages, remove


class PackageManagerTests(unittest.TestCase):
    def test_install_list_remove_local_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "321code.json").write_text('{"name":"demo","scripts":{}}', encoding="utf-8")
            package = root / "sample"
            package.mkdir()
            (package / "package.json").write_text(json.dumps({
                "name": "hello321", "version": "1.2.0"
            }), encoding="utf-8")
            (package / "hello.321").write_text('print "Hej z pakietu"\n', encoding="utf-8")
            archive = root / "hello321.zip"
            with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                bundle.write(package / "package.json", "package.json")
                bundle.write(package / "hello.321", "hello.321")
            self.assertIn("hello321@1.2.0", install(str(archive), root))
            self.assertEqual(list_packages(root), [{
                "name": "hello321", "version": "1.2.0", "installed": True
            }])
            self.assertIn("hello321", remove("hello321", root))
            self.assertEqual(list_packages(root), [])

    def test_reject_archive_without_package_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "321code.json").write_text("{}", encoding="utf-8")
            archive = root / "bad.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("bad.321", 'print "x"')
            with self.assertRaises(PackageError):
                install(str(archive), root)


if __name__ == "__main__":
    unittest.main()
