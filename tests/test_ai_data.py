import csv
import json
import tempfile
import unittest
from pathlib import Path

from code321.ai_trainer import load_training_text


class DatasetLoaderTests(unittest.TestCase):
    def test_loads_plain_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "dataset.txt").write_text("# komentarz\nAla ma kota.\n", encoding="utf-8")
            self.assertEqual(load_training_text(root, {}), "Ala ma kota.")

    def test_loads_chat_messages_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = {"messages": [
                {"role": "user", "content": "Cześć"},
                {"role": "assistant", "content": "Witaj"},
            ]}
            (root / "dataset.jsonl").write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
            cfg = {"dataset_file": "dataset.jsonl"}
            text = load_training_text(root, cfg)
            self.assertIn("Użytkownik: Cześć", text)
            self.assertIn("AI: Witaj", text)

    def test_loads_prompt_completion_jsonl(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row = {"prompt": "Ile to 2+2?", "completion": "4"}
            (root / "data.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")
            text = load_training_text(root, {"dataset_file": "data.jsonl"})
            self.assertIn("AI: 4", text)

    def test_loads_prompt_response_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "data.csv").write_text("prompt,response\nHej,Cześć\n", encoding="utf-8")
            text = load_training_text(root, {"dataset_file": "data.csv"})
            self.assertIn("Użytkownik: Hej", text)
            self.assertIn("AI: Cześć", text)

    def test_rejects_path_outside_project(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "project"
            root.mkdir()
            outside = Path(tmp) / "outside.txt"
            outside.write_text("x", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_training_text(root, {"dataset_file": "../outside.txt"})


if __name__ == "__main__":
    unittest.main()
