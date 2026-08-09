from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.+?)\s*$", re.MULTILINE)


def heading_anchor(value: str) -> str:
    value = re.sub(r"<[^>]+>", "", value).strip().lower()
    value = re.sub(r"[^\w\- ]", "", value)
    return re.sub(r" +", "-", value)


class DocumentationTests(unittest.TestCase):
    def test_required_user_and_contributor_guides_exist(self) -> None:
        required = (
            "CONTRIBUTING.md",
            "SECURITY.md",
            "docs/README.md",
            "docs/INSTALLATION.md",
            "docs/CLI_REFERENCE.md",
            "docs/RULE_CATALOG.md",
            "docs/CI.md",
            "docs/PROOF_REQUIREMENTS.md",
            "docs/BOUNTY_PROFILE.md",
        )

        for relative in required:
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_file())

    def test_internal_markdown_links_resolve_to_files_and_headings(self) -> None:
        documents = [ROOT / "README.md", ROOT / "CONTRIBUTING.md", ROOT / "SECURITY.md"]
        documents.extend(sorted((ROOT / "docs").glob("*.md")))

        for document in documents:
            content = document.read_text(encoding="utf-8")
            for raw_target in MARKDOWN_LINK.findall(content):
                if raw_target.startswith(("http://", "https://", "mailto:")):
                    continue
                path_part, separator, fragment = raw_target.partition("#")
                target = document if not path_part else (document.parent / path_part).resolve()
                with self.subTest(document=document.name, target=raw_target):
                    self.assertTrue(target.is_file(), f"missing link target: {target}")
                    if separator and fragment:
                        target_content = target.read_text(encoding="utf-8")
                        anchors = {
                            heading_anchor(heading)
                            for heading in HEADING.findall(target_content)
                        }
                        self.assertIn(fragment, anchors)

    def test_readme_and_cli_reference_cover_every_public_command(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        reference = (ROOT / "docs/CLI_REFERENCE.md").read_text(encoding="utf-8")

        for command in (
            "rules",
            "inspect",
            "benchmark",
            "evaluate",
            "proofs",
            "fetch",
            "explain",
            "compatibility",
            "bounty",
        ):
            with self.subTest(command=command):
                self.assertIn(f"holes {command}", readme)
                self.assertIn(f"holes {command}", reference)


if __name__ == "__main__":
    unittest.main()
