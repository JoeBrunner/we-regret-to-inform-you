import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/we-regret-to-inform-you/scripts/make_docx.py"
SPEC = importlib.util.spec_from_file_location("make_docx", SCRIPT)
DOCX = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DOCX)
NS = {"w": DOCX.W}
W = "{" + DOCX.W + "}"
SAMPLE = ROOT / "examples/sample-resume.md"


class DocxTests(unittest.TestCase):
    def setUp(self):
        scratch = ROOT / "we-regret-to-inform-you"
        scratch.mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name)
        self.output = self.work / "resume.docx"
        DOCX.write_docx(SAMPLE, self.output)

    def document(self):
        with zipfile.ZipFile(self.output) as archive:
            return ET.fromstring(archive.read("word/document.xml"))

    def test_package_parts_parse_and_relationships_resolve(self):
        expected = {"[Content_Types].xml", "word/document.xml", "word/styles.xml",
                    "_rels/.rels", "word/_rels/document.xml.rels", "word/numbering.xml"}
        with zipfile.ZipFile(self.output) as archive:
            self.assertEqual(set(archive.namelist()), expected)
            self.assertIsNone(archive.testzip())
            for name in expected:
                ET.fromstring(archive.read(name))
            for relfile, base in [("_rels/.rels", ""), ("word/_rels/document.xml.rels", "word/")]:
                for rel in ET.fromstring(archive.read(relfile)):
                    self.assertIn(base + rel.get("Target"), expected)

    def test_heading_and_bullet_styles(self):
        document = self.document()
        paragraphs = document.findall(".//w:body/w:p", NS)
        text_styles = [("".join(p.itertext()), p.find("w:pPr/w:pStyle", NS).get(W + "val"))
                       for p in paragraphs]
        for block, (text, style) in zip(DOCX.read_blocks(SAMPLE), text_styles):
            self.assertEqual(text, block["text"])
            self.assertEqual(style, DOCX.STYLES[block["type"]])
        self.assertEqual(len(text_styles), len(DOCX.read_blocks(SAMPLE)))
        bullets = [p for p in paragraphs if p.find("w:pPr/w:pStyle", NS).get(W + "val") == "ListBullet"]
        self.assertGreater(len(bullets), 0)
        for p in bullets:
            self.assertEqual(p.find("w:pPr/w:numPr/w:numId", NS).get(W + "val"), "1")
        with zipfile.ZipFile(self.output) as archive:
            styles = ET.fromstring(archive.read("word/styles.xml"))
            ids = {s.get(W + "styleId") for s in styles.findall("w:style", NS)}
            self.assertEqual(ids, set(DOCX.STYLES.values()))

    def test_special_characters_and_unicode_round_trip(self):
        text = 'Renée & José <Support> "customers" O\'Neil – “ready”'
        source = self.work / "special.md"
        source.write_text("# " + text + "\n- " + text, encoding="utf-8")
        DOCX.write_docx(source, self.output)
        self.assertEqual([n.text for n in self.document().findall(".//w:t", NS)], [text, text])
        with zipfile.ZipFile(self.output) as archive:
            xml = archive.read("word/document.xml").decode()
            for escaped in ("&amp;", "&lt;", "&gt;", "&quot;", "&apos;"):
                self.assertIn(escaped, xml)

    def test_plain_letter_layout_and_font(self):
        document = self.document()
        for tag in ("tbl", "drawing", "pict", "txbxContent", "headerReference", "footerReference"):
            self.assertIsNone(document.find(".//w:" + tag, NS))
        section = document.find(".//w:sectPr", NS)
        self.assertEqual(section.find("w:pgSz", NS).attrib, {W + "w": "12240", W + "h": "15840"})
        self.assertEqual(section.find("w:cols", NS).get(W + "num"), "1")
        for side in ("top", "bottom", "left", "right"):
            self.assertEqual(section.find("w:pgMar", NS).get(W + side), "1080")
        with zipfile.ZipFile(self.output) as archive:
            styles = ET.fromstring(archive.read("word/styles.xml"))
        self.assertEqual(styles.find(".//w:docDefaults//w:rFonts", NS).get(W + "ascii"), "Calibri")
        self.assertEqual(styles.find(".//w:docDefaults//w:sz", NS).get(W + "val"), "22")

    def test_json_and_markdown_produce_same_document(self):
        source = self.work / "resume.json"
        source.write_text(json.dumps({"blocks": DOCX.read_blocks(SAMPLE)}), encoding="utf-8")
        other = self.work / "json.docx"
        DOCX.write_docx(source, other)
        self.assertEqual(self.output.read_bytes(), other.read_bytes())
        self.assertNotIn("Entirely fictional", "".join(self.document().itertext()))

    def test_invalid_input_does_not_overwrite_output(self):
        before = self.output.read_bytes()
        for content in ('{"blocks": [{"type": "table", "text": "bad"}]}', '{"blocks": []}'):
            source = self.work / "invalid.json"
            source.write_text(content, encoding="utf-8")
            with self.assertRaises(ValueError):
                DOCX.write_docx(source, self.output)
            self.assertEqual(self.output.read_bytes(), before)
        source = self.work / "invalid.md"
        source.write_text("# Name\x00", encoding="utf-8")
        with self.assertRaises(ValueError):
            DOCX.write_docx(source, self.output)
        self.assertEqual(self.output.read_bytes(), before)
        with self.assertRaises(ValueError):
            DOCX.write_docx(source, source)

    def test_cli(self):
        result = subprocess.run([sys.executable, str(SCRIPT), str(SAMPLE), str(self.output)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(zipfile.is_zipfile(self.output))

    @unittest.skipUnless(sys.platform == "darwin" and Path("/usr/bin/textutil").exists(),
                         "macOS textutil is not available")
    def test_textutil_reads_name_headings_and_bullet(self):
        result = subprocess.run(["/usr/bin/textutil", "-convert", "txt", "-stdout", str(self.output)],
                                capture_output=True, text=True, check=True)
        for block in DOCX.read_blocks(SAMPLE):
            if block["type"] in ("title", "heading1", "heading2", "bullet"):
                self.assertIn(block["text"], result.stdout)

    @unittest.skipUnless(shutil.which("soffice"), "LibreOffice soffice is not on PATH")
    def test_soffice_produces_pdf(self):
        profile = (self.work / "lo-profile").as_uri()
        result = subprocess.run([shutil.which("soffice"), f"-env:UserInstallation={profile}",
                                 "--headless", "--convert-to", "pdf", "--outdir", str(self.work),
                                 str(self.output)], capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        pdf = self.output.with_suffix(".pdf")
        self.assertTrue(pdf.exists(), result.stdout + result.stderr)
        self.assertGreater(pdf.stat().st_size, 100)
        self.assertTrue(pdf.read_bytes().startswith(b"%PDF-"))


if __name__ == "__main__":
    unittest.main()
