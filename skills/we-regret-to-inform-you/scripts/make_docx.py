#!/usr/bin/env python3
"""Make a simple resume DOCX using Python 3.9+ and the standard library.

Usage: python3 make_docx.py RESUME.md RESUME.docx
Markdown: # title, ## section, ### role, - bullet, or a plain paragraph.
JSON: {"blocks": [{"type": "title", "text": "Name"}, ...]}
Types: title, heading1, heading2, bullet, paragraph. Text is always literal.
HTML comments in Markdown are omitted. No inline Markdown is interpreted.
"""
import argparse
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
REL = "http://schemas.openxmlformats.org/package/2006/relationships"
OFFICE_REL = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
XML = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
STYLES = {"title": "Title", "heading1": "Heading1", "heading2": "Heading2",
          "bullet": "ListBullet", "paragraph": "Normal"}


def xml_text(text):
    if any(not (c in "\t\n\r" or 0x20 <= ord(c) <= 0xD7FF
                or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF)
           for c in text):
        raise ValueError("Input contains a character that XML cannot represent")
    return escape(text, {'"': "&quot;", "'": "&apos;"})


def read_blocks(path):
    source = Path(path)
    text = source.read_text(encoding="utf-8-sig")
    if source.suffix.lower() == ".json":
        data = json.loads(text)
        blocks = data.get("blocks") if isinstance(data, dict) else None
        if not isinstance(blocks, list):
            raise ValueError('JSON must contain a "blocks" list')
    else:
        text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
        blocks = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            kind = "paragraph"
            for prefix, candidate in [("### ", "heading2"), ("## ", "heading1"),
                                      ("# ", "title"), ("- ", "bullet")]:
                if line.startswith(prefix):
                    kind, line = candidate, line[len(prefix):]
                    break
            blocks.append({"type": kind, "text": line})
    if not blocks:
        raise ValueError("Resume is empty")
    for block in blocks:
        if (not isinstance(block, dict) or block.get("type") not in STYLES
                or not isinstance(block.get("text"), str) or not block["text"].strip()):
            raise ValueError("Each block needs a supported type and nonempty text")
    return blocks


def paragraph(block):
    kind, text = block["type"], block["text"]
    props = f'<w:pStyle w:val="{STYLES[kind]}"/>'
    if kind == "bullet":
        props += '<w:numPr><w:ilvl w:val="0"/><w:numId w:val="1"/></w:numPr>'
    runs = []
    for i, line in enumerate(text.split("\n")):
        if i:
            runs.append("<w:r><w:br/></w:r>")
        runs.append(f'<w:r><w:t xml:space="preserve">{xml_text(line)}</w:t></w:r>')
    return f'<w:p><w:pPr>{props}</w:pPr>{"".join(runs)}</w:p>'


def styles_xml():
    normal = ('<w:style w:type="paragraph" w:default="1" w:styleId="Normal">'
              '<w:name w:val="Normal"/><w:qFormat/>'
              '<w:pPr><w:widowControl/>'
              '<w:spacing w:after="80" w:line="250" w:lineRule="auto"/></w:pPr></w:style>')
    styles = [normal]
    for sid, name, size, before, after, outline in [
        ("Title", "Title", 32, 0, 60, None),
        ("Heading1", "heading 1", 22, 180, 60, 0),
        ("Heading2", "heading 2", 22, 120, 40, 1),
        ("ListBullet", "List Bullet", 22, 0, 60, None),
    ]:
        props = "<w:keepNext/><w:keepLines/>" if sid != "ListBullet" else ""
        props += f'<w:spacing w:before="{before}" w:after="{after}"/>'
        if sid == "ListBullet":
            props += '<w:ind w:left="240" w:hanging="180"/>'
        if outline is not None:
            props += f'<w:outlineLvl w:val="{outline}"/>'
        bold = "<w:b/><w:bCs/>" if sid != "ListBullet" else ""
        styles.append(f'<w:style w:type="paragraph" w:styleId="{sid}">'
                      f'<w:name w:val="{name}"/><w:basedOn w:val="Normal"/>'
                      '<w:next w:val="Normal"/><w:qFormat/>'
                      f'<w:pPr>{props}</w:pPr><w:rPr>{bold}<w:sz w:val="{size}"/>'
                      f'<w:szCs w:val="{size}"/></w:rPr></w:style>')
    return (f'<w:styles xmlns:w="{W}"><w:docDefaults><w:rPrDefault><w:rPr>'
            '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri" w:eastAsia="Calibri"/>'
            '<w:color w:val="000000"/><w:sz w:val="22"/><w:szCs w:val="22"/>'
            '<w:lang w:val="en-US"/></w:rPr></w:rPrDefault></w:docDefaults>'
            + "".join(styles) + '</w:styles>')


def write_docx(source, output):
    source, output = Path(source), Path(output)
    if source.resolve() == output.resolve():
        raise ValueError("Input and output must be different files")
    blocks = read_blocks(source)
    body = "".join(paragraph(block) for block in blocks)
    document = (f'<w:document xmlns:w="{W}"><w:body>{body}<w:sectPr>'
                '<w:pgSz w:w="12240" w:h="15840"/>'
                '<w:pgMar w:top="1080" w:right="1080" w:bottom="1080" w:left="1080"'
                ' w:header="0" w:footer="0" w:gutter="0"/>'
                '<w:cols w:num="1"/></w:sectPr></w:body></w:document>')
    numbering = (f'<w:numbering xmlns:w="{W}"><w:abstractNum w:abstractNumId="0">'
                 '<w:multiLevelType w:val="singleLevel"/><w:lvl w:ilvl="0">'
                 '<w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/>'
                 '<w:lvlJc w:val="left"/><w:pPr><w:tabs><w:tab w:val="num" w:pos="240"/>'
                 '</w:tabs><w:ind w:left="240" w:hanging="180"/></w:pPr>'
                 '<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/></w:rPr>'
                 '</w:lvl></w:abstractNum><w:num w:numId="1">'
                 '<w:abstractNumId w:val="0"/></w:num></w:numbering>')
    content_types = ('<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                     '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                     '<Default Extension="xml" ContentType="application/xml"/>')
    for part, kind in [("document", "document.main"), ("styles", "styles"), ("numbering", "numbering")]:
        content_types += (f'<Override PartName="/word/{part}.xml" ContentType="application/'
                          f'vnd.openxmlformats-officedocument.wordprocessingml.{kind}+xml"/>')
    content_types += "</Types>"
    root_rels = (f'<Relationships xmlns="{REL}"><Relationship Id="rId1"'
                 f' Type="{OFFICE_REL}/officeDocument" Target="word/document.xml"/></Relationships>')
    doc_rels = f'<Relationships xmlns="{REL}">'
    for i, part in enumerate(["styles", "numbering"], 1):
        doc_rels += (f'<Relationship Id="rId{i}" Type="{OFFICE_REL}/{part}" Target="{part}.xml"/>')
    doc_rels += "</Relationships>"
    parts = {"[Content_Types].xml": content_types, "_rels/.rels": root_rels,
             "word/document.xml": document, "word/styles.xml": styles_xml(),
             "word/numbering.xml": numbering, "word/_rels/document.xml.rels": doc_rels}
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_STORED) as archive:
        for name, content in sorted(parts.items()):
            info = zipfile.ZipInfo(name, (2026, 10, 15, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (XML + content).encode("utf-8"))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    try:
        print(write_docx(args.input, args.output))
    except (OSError, ValueError) as exc:
        print(f"Cannot make DOCX: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
