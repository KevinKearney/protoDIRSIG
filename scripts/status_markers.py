#!/usr/bin/env python3
"""Status markers: every marker in the human documents is a term of the legend, used as the legend allows.

    python scripts/status_markers.py            # list every marker found (file, line, build, agreement)
    python scripts/status_markers.py --check    # exit 1 and list the problems if any rule fails

The legend is stated once, in the CONOPS (`docs/MANIFOLD_DIRSIG_CONOPS_and_Guide.md`, Part II) and mirrored in
`api/README.md`, each between the lines `<!-- status-legend -->` and `<!-- /status-legend -->`; text inside those
blocks is not scanned. Two axes:

- build: `planned` (no code at HEAD), `built, partial` (code at HEAD, limits stated with the marker), `built` (code at
  HEAD with evidence named);
- agreement: `open` (a question for MANIFOLD, no position taken), `proposed` (offered to MANIFOLD, not agreed),
  `agreed` (the C-n row's Outcome is accepted), `internal` (an SDK-side contract not offered to MANIFOLD).

Scanned documents: the CONOPS, `api/*.md`, `api/openapi.yaml`, the descriptions in `api/schemas/*.json`, `README.md`
and `BACKLOG.md`. Fenced code blocks are not scanned.

What is a marker. A backtick span whose whole content is a legend term, or two terms joined by " / ", for example
`built / proposed`. A backtick span of the form `<words> / <words>` where a side is not a legend term is a marker
with a term outside the legend. In a table whose header has `Build` and `Agreement` columns, those two cells are the
marker of the row: the Build cell starts with one backticked build term (or is `—` when the Agreement cell is `open`;
an open question with nothing to build), and the Agreement cell is one backticked agreement term.

Rules, each a failure:

1. term outside the legend: a slash-form marker with a side that is not a legend term; a Build or Agreement cell
   whose term is not a term of that axis; a table with a `Status` column holding a backticked legend term (the table
   needs Build and Agreement columns instead); an unbackticked marker word used as a marker, that is `proposed`,
   `planned`, `internal` or `agreed` directly after `(` or `, ` and directly before `)`, `,`, `;` or `:`, or
   capitalized as a sentence of its own (`Proposed.`), or a `Status:` line whose value is not a backticked
   two-axis marker.
2. one axis only: every marker outside the Build and Agreement columns, in headings, bold-lead paragraphs, table
   cells and prose alike, is written `build / agreement`. The single exception is `open` alone: a question for
   MANIFOLD that takes no position and has nothing built SDK-side. A build term alone or `proposed`, `internal`,
   `agreed` alone fails.
3. order and axis: the first term of a slash form is a build term and the second an agreement term; so `proposed`,
   `open`, `agreed` and `internal` may not stand first, nor `planned` or `built` second.
4. `agreed` only where a C-n is accepted: the scope of the marker (see below) names at least one `C-n`, and every
   `C-n` it names has the Outcome `accepted` in the convergence table; in that table, the row's own Outcome.
5. evidence: a `built` or `built, partial` marker needs, in its scope, a backticked evidence item: a path under
   `tests/` or `notebooks/` or `manifold_contracts/vectors/`, or a test file name `test_*.py`, or a test function
   name `test_*` defined in `tests/`. Every evidence item named in the scope must exist at HEAD.
6. limits: a `built, partial` marker states its limits: in a Build cell, words (backtick spans not counted) follow
   the marker in the same cell; in prose, at least three words (backtick spans not counted) follow the marker before
   the sentence ends; on a heading, the section's text before its first subheading contains the word "Limits".

Scope: the table row for a marker in a table; the paragraph (one line, by this repository's convention) for a marker
in prose or a bold-lead paragraph; for a marker on a heading, the heading and its section, subsections included, up
to the next heading of the same or a higher level.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONOPS = "docs/MANIFOLD_DIRSIG_CONOPS_and_Guide.md"

BUILD = ("built, partial", "built", "planned")
AGREE = ("open", "proposed", "agreed", "internal")
TERMS = BUILD + AGREE
LEGEND_OPEN, LEGEND_CLOSE = "<!-- status-legend -->", "<!-- /status-legend -->"

SPAN = re.compile(r"`([^`\n]+)`")
SLASH = re.compile(r"^([a-z][a-z ,]*?) / ([a-z][a-z ,]*?)$")
BARE = re.compile(r"(?:\(|, )(proposed|planned|internal|agreed)(?=[),;:])")
LEAD = re.compile(r"(?:^|\. )(Proposed|Planned|Internal|Agreed)\.")
STATUS_LINE = re.compile(r"\bStatus: (?!`)(\S+)")
EVIDENCE_PATH = re.compile(r"^(tests/|notebooks/|manifold_contracts/vectors/)\S*$")
TEST_NAME = re.compile(r"^(test_\w+)(\.py)?$")
CN = re.compile(r"\bC-(\d+)\b")


def documents(root):
    """The scanned documents, repository-relative, in a fixed order."""
    names = [CONOPS, "README.md", "BACKLOG.md"]
    names += sorted(str(p.relative_to(root)) for p in (root / "api").glob("*.md"))
    names += ["api/openapi.yaml"]
    names += sorted(str(p.relative_to(root)) for p in (root / "api" / "schemas").glob("*.json"))
    return [n for n in names if (root / n).exists()]


def schema_lines(text):
    """The description strings of a JSON schema, each as one line with its line number."""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        m = re.search(r'"description":\s*"((?:[^"\\]|\\.)*)"', line)
        if m:
            out.append((i, json.loads('"' + m.group(1) + '"')))
    return out


def test_names(root):
    """Test function names defined in tests/ and the test file names."""
    names = set()
    for p in (root / "tests").glob("*.py"):
        names.add(p.name)
        names |= set(re.findall(r"^\s*def (test_\w+)", p.read_text(), re.M))
    return names


def split_row(line):
    return [c.strip() for c in line.strip().strip("|").split("|")]


class Doc:
    """One document as numbered lines, with code blocks and the legend block removed, and its tables parsed."""

    def __init__(self, name, text):
        self.name = name
        if name.endswith(".json"):
            self.lines = schema_lines(text)
        else:
            self.lines, fence, legend = [], False, False
            for i, line in enumerate(text.splitlines(), 1):
                s = line.strip()
                if s.startswith("```"):
                    fence = not fence
                    continue
                if s == LEGEND_OPEN:
                    legend = True
                if s == LEGEND_CLOSE:
                    legend = False
                    continue
                if not (fence or legend) and not line.startswith("    "):
                    self.lines.append((i, line))
        self.tables = {}                       # line number -> (header cells, cells)
        header = None
        for i, line in self.lines:
            if line.startswith("|"):
                cells = split_row(line)
                if header is None:
                    header = cells
                elif not all(set(c) <= set("-: ") for c in cells):
                    self.tables[i] = (header, cells)
            else:
                header = None


def markers_in(text):
    """(term or (build, agreement), span text) for each backticked marker candidate in text."""
    out = []
    for m in SPAN.finditer(text):
        s = m.group(1).strip()
        if s in TERMS:
            out.append(((s,), s, m.end()))
        else:
            sm = SLASH.match(s)
            if sm:
                out.append(((sm.group(1).strip(), sm.group(2).strip()), s, m.end()))
    return out


def outcomes(conops_doc):
    """{n: outcome} from the convergence table."""
    out = {}
    for i, (header, cells) in conops_doc.tables.items():
        if header and header[0] == "ID" and cells and CN.fullmatch(cells[0]):
            out[int(CN.fullmatch(cells[0]).group(1))] = cells[header.index("Outcome")] if "Outcome" in header else ""
    return out


def sections(doc):
    """For each heading line number, its section (subsections included) up to the next heading of its level or higher."""
    heads = [(i, len(line) - len(line.lstrip("#"))) for i, line in doc.lines if line.startswith("#")]
    out = {}
    for k, (i, level) in enumerate(heads):
        end = next((j for j, lv in heads[k + 1:] if lv <= level), 10 ** 9)
        out[i] = "\n".join(l for j, l in doc.lines if i <= j < end)
    return out


def check_doc(doc, root, accepted, tests):
    """The problems of one document, and the markers found as (line, build, agreement)."""
    problems, found = [], []
    secs = sections(doc) if not doc.name.endswith(".json") else {}

    def where(i):
        return f"{doc.name}:{i}"

    def evidence(i, scope, label):
        items = [s.strip() for s in SPAN.findall(scope)]
        ev = [s for s in items if EVIDENCE_PATH.match(s)]
        names = [s for s in items if TEST_NAME.match(s)]
        missing = [s for s in ev if not (root / s.rstrip("/")).exists()] + [s for s in names if s not in tests]
        for s in missing:
            problems.append(f"{where(i)}: {label} names evidence `{s}`, which does not exist")
        if not [s for s in ev + names if s not in missing]:
            problems.append(f"{where(i)}: {label} without named evidence (a tests/ or notebooks/ path or a test name)")

    def agreed(i, scope, own=None):
        ids = [own] if own is not None else [int(n) for n in CN.findall(scope)]
        if not ids:
            problems.append(f"{where(i)}: `agreed` names no C-n")
        for n in ids:
            if accepted.get(n, "").strip("* ").lower() != "accepted":
                problems.append(f"{where(i)}: `agreed` but C-{n:02d} has no accepted Outcome")

    def limits(i, text, after, heading_scope=None):
        if heading_scope is not None:
            body = heading_scope.split("\n", 1)[1] if "\n" in heading_scope else ""
            if "limits" not in body.split("\n#")[0].lower():
                problems.append(f"{where(i)}: `built, partial` heading whose section states no limits")
            return
        rest = re.split(r"(?<=[.!?])\s", text[after:], maxsplit=1)[0]
        if len(re.findall(r"\w+", SPAN.sub("", rest))) < 3:
            problems.append(f"{where(i)}: `built, partial` without its limits in the same sentence")

    def validate(i, terms, span, text, after, scope, heading_scope=None, own=None):
        if len(terms) == 1:
            t = terms[0]
            if t != "open":
                problems.append(f"{where(i)}: `{span}` gives one axis; write `build / agreement` (only `open` stands alone)")
                return
            found.append((i, "", "open"))
            return
        b, a = terms
        bad = [t for t in terms if t not in TERMS]
        if bad:
            problems.append(f"{where(i)}: `{span}`: term outside the legend: {', '.join(bad)}")
            return
        if b not in BUILD or a not in AGREE:
            problems.append(f"{where(i)}: `{span}`: the build term comes first and the agreement term second")
            return
        found.append((i, b, a))
        if a == "agreed":
            agreed(i, scope, own)
        if b.startswith("built"):
            evidence(i, heading_scope or scope, f"`{span}`")
        if b == "built, partial":
            limits(i, text, after, heading_scope)

    for i, line in doc.lines:
        for m in list(BARE.finditer(line)) + list(LEAD.finditer(line)):
            problems.append(f"{where(i)}: unbackticked marker word `{m.group(1)}`; write a backticked `build / agreement` marker")
        sm = STATUS_LINE.search(line)
        if sm:
            problems.append(f"{where(i)}: `Status:` line with value {sm.group(1)!r}; write a backticked `build / agreement` marker")
        row = doc.tables.get(i)
        if row:
            header, cells = row
            own = None
            if header and header[0] == "ID" and cells and CN.fullmatch(cells[0]):
                own = int(CN.fullmatch(cells[0]).group(1))
            if "Status" in header and len(cells) == len(header):
                cell = cells[header.index("Status")]
                if [m for m in markers_in(cell)]:
                    problems.append(f"{where(i)}: a Status column holding a marker; use Build and Agreement columns")
            if "Build" in header and "Agreement" in header and len(cells) == len(header):
                bc, ac = cells[header.index("Build")], cells[header.index("Agreement")]
                am = re.fullmatch(r"`([^`]+)`", ac)
                a = am.group(1) if am else ac
                if a not in AGREE:
                    problems.append(f"{where(i)}: Agreement cell {ac!r} is not an agreement term")
                bm = re.match(r"`([^`]+)`", bc)
                if bc == "—":
                    if a != "open":
                        problems.append(f"{where(i)}: an empty Build cell is allowed only with `open`")
                    else:
                        found.append((i, "", a))
                elif not bm or bm.group(1) not in BUILD:
                    problems.append(f"{where(i)}: Build cell {bc!r} does not start with a build term")
                elif a in AGREE:
                    b = bm.group(1)
                    found.append((i, b, a))
                    if a == "agreed":
                        agreed(i, line, own)
                    if b.startswith("built"):
                        evidence(i, line, f"Build `{b}`")
                    if b == "built, partial" and not re.search(r"\w", SPAN.sub("", bc[bm.end():])):
                        problems.append(f"{where(i)}: Build `built, partial` without its limits in the cell")
                skip = {header.index("Build"), header.index("Agreement")}
                other = " | ".join(c for k, c in enumerate(cells) if k not in skip)
            else:
                other = line
            for terms, span, after in markers_in(other):
                validate(i, terms, span, other, after, line, own=own)
            continue
        heading = line.startswith("#")
        for terms, span, after in markers_in(line):
            validate(i, terms, span, line, after, line, heading_scope=secs.get(i) if heading else None)
    return problems, found


def run(root=ROOT):
    """(problems, notices, markers) for the repository at root."""
    docs = {n: Doc(n, (root / n).read_text()) for n in documents(root)}
    accepted = outcomes(docs[CONOPS])
    tests = test_names(root)
    problems, markers = [], []
    for name, doc in docs.items():
        p, found = check_doc(doc, root, accepted, tests)
        problems += p
        markers += [(name, i, b, a) for i, b, a in found]
    return problems, [], markers


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="exit 1 if any rule fails")
    args = ap.parse_args(argv)
    problems, notices, markers = run()
    if not args.check:
        for name, i, b, a in markers:
            print(f"{name}\t{i}\t{b}\t{a}")
    for n in notices:
        print(f"notice: {n}", file=sys.stderr)
    for p in problems:
        print(p, file=sys.stderr)
    if args.check:
        print(f"status_markers: {len(markers)} markers, {len(problems)} problems", file=sys.stderr)
        return 1 if problems else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
