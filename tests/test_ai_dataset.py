import json, tempfile, unittest
from pathlib import Path
from code321.ai_dataset import load_task_training_text

class TaskDatasetTests(unittest.TestCase):
    def test_balances_tagged_jsonl_to_requested_quotas(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            rows=[{"category":"coding","prompt":"Napisz funkcję","completion":"def f(): pass"},{"category":"chat","prompt":"Cześć","completion":"Witaj"},{"category":"reasoning","prompt":"2+2","completion":"4"}]
            (root/"dataset.jsonl").write_text("\n".join(json.dumps(x,ensure_ascii=False) for x in rows),encoding="utf-8")
            text, report=load_task_training_text(root,{"dataset_file":"dataset.jsonl","task_mix":{"programowanie":3,"rozmowa":2,"rozumowanie":1},"seed":321})
            self.assertEqual(text.count("Użytkownik:"),6)
            self.assertTrue(any("Łącznie do treningu: 6" in x for x in report))
    def test_fails_when_category_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"dataset.jsonl").write_text(json.dumps({"category":"coding","prompt":"x","completion":"y"}),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"Brak przykładów"):
                load_task_training_text(root,{"dataset_file":"dataset.jsonl","task_mix":{"rozmowa":10}})
    def test_generic_data_warns_and_balances(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/"dataset.txt").write_text("A"*3000,encoding="utf-8")
            text, report=load_task_training_text(root,{"dataset_file":"dataset.txt","task_mix":{"programowanie":2,"rozmowa":3}})
            self.assertEqual(text.count("A"),5000)
            self.assertTrue(any("wspólnego tekstu ogólnego" in x for x in report))

if __name__ == "__main__": unittest.main()
