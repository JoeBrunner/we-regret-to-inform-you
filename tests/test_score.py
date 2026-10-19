import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/we-regret-to-inform-you/scripts/score.py"
SAMPLE = ROOT / "examples/sample-resume.md"

STRONG = """<!-- Fictional test resume. -->
# Jordan Reyes
Austin, TX | (512) 555-0100 | jordan@example.com

## Summary
Customer success manager for B2B software, 6 years of renewals and onboarding.

## Experience
### Customer Success Manager | Northwind Cloud | 2022 – Present
- Renewed 94% of a $2.1M book across 38 accounts.
- Cut onboarding time from 30 days to 18 by building a setup checklist.
- Ran quarterly reviews for 12 enterprise customers.

### Support Lead | Fabrikam Apps | 2019 – 2022
- Trained 9 new agents and raised team CSAT from 82 to 91.
- Wrote 40 help articles that deflected about 15% of tickets.

## Education
### BA in Economics | Riverbend University | 2018
"""


def judgments(passes):
    """A full J1 to J6 set where the first `passes` entries pass."""
    return {"J%d" % i: {"result": "PASS" if i <= passes else "FAIL",
                        "why": "because %d" % i, "evidence": "line %d" % i} for i in range(1, 7)}


class ScoreTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "we-regret-to-inform-you"
        scratch.mkdir(exist_ok=True)
        temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name)

    def run_score(self, resume, *flags, judged=None, raw_judgments=None):
        """Write the resume text, run the scorer, and return the finished process."""
        path = self.work / "resume.md"
        path.write_text(resume, encoding="utf-8")
        command = [sys.executable, str(SCRIPT), str(path)]
        if judged is not None or raw_judgments is not None:
            file = self.work / "judgments.json"
            file.write_text(raw_judgments if raw_judgments is not None else json.dumps(judged),
                            encoding="utf-8")
            command += ["--judgments", str(file)]
        return subprocess.run(command + list(flags), capture_output=True, text=True)

    def results(self, resume):
        """Map M1..M4 to PASS or FAIL for a resume."""
        process = self.run_score(resume, "--json")
        self.assertEqual(process.returncode, 0, process.stderr)
        return {c["id"]: c["result"] for c in json.loads(process.stdout)["checks"]}

    def test_sample_resume(self):
        process = subprocess.run([sys.executable, str(SCRIPT), str(SAMPLE)],
                                 capture_output=True, text=True)
        self.assertEqual(process.returncode, 0, process.stderr)
        rows = {line.split("|")[1].split()[0]: line.split("|")[2].strip()
                for line in process.stdout.splitlines() if line.startswith("| M")}
        self.assertEqual(rows, {"M1": "FAIL", "M2": "FAIL", "M3": "FAIL", "M4": "PASS"})
        self.assertIn("Mechanical checks only: 1 of 4 passed.", process.stdout)
        self.assertNotIn("Draft:", process.stdout)

    def test_strong_resume_passes_all_four(self):
        self.assertEqual(self.results(STRONG), {"M1": "PASS", "M2": "PASS", "M3": "PASS", "M4": "PASS"})

    def test_m1_boundary_two_vs_three_phrases(self):
        two = STRONG + "\nA team player who is hardworking.\n"
        three = two + "Also dedicated.\n"
        self.assertEqual(self.results(two)["M1"], "PASS")
        self.assertEqual(self.results(three)["M1"], "FAIL")

    def test_m1_counts_distinct_phrases_and_word_boundaries(self):
        repeated = STRONG + "\nteam player. Team Player. TEAM PLAYER. team player.\n"
        self.assertEqual(self.results(repeated)["M1"], "PASS")
        # "dedicated" inside another word must not match; "communicationsX" is not "communication".
        inside = STRONG + "\nundedicated hardworkingly communications\n"
        self.assertEqual(self.results(inside)["M1"], "PASS")

    def test_m1_ignores_role_and_degree_lines(self):
        resume = STRONG.replace("### BA in Economics", "### BA in Communication, Dedicated Teamwork Track")
        resume = resume.replace("6 years of renewals", "6 years of renewals, a team player with attention to detail")
        self.assertEqual(self.results(resume)["M1"], "PASS")
        resume = resume.replace("Ran quarterly reviews", "Strong communicator who ran quarterly reviews")
        self.assertEqual(self.results(resume)["M1"], "FAIL")

    def test_m1_ignores_filler_inside_blanks(self):
        text = STRONG + "\n[ADD: team player, hardworking, dedicated, passionate]\n"
        self.assertEqual(self.results(text)["M1"], "PASS")

    def test_m2_boundary_one_vs_two_weak_bullets(self):
        one = STRONG + "\n- Helped customers with setup.\n"
        two = one + "- Responsible for renewals.\n"
        self.assertEqual(self.results(one)["M2"], "PASS")
        self.assertEqual(self.results(two)["M2"], "FAIL")

    def test_m2_only_counts_bullets_that_start_with_the_phrase(self):
        text = STRONG + "\n- Never helped anyone.\n- Rehelped nobody.\nHelped in a paragraph.\n"
        self.assertEqual(self.results(text)["M2"], "PASS")

    def test_m3_half_passes_and_under_half_fails(self):
        half = "## Experience\n### A | B | 2020\n- Grew sales 20%.\n- Answered phones.\n"
        under = "## Experience\n### A | B | 2020\n- Grew sales 20%.\n- Answered phones.\n- Filed forms.\n"
        self.assertEqual(self.results("# N\n" + half)["M3"], "PASS")
        self.assertEqual(self.results("# N\n" + under)["M3"], "FAIL")

    def test_m3_digit_inside_blank_does_not_count(self):
        text = "# N\n## Experience\n### A | B | 2020\n- Grew sales [ADD: by what percent, 20?].\n"
        self.assertEqual(self.results(text)["M3"], "FAIL")
        counted = "# N\n## Experience\n### A | B | 2020\n- Grew sales 20% [ADD: over what period?].\n"
        self.assertEqual(self.results(counted)["M3"], "PASS")

    def test_m3_only_the_two_most_recent_roles(self):
        text = ("# N\n## Experience\n### A | B | 2022\n- Grew sales 20%.\n"
                "### C | D | 2020\n- Cut costs 5%.\n"
                "### E | F | 2018\n- Answered phones.\n- Filed forms.\n- Greeted guests.\n")
        process = self.run_score(text, "--json")
        check = json.loads(process.stdout)["checks"][2]
        self.assertEqual(check["result"], "PASS")
        self.assertIn("2 of 2 bullets", check["evidence"])

    def test_m3_no_experience_bullets(self):
        process = self.run_score("# N\n## Summary\n- Grew sales 20%.\n", "--json")
        check = json.loads(process.stdout)["checks"][2]
        self.assertEqual(check["result"], "FAIL")
        self.assertEqual(check["evidence"], "no experience bullets found")

    def test_m4_total_words_boundary(self):
        base = "# N\n## Experience\n### A | B | 2020\n- Grew sales 20%.\n"
        base_words = 8  # N, Experience, A, B, 2020, Grew, sales, 20%.
        at_limit = base + " ".join(["word"] * (700 - base_words)) + "\n"
        over = base + " ".join(["word"] * (701 - base_words)) + "\n"
        self.assertEqual(self.results(at_limit)["M4"], "PASS")
        self.assertEqual(self.results(over)["M4"], "FAIL")
        evidence = json.loads(self.run_score(over, "--json").stdout)["checks"][3]["evidence"]
        self.assertIn("701 words", evidence)

    def test_m4_bullet_length_boundary(self):
        base = "# N\n## Experience\n### A | B | 2020\n"
        self.assertEqual(self.results(base + "- " + " ".join(["w"] * 40) + "\n")["M4"], "PASS")
        self.assertEqual(self.results(base + "- " + " ".join(["w"] * 41) + "\n")["M4"], "FAIL")

    def test_judgment_counts_and_verdicts(self):
        # STRONG passes all four mechanical checks, so total = 4 + judged passes.
        expected = {2: (6, "We regret to inform you."), 3: (7, "We'll keep your resume on file."),
                    4: (8, "We'll keep your resume on file."), 5: (9, "We are pleased to inform you."),
                    6: (10, "We are pleased to inform you.")}
        for passes, (total, verdict) in expected.items():
            process = self.run_score(STRONG, judged=judgments(passes))
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertIn("**Passed: %d of 10**" % total, process.stdout)
            self.assertIn("\n**%s**" % verdict, process.stdout)
            self.assertNotIn("Mechanical checks only", process.stdout)
            self.assertIn("| J1 Screen software can read it |", process.stdout)
            self.assertIn("| J6 Speaks the post's language |", process.stdout)

    def test_zero_passes_verdict(self):
        sample = subprocess.run(
            [sys.executable, str(SCRIPT), str(SAMPLE), "--judgments", str(self._write(judgments(0)))],
            capture_output=True, text=True)
        self.assertIn("**Passed: 1 of 10**", sample.stdout)
        self.assertIn("**We regret to inform you.**", sample.stdout)

    def _write(self, data):
        path = self.work / "j.json"
        path.write_text(json.dumps(data), encoding="utf-8")
        return path

    def test_bad_judgments_exit_two(self):
        missing = judgments(6)
        del missing["J4"]
        bad_value = judgments(6)
        bad_value["J2"]["result"] = "pass"
        extra = judgments(6)
        extra["J7"] = {"result": "PASS", "why": "", "evidence": ""}
        for name, process in [
            ("missing key", self.run_score(STRONG, judged=missing)),
            ("bad result", self.run_score(STRONG, judged=bad_value)),
            ("extra key", self.run_score(STRONG, judged=extra)),
            ("invalid json", self.run_score(STRONG, raw_judgments="{not json")),
        ]:
            self.assertEqual(process.returncode, 2, name)
            self.assertNotEqual(process.stderr.strip(), "", name)
            self.assertEqual(process.stdout, "", name)

    def test_input_errors_exit_two(self):
        self.assertEqual(self.run_score("<!-- only a comment -->\n  \n").returncode, 2)
        missing = subprocess.run([sys.executable, str(SCRIPT), str(self.work / "none.md")],
                                 capture_output=True, text=True)
        self.assertEqual(missing.returncode, 2)

    def test_blanks_line(self):
        text = STRONG + "\n- Grew [ADD: by how much?] and [ADD: who for?]\n[add: lower case]\n"
        process = self.run_score(text)
        self.assertTrue(process.stdout.rstrip().endswith("Draft: 3 blanks to fill before sending."))
        clean = self.run_score(STRONG)
        self.assertNotIn("Draft:", clean.stdout)
        self.assertEqual(json.loads(self.run_score(text, "--json").stdout)["blanks"], 3)

    def test_json_matches_markdown(self):
        with_j = self.run_score(STRONG, "--json", judged=judgments(4))
        data = json.loads(with_j.stdout)
        self.assertEqual((data["passed"], data["total"]), (8, 10))
        self.assertEqual(data["verdict"], "We'll keep your resume on file.")
        self.assertEqual([c["id"] for c in data["checks"]],
                         ["M1", "M2", "M3", "M4", "J1", "J2", "J3", "J4", "J5", "J6"])
        markdown = self.run_score(STRONG, judged=judgments(4)).stdout
        for check in data["checks"]:
            self.assertIn("| %s %s | %s |" % (check["id"], check["name"], check["result"]), markdown)
        self.assertIn("**Passed: %d of 10**" % data["passed"], markdown)
        mech = json.loads(self.run_score(SAMPLE.read_text(encoding="utf-8"), "--json").stdout)
        self.assertEqual((mech["passed"], mech["total"], mech["verdict"], mech["blanks"]),
                         (1, 4, None, 0))


if __name__ == "__main__":
    unittest.main()
