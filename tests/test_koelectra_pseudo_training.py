import unittest

from scripts.train_koelectra_pseudo import build_pseudo_dataset


class KoElectraPseudoTrainingTests(unittest.TestCase):
    def test_build_pseudo_dataset_contains_all_risk_labels_from_seed_texts(self):
        rows = build_pseudo_dataset(
            [],
            max_source_rows=0,
            max_samples_per_label=20,
            seed=42,
        )

        labels = {row["label"] for row in rows}

        self.assertEqual(labels, {"LOW", "MEDIUM", "HIGH"})
        self.assertTrue(all(row["text"] for row in rows))


if __name__ == "__main__":
    unittest.main()
