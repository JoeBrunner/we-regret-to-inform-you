#!/usr/bin/env python3
"""Score a resume on ten yes/no checks: four counted here, six judged by Claude.

Usage: python3 score.py RESUME.md [--judgments JUDGMENTS.json] [--json]
M1 to M4 are mechanical and always scored. J1 to J6 come in as JSON from Claude:
{"J1": {"result": "PASS" or "FAIL", "why": "...", "evidence": "..."}, ...}
Exit 0: scored (whatever the score); 2: input or usage error. Never 1.
"""
import argparse
import json
import re
import sys
from pathlib import Path

FILLER = [
    "team player", "hardworking", "hard-working", "dedicated", "passionate", "passion for",
    "detail-oriented", "attention to detail", "self-starter", "go-getter", "strong communicator",
    "positive attitude", "results-driven", "communication", "teamwork", "problem solving",
    "problem-solving", "time management", "adaptability", "customer focus", "people person",
    "think outside the box",
]
WEAK_OPENERS = ["responsible for", "helped", "assisted", "worked on", "duties included",
                "tasked with", "participated in", "in charge of"]
JUDGE_NAMES = {
    "J1": "Screen software can read it",
    "J2": "Names the job",
    "J3": "Covers every must-have",
    "J4": "Six-second skim",
    "J5": "Best work first",
    "J6": "Speaks the post's language",
}
MECH_NAMES = {"M1": "Filler words", "M2": "Weak openers", "M3": "Results", "M4": "Length"}
VERDICTS = [(6, "We regret to inform you."), (8, "We'll keep your resume on file."),
            (10, "We are pleased to inform you.")]

COMMENT = re.compile(r"<!--.*?-->", re.S)
BLANK = re.compile(r"\[ADD:[^\]]*\]", re.I)
BULLET = re.compile(r"^\s*-\s+(.*\S)\s*$")


class InputError(Exception):
    pass


def phrase_pattern(phrase):
    return re.compile(r"\b" + re.escape(phrase).replace(r"\ ", r"\s+") + r"\b", re.I)


FILLER_PATTERNS = [(p, phrase_pattern(p)) for p in FILLER]
WEAK_PATTERN = re.compile(r"^(?:" + "|".join(phrase_pattern(p).pattern for p in WEAK_OPENERS) + ")",
                          re.I)


def bullets_of(lines):
    found = []
    for line in lines:
        match = BULLET.match(line)
        if match:
            found.append(match.group(1))
    return found


def experience_bullets(lines):
    """Bullets under the first two ### roles of the first ## section named experience."""
    in_section, roles, current = False, 0, None
    collected = []
    for line in lines:
        if re.match(r"^##(?!#)", line):
            if in_section:
                break
            in_section = "experience" in line.lower()
            roles, current = 0, None
        elif in_section and line.startswith("###"):
            roles += 1
            current = roles if roles <= 2 else None
        elif in_section and current:
            match = BULLET.match(line)
            if match:
                collected.append(match.group(1))
    return collected


def check_filler(text):
    found = [phrase for phrase, pattern in FILLER_PATTERNS if pattern.search(text)]
    return ("FAIL" if len(found) >= 3 else "PASS",
            ", ".join(found) if found else "no filler phrases found")


def check_openers(bullets):
    weak = [b for b in bullets if WEAK_PATTERN.match(b)]
    evidence = "; ".join('"' + b[:60] + '"' for b in weak) if weak else "no weak openers"
    return ("FAIL" if len(weak) >= 2 else "PASS", evidence)


def check_results(lines):
    bullets = experience_bullets(lines)
    if not bullets:
        return "FAIL", "no experience bullets found"
    shown = sum(1 for b in bullets if re.search(r"[0-9]", b))
    return ("PASS" if shown * 2 >= len(bullets) else "FAIL",
            "%d of %d bullets in the two most recent roles show a number" % (shown, len(bullets)))


def check_length(lines, bullets):
    words = 0
    for line in lines:
        line = re.sub(r"^\s*(?:#+|-)", " ", line).replace("|", " ")
        words += len(line.split())
    longest = max((len(b.split()) for b in bullets), default=0)
    ok = words <= 700 and longest <= 40
    return "PASS" if ok else "FAIL", "%d words total, longest bullet %d words" % (words, longest)


def mechanical(raw):
    """Return (checks, blanks) for resume text."""
    text = COMMENT.sub("", raw)
    if not text.strip():
        raise InputError("the resume is empty")
    blanks = len(BLANK.findall(text))
    body = BLANK.sub("", text)
    lines = body.splitlines()
    bullets = bullets_of(lines)
    # Role and degree lines (###) name real titles: "Communication" in a degree is not filler.
    prose = "\n".join(line for line in lines if not line.startswith("###"))
    results = [check_filler(prose), check_openers(bullets), check_results(lines),
               check_length(lines, bullets)]
    checks = [{"id": key, "name": MECH_NAMES[key], "result": r, "evidence": e}
              for key, (r, e) in zip(MECH_NAMES, results)]
    return checks, blanks


def load_judgments(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as error:
        raise InputError("cannot read the judgments file: %s" % error)
    except (ValueError, UnicodeDecodeError) as error:
        raise InputError("the judgments file is not valid JSON: %s" % error)
    if not isinstance(data, dict):
        raise InputError("the judgments file must be a JSON object with keys J1 to J6")
    missing = [k for k in JUDGE_NAMES if k not in data]
    extra = [k for k in data if k not in JUDGE_NAMES]
    if missing:
        raise InputError("judgments missing: " + ", ".join(missing))
    if extra:
        raise InputError("unexpected judgment keys: " + ", ".join(map(str, extra)))
    checks = []
    for key, name in JUDGE_NAMES.items():
        entry = data[key]
        if not isinstance(entry, dict) or entry.get("result") not in ("PASS", "FAIL"):
            raise InputError("%s result must be exactly PASS or FAIL" % key)
        parts = []
        for field in ("why", "evidence"):
            value = entry.get(field, "")
            if not isinstance(value, str):
                raise InputError("%s %s must be a string" % (key, field))
            parts.append(value.strip())
        why, proof = parts
        evidence = "%s Evidence: %s" % (why, proof) if why and proof else why or proof
        checks.append({"id": key, "name": name, "result": entry["result"], "evidence": evidence})
    return checks


def verdict_for(passed):
    for top, line in VERDICTS:
        if passed <= top:
            return line


def cell(text):
    return " ".join(str(text).split()).replace("|", "\\|")


def render(checks, passed, verdict, blanks):
    out = ["| Check | Result | Evidence |", "|---|---|---|"]
    for c in checks:
        out.append("| %s %s | %s | %s |" % (c["id"], cell(c["name"]), c["result"], cell(c["evidence"])))
    out.append("")
    if verdict:
        out += ["**Passed: %d of 10**" % passed, "", "**%s**" % verdict]
    else:
        out.append("Mechanical checks only: %d of 4 passed. Add Claude's six judgment checks "
                   "for the full score." % passed)
    if blanks:
        out += ["", "Draft: %d blanks to fill before sending." % blanks]
    return "\n".join(out)


def run(args):
    try:
        raw = Path(args.resume).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise InputError("cannot read the resume: %s" % error)
    checks, blanks = mechanical(raw)
    if args.judgments:
        checks += load_judgments(args.judgments)
    passed = sum(1 for c in checks if c["result"] == "PASS")
    verdict = verdict_for(passed) if args.judgments else None
    if args.json:
        return json.dumps({"checks": checks, "passed": passed, "total": len(checks),
                           "verdict": verdict, "blanks": blanks}, indent=2)
    return render(checks, passed, verdict, blanks)


def main():
    parser = argparse.ArgumentParser(description="Score a resume markdown file.")
    parser.add_argument("resume")
    parser.add_argument("--judgments", help="JSON file with Claude's J1 to J6 results")
    parser.add_argument("--json", action="store_true", help="print one JSON object")
    args = parser.parse_args()
    try:
        print(run(args))
    except InputError as error:
        print("score.py: %s" % error, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
