from pathlib import Path
import re
import unittest

from contract_holes import __version__


ROOT = Path(__file__).resolve().parents[1]


class ReleaseTests(unittest.TestCase):
    def test_release_version_is_synchronized(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        task_tracker = (ROOT / "TASKS.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        workflow = (ROOT / "examples/github-actions/contract-holes.yml").read_text(
            encoding="utf-8"
        )

        metadata_version = re.search(
            r'^version = "([^"]+)"$', pyproject, flags=re.MULTILINE
        )
        self.assertIsNotNone(metadata_version)
        self.assertEqual(__version__, "1.0.0")
        self.assertEqual(metadata_version.group(1), __version__)
        self.assertIn("Current release: `1.0.0`", task_tracker)
        self.assertIn("## 1.0.0 — 2026-08-08", changelog)
        self.assertIn("contract-holes==1.0.0", workflow)

    def test_release_build_inputs_are_exact_and_complete(self) -> None:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        requirements = (ROOT / "requirements/release.txt").read_text(
            encoding="utf-8"
        )
        manifest = (ROOT / "MANIFEST.in").read_text(encoding="utf-8")

        self.assertIn('requires = ["setuptools==80.9.0"]', pyproject)
        for pin in (
            "build==1.5.0",
            "packaging==26.2",
            "pyproject-hooks==1.2.0",
            "setuptools==80.9.0",
            "wheel==0.45.1",
        ):
            self.assertIn(pin, requirements)
        for included in (
            "include CHANGELOG.md",
            "include LICENSE",
            "recursive-include docs *.md",
            "recursive-include release *",
            "recursive-include src/contract_holes/schemas *.json",
            "recursive-include tests *.json *.md *.py *.sol *.toml",
        ):
            self.assertIn(included, manifest)

    def test_release_process_requires_reproduction_smoke_hashes_and_signatures(self) -> None:
        process = (ROOT / "docs/RELEASING.md").read_text(encoding="utf-8")
        checklist = (ROOT / "release/1.0.0-checklist.md").read_text(
            encoding="utf-8"
        )
        tool = (ROOT / "scripts/release.py").read_text(encoding="utf-8")

        for requirement in (
            "independently",
            "byte-for-byte",
            "SHA256SUMS",
            "smoke",
            "git tag -s v1.0.0",
            "gpg --verify",
        ):
            self.assertIn(requirement, process)
        self.assertIn("approved signed local release", checklist)
        self.assertIn("6A60 6D37 A243 C52A", checklist)
        self.assertIn("independent_builds", tool)
        self.assertIn("_smoke_test_wheel", tool)
        self.assertIn("_normalize_sdist", tool)
        self.assertIn("_validate_wheel", tool)
        self.assertIn("_validate_sdist", tool)


if __name__ == "__main__":
    unittest.main()
