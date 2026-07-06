"""
Word-document question importer for the exam builder.

A .docx file is a zip archive whose main body lives in word/document.xml, so
paragraphs can be extracted with the standard library alone — deliberately no
python-docx/lxml dependency (Vercel bundle size, docs/01 §6 "no heavyweight
deps for narrow features").

Expected document format (one question per block, blank lines optional):

    1. What does CPU stand for?
    A) Central Processing Unit
    B) Computer Personal Unit
    C) Central Process Utility
    D) Control Processing Unit
    Answer: A
    Marks: 2                  <- optional, defaults to 1
    Explanation: ...          <- optional

Accepted variants: "Q1." / "1)" / "Question 1:" for the question line;
"A." / "(a)" / "a)" for options; "Ans: B" / "Correct Answer: (b)" for the
answer. Parsing is forgiving per-question: valid questions import, broken
ones come back as errors naming the question number and what's missing.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from typing import List, Optional, Tuple
from xml.etree import ElementTree

W_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

# Question start: "1." "1)" "Q1." "Question 1:" — captures number + text
QUESTION_RE = re.compile(r"^(?:q(?:uestion)?\s*)?(\d{1,3})\s*[.)\:\-]\s*(\S.*)$", re.IGNORECASE)
# Option line: "A)" "A." "(a)" "[B]" — captures letter + text
OPTION_RE = re.compile(r"^[(\[]?\s*([a-dA-D])\s*[.)\]\:\-]\s*(\S.*)$")
# Answer line: "Answer: A" "Ans - (b)" "Correct Answer: C"
ANSWER_RE = re.compile(
    r"^(?:correct\s+)?ans(?:wer)?\s*[.:\-]?\s*[(\[]?\s*([a-dA-D])\s*[)\]]?\s*$",
    re.IGNORECASE,
)
MARKS_RE = re.compile(r"^marks?\s*[.:\-]?\s*(\d{1,3})\s*$", re.IGNORECASE)
EXPLANATION_RE = re.compile(r"^explanation\s*[.:\-]\s*(\S.*)$", re.IGNORECASE)


class DocxParseError(Exception):
    """The uploaded file is not a readable .docx document."""


@dataclass
class ParsedQuestion:
    number: int
    question_text: str = ""
    options: dict = field(default_factory=dict)  # 'A'..'D' -> text
    correct_option: Optional[str] = None
    marks: int = 1
    explanation: Optional[str] = None

    def problems(self) -> List[str]:
        issues = []
        if not self.question_text.strip():
            issues.append("question text is empty")
        missing = [letter for letter in "ABCD" if not self.options.get(letter, "").strip()]
        if missing:
            issues.append(f"missing option(s) {', '.join(missing)}")
        if not self.correct_option:
            issues.append('no answer line (add e.g. "Answer: A")')
        return issues


def extract_docx_lines(data: bytes) -> List[str]:
    """All logical text lines of the document, in order. Soft line breaks
    (Shift+Enter) split into separate lines just like real paragraphs;
    table-cell text is included because table paragraphs are ordinary w:p
    nodes in document order."""
    try:
        with zipfile.ZipFile(BytesIO(data)) as zf:
            xml = zf.read("word/document.xml")
    except (zipfile.BadZipFile, KeyError) as exc:
        raise DocxParseError("Not a valid .docx file") from exc
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError as exc:
        raise DocxParseError("Could not read the document contents") from exc

    lines: List[str] = []
    for para in root.iter(f"{W_NS}p"):
        parts: List[str] = []
        for node in para.iter():
            if node.tag == f"{W_NS}t":
                parts.append(node.text or "")
            elif node.tag in (f"{W_NS}br", f"{W_NS}cr"):
                parts.append("\n")
        for line in "".join(parts).split("\n"):
            line = line.strip()
            if line:
                lines.append(line)
    return lines


def parse_questions(lines: List[str]) -> Tuple[List[ParsedQuestion], List[str]]:
    """Parse text lines into questions + human-readable error strings.

    Only questions with all four options and an answer are returned; every
    discarded block contributes one error explaining why.
    """
    questions: List[ParsedQuestion] = []
    errors: List[str] = []
    current: Optional[ParsedQuestion] = None
    # What multi-line text we're inside of: question text until the first
    # option appears, explanation once "Explanation:" was seen.
    appending_to: Optional[str] = None

    def close_current():
        nonlocal current
        if current is None:
            return
        issues = current.problems()
        if issues:
            errors.append(f"Question {current.number}: {'; '.join(issues)}")
        else:
            questions.append(current)
        current = None

    for line in lines:
        q_match = QUESTION_RE.match(line)
        # An option/answer/marks line can never start a question — check the
        # specific patterns first so "2. Marks: ..." style ambiguity resolves
        # toward the current block.
        if current is not None:
            option = OPTION_RE.match(line)
            # Option letters only count while the block is still collecting
            # options; afterwards "D) ..." inside an explanation stays text.
            if option and current.correct_option is None:
                letter = option.group(1).upper()
                current.options[letter] = option.group(2).strip()
                appending_to = f"option_{letter}"
                continue
            answer = ANSWER_RE.match(line)
            if answer:
                current.correct_option = answer.group(1).upper()
                appending_to = None
                continue
            marks = MARKS_RE.match(line)
            if marks:
                current.marks = max(1, int(marks.group(1)))
                appending_to = None
                continue
            explanation = EXPLANATION_RE.match(line)
            if explanation:
                current.explanation = explanation.group(1).strip()
                appending_to = "explanation"
                continue

        if q_match:
            close_current()
            current = ParsedQuestion(number=int(q_match.group(1)), question_text=q_match.group(2).strip())
            appending_to = "question_text"
            continue

        # Continuation line: extend whatever multi-line field is open.
        if current is not None and appending_to == "question_text" and not current.options:
            current.question_text += " " + line
        elif current is not None and appending_to == "explanation":
            current.explanation = (current.explanation or "") + " " + line
        elif current is not None and appending_to and appending_to.startswith("option_"):
            letter = appending_to.removeprefix("option_")
            current.options[letter] = f"{current.options.get(letter, '')} {line}".strip()
        elif current is None:
            # Prose before the first question (title, instructions) is fine —
            # silently skipped.
            continue

    close_current()

    if not questions and not errors:
        errors.append(
            "No questions found. Expected numbered questions like "
            '"1. Question text" followed by options "A) … D)" and "Answer: A".'
        )
    return questions, errors
