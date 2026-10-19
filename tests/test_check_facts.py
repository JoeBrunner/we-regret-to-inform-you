import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/we-regret-to-inform-you/scripts/check_facts.py"
SPEC = importlib.util.spec_from_file_location("check_facts", SCRIPT)
FACTS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(FACTS)
OLD = "# Morgan Ellis\n### Support Specialist | Alderpath Software | 2021–2026\n- Helped customers with account setup.\n- Handled 45 chats per day."


class FactTests(unittest.TestCase):
    def test_fake_number_flagged(self):
        self.assertIn(("number", "35%"), FACTS.check_facts(OLD, OLD + "\n- Reduced churn by 35%."))

    def test_only_rewording_is_clean(self):
        new = OLD.replace("Helped customers with account setup.", "Guided customers through account setup.")
        self.assertEqual(FACTS.check_facts(OLD, new), [])

    def test_new_year_and_multiword_name_flagged(self):
        flags = FACTS.check_facts(OLD, OLD + "\n### Director of Support | Invented Company | 2027")
        self.assertIn(("number", "2027"), flags)
        self.assertIn(("name", "Director of Support"), flags)
        self.assertIn(("name", "Invented Company"), flags)

    def test_placeholders_and_comments_ignored(self):
        self.assertEqual(FACTS.check_facts(OLD, OLD + "\n[ADD: Did 75% at New Company improve?]\n"
                                         "<!-- 88% Hidden Company -->"), [])

    def test_job_terms_ignored_but_not_job_numbers(self):
        job = "Customer Success Manager with 10 years of experience."
        flags = FACTS.check_facts(OLD, OLD + "\nCustomer Success Manager\n10 years", job)
        self.assertEqual(flags, [("number", "10")])

    def test_units_and_precise_numbers(self):
        flags = FACTS.check_facts("50 tickets, $1,000 budget", "50% retention, $1000 budget, 2.5 years")
        self.assertEqual(flags, [("number", "50%"), ("number", "2.5")])

    def test_case_and_whitespace_do_not_create_a_new_name(self):
        self.assertEqual(FACTS.check_facts("customer success manager", "Customer  Success Manager"), [])

    def test_name_punctuation_does_not_create_a_new_fact(self):
        self.assertEqual(FACTS.check_facts("Alderpath Software", "Alderpath Software."), [])

    def test_changed_numeric_sign_flagged(self):
        self.assertEqual(FACTS.check_facts("10%", "-10%"), [("number", "-10%")])

    def test_names_do_not_join_across_lines_or_separators(self):
        self.assertEqual(FACTS.names("Summary\nExperience\nSkills\nEducation\nZendesk, Salesforce"), [])
        self.assertEqual(FACTS.names("Renée Ellis | Café Lumière"), ["Renée Ellis", "Café Lumière"])

    def test_duplicate_additions_reported_once(self):
        self.assertEqual(FACTS.check_facts("", "25% 25%\nNew Company\nNew Company"),
                         [("number", "25%"), ("name", "New Company")])

    def test_cli_exit_status_and_output(self):
        scratch = ROOT / "we-regret-to-inform-you"
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temp:
            old, new, job = [Path(temp) / name for name in ("old.md", "new.md", "job.md")]
            old.write_text(OLD, encoding="utf-8")
            job.write_text("Customer Success Manager", encoding="utf-8")
            for text, code, expected in [(OLD, 0, "No new numbers"),
                                          (OLD + "\n99%", 1, "REVIEW number: 99%")]:
                new.write_text(text, encoding="utf-8")
                result = subprocess.run([sys.executable, str(SCRIPT), str(old), str(new), str(job)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, code, result.stderr)
                self.assertIn(expected, result.stdout)
            result = subprocess.run([sys.executable, str(SCRIPT), str(old), str(Path(temp) / "missing.md")],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main()
