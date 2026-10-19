#!/usr/bin/env python3
"""Flag new numbers and capitalized multi-word names, not prove truth.

Usage: python3 check_facts.py ORIGINAL.md RESUME.md [JOB.md]
Exit 0: no flags; 1: additions to review; 2: input error.
Job wording can explain a name flag, never a new number. Even an old number can
be assigned to a different claim; tools, roles and claims need a human/model audit.
"""
import argparse
import re
import sys
import unicodedata
from pathlib import Path

NUMBER = re.compile(r"(?<!\w)[+−-]?[$€£]?\d+(?:,\d{3})*(?:\.\d+)?(?:[%+]|[kKmMbB]\b)?(?!\w)")
WORD = re.compile(r"[^\W\d_][\w'’]*(?:[.-][^\W\d_][\w'’]*)*", re.UNICODE)
CONNECTORS = {"of", "the", "and", "for", "in", "at", "&"}


def clean(text):
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    return re.sub(r"\[ADD:[^\]]*\]", "", text, flags=re.I)


def normalize(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def names(text):
    """Consecutive capitalized words, allowing connectors, within a line."""
    found = []
    for line in text.splitlines():
        tokens = list(WORD.finditer(line))
        i = 0
        while i < len(tokens):
            if not tokens[i].group()[0].isupper():
                i += 1
                continue
            start, end, capitals = i, i, 1
            j = i + 1
            while j < len(tokens):
                gap = line[tokens[j - 1].end():tokens[j].start()]
                word = tokens[j].group()
                if not gap or not re.fullmatch(r"\s+(?:&\s+)?", gap):
                    break
                if word[0].isupper():
                    capitals += 1
                    end = j
                elif word not in CONNECTORS:
                    break
                j += 1
            if capitals >= 2:
                found.append(line[tokens[start].start():tokens[end].end()])
            i = max(end + 1, i + 1)
    return found


def present(phrase, text):
    return re.search(r"(?<!\w)" + re.escape(normalize(phrase)) + r"(?!\w)", normalize(text)) is not None


def check_facts(old, new, job=""):
    old, new, job = clean(old), clean(new), clean(job)
    known_numbers = {normalize(m.group()).replace(",", "") for m in NUMBER.finditer(old)}
    flags, seen = [], set()
    for match in NUMBER.finditer(new):
        value = match.group()
        key = ("number", normalize(value).replace(",", ""))
        if key[1] not in known_numbers and key not in seen:
            flags.append(("number", value))
            seen.add(key)
    for value in names(new):
        key = ("name", normalize(value))
        if key not in seen and not present(value, old) and not present(value, job):
            flags.append(("name", value))
            seen.add(key)
    return flags


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("original", type=Path)
    parser.add_argument("rewrite", type=Path)
    parser.add_argument("job", type=Path, nargs="?")
    args = parser.parse_args()
    try:
        flags = check_facts(args.original.read_text(encoding="utf-8-sig"),
                            args.rewrite.read_text(encoding="utf-8-sig"),
                            args.job.read_text(encoding="utf-8-sig") if args.job else "")
    except (OSError, UnicodeError) as exc:
        print(f"Cannot check facts: {exc}", file=sys.stderr)
        return 2
    if flags:
        for kind, value in flags:
            print(f"REVIEW {kind}: {value}")
        return 1
    print("No new numbers or capitalized multi-word names found. Still audit every claim.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
