import json
from pathlib import Path
import shutil
import tempfile
import unittest

from contract_holes.benchmark import (
    benchmark_exit_status,
    benchmark_paths,
    compare_with_baseline,
)


CORPUS_ROOT = Path("tests/fixtures/m2_corpus").resolve()


def performance_payload(multiplier: float) -> dict[str, object]:
    return {
        "modes": {
            "source_only": {
                "duration_seconds": 1.0 * multiplier,
                "python_peak_bytes": 1000 * multiplier,
            },
            "compiler": {
                "duration_seconds": 4.0 * multiplier,
                "python_peak_bytes": 4000 * multiplier,
                "phases": {
                    "compile_duration_seconds": 2.0 * multiplier,
                    "index_duration_seconds": 1.0 * multiplier,
                    "scan_duration_seconds": 1.0 * multiplier,
                },
            },
        }
    }


class BenchmarkTests(unittest.TestCase):
    def test_performance_regressions_are_reported_but_do_not_fail(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            baseline_path = root / "baseline.json"
            baseline_path.write_text(
                json.dumps(performance_payload(1.0)), encoding="utf-8"
            )
            current = performance_payload(1.5)
            comparison = compare_with_baseline(current, baseline_path, root)
            current["correctness"] = {"status": "passed"}
            current["performance_comparison"] = comparison

        self.assertEqual(comparison["status"], "reported")
        self.assertEqual(len(comparison["regressions"]), 7)
        self.assertTrue(
            all(
                metric["classification"] == "regression"
                for metric in comparison["metrics"]
            )
        )
        self.assertEqual(benchmark_exit_status(current), 0)
        current["correctness"] = {"status": "failed"}
        self.assertEqual(benchmark_exit_status(current), 1)

    @unittest.skipUnless(shutil.which("forge"), "Foundry is required for benchmarking")
    def test_offline_corpus_benchmark_matches_versioned_expectations(self) -> None:
        payload = benchmark_paths([CORPUS_ROOT / "src"], offline=True)

        self.assertEqual(payload["correctness"]["status"], "passed")
        self.assertEqual(
            payload["modes"]["source_only"]["findings"],
            {"finding_count": 0, "rule_counts": {}, "severity_counts": {}},
        )
        self.assertEqual(
            payload["modes"]["compiler"]["findings"],
            {
                "finding_count": 5,
                "rule_counts": {"SOL005": 5},
                "severity_counts": {"high": 5},
            },
        )
        self.assertGreater(payload["modes"]["source_only"]["duration_seconds"], 0)
        self.assertGreater(payload["modes"]["source_only"]["python_peak_bytes"], 0)
        self.assertGreater(payload["modes"]["compiler"]["duration_seconds"], 0)
        self.assertGreater(payload["modes"]["compiler"]["python_peak_bytes"], 0)
        self.assertEqual(benchmark_exit_status(payload), 0)


if __name__ == "__main__":
    unittest.main()
