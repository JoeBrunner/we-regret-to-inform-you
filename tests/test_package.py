import ast
import importlib.util
import json
from pathlib import Path
import re
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/we-regret-to-inform-you"
SPEC = importlib.util.spec_from_file_location("make_zip", ROOT / "make_zip.py")
PACKAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGE)


class PackageTests(unittest.TestCase):
    def test_skill_has_frontmatter_name(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(text.startswith("---"))
        front = text.split("---", 2)[1]
        self.assertRegex(front, r"(?m)^name: we-regret-to-inform-you$")

    def test_file_list_includes_scorer(self):
        self.assertEqual(set(PACKAGE.FILES), {"SKILL.md", "scripts/check_facts.py",
                                              "scripts/make_docx.py", "scripts/score.py"})

    def test_manifests_and_install_commands_match(self):
        plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text())
        market = json.loads((ROOT / ".claude-plugin/marketplace.json").read_text())
        self.assertEqual(plugin["name"], "we-regret-to-inform-you")
        self.assertEqual(market["name"], "we-regret-to-inform-you")
        self.assertEqual(market["plugins"][0]["name"], plugin["name"])
        self.assertEqual(market["plugins"][0]["source"], "./")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        for prefix in ("/plugin", "claude plugin"):
            self.assertIn(prefix + " marketplace add JoeBrunner/" + market["name"], readme)
            self.assertIn(prefix + " install " + plugin["name"] + "@" + market["name"], readme)
        self.assertNotIn("—", readme)
        self.assertIn("[PROOF.md](PROOF.md)", readme)
        self.assertNotIn("<!-- PROOF", readme)

    def test_zip_reproducible_clean_and_current(self):
        scratch = ROOT / "we-regret-to-inform-you"
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temp:
            first = PACKAGE.build(Path(temp) / "first.zip")
            second = PACKAGE.build(Path(temp) / "second.zip")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.read_bytes(), PACKAGE.OUT.read_bytes())
            with zipfile.ZipFile(first) as archive:
                self.assertEqual(set(archive.namelist()),
                                 {"we-regret-to-inform-you/" + p for p in PACKAGE.FILES})
                for name in PACKAGE.FILES:
                    self.assertEqual(archive.read("we-regret-to-inform-you/" + name), (SKILL / name).read_bytes())
                for info in archive.infolist():
                    self.assertEqual(info.date_time, PACKAGE.FIXED_TIME)
                    self.assertNotIn("__pycache__", info.filename)
                    self.assertNotIn(".DS_Store", info.filename)

    def test_python39_syntax_and_stdlib_imports(self):
        allowed = {"argparse", "json", "re", "sys", "zipfile", "pathlib", "xml", "unicodedata"}
        for path in [ROOT / "make_zip.py", *sorted((SKILL / "scripts").glob("*.py"))]:
            tree = ast.parse(path.read_text(encoding="utf-8"), feature_version=(3, 9))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertIn(alias.name.split(".")[0], allowed)
                elif isinstance(node, ast.ImportFrom):
                    self.assertIn(node.module.split(".")[0], allowed)
        self.assertLessEqual(len((SKILL / "scripts/make_docx.py").read_text().splitlines()), 250)


if __name__ == "__main__":
    unittest.main()
