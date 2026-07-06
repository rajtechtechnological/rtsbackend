"""Unit tests for the exam-builder Word importer (no DB needed)."""

import zipfile
from io import BytesIO

import pytest

from app.utils.docx_parser import (
    DocxParseError,
    extract_docx_lines,
    parse_questions,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def make_docx(paragraphs):
    """Minimal .docx: one w:p per entry; embedded '\n' becomes a soft w:br."""
    body = []
    for para in paragraphs:
        runs = []
        for i, segment in enumerate(para.split("\n")):
            if i > 0:
                runs.append("<w:br/>")
            runs.append(f"<w:t>{segment}</w:t>")
        body.append(f"<w:p><w:r>{''.join(runs)}</w:r></w:p>")
    document = (
        f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<w:document xmlns:w="{W_NS}"><w:body>{"".join(body)}</w:body></w:document>'
    )
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", document)
    return buf.getvalue()


SIMPLE_DOC = [
    "Module 1 Test — General Instructions",  # prose before questions: ignored
    "1. What does CPU stand for?",
    "A) Central Processing Unit",
    "B) Computer Personal Unit",
    "C) Central Process Utility",
    "D) Control Processing Unit",
    "Answer: A",
    "Marks: 2",
    "Explanation: CPU is the processor.",
    "",
    "Q2) Which is an input device?",
    "(a) Monitor",
    "(b) Keyboard",
    "(c) Printer",
    "(d) Speaker",
    "Correct Answer: B",
]


def test_happy_path_two_questions():
    lines = extract_docx_lines(make_docx(SIMPLE_DOC))
    questions, errors = parse_questions(lines)

    assert errors == []
    assert len(questions) == 2

    q1 = questions[0]
    assert q1.question_text == "What does CPU stand for?"
    assert q1.options["A"] == "Central Processing Unit"
    assert q1.options["D"] == "Control Processing Unit"
    assert q1.correct_option == "A"
    assert q1.marks == 2
    assert q1.explanation == "CPU is the processor."

    q2 = questions[1]
    assert q2.question_text == "Which is an input device?"
    assert q2.correct_option == "B"
    assert q2.marks == 1  # default
    assert q2.explanation is None


def test_soft_line_breaks_within_one_paragraph():
    doc = make_docx([
        "1. Soft-break question?\nA) one\nB) two\nC) three\nD) four\nAns: C"
    ])
    questions, errors = parse_questions(extract_docx_lines(doc))
    assert errors == []
    assert questions[0].correct_option == "C"


def test_missing_option_and_answer_reported_per_question():
    doc = make_docx([
        "1. Complete question?",
        "A) yes", "B) no", "C) maybe", "D) sure",
        "Answer: D",
        "2. Broken question — no option D or answer",
        "A) x", "B) y", "C) z",
    ])
    questions, errors = parse_questions(extract_docx_lines(doc))
    assert len(questions) == 1  # the valid one still imports
    assert len(errors) == 1
    assert "Question 2" in errors[0]
    assert "option(s) D" in errors[0]
    assert "no answer line" in errors[0]


def test_multiline_question_and_option_text():
    doc = make_docx([
        "1. A question that continues",
        "onto a second paragraph?",
        "A) first option also",
        "continues here",
        "B) two", "C) three", "D) four",
        "Answer: A",
    ])
    questions, errors = parse_questions(extract_docx_lines(doc))
    assert errors == []
    assert questions[0].question_text == "A question that continues onto a second paragraph?"
    assert questions[0].options["A"] == "first option also continues here"


def test_option_like_text_after_answer_is_not_an_option():
    doc = make_docx([
        "1. Q?",
        "A) 1", "B) 2", "C) 3", "D) 4",
        "Answer: B",
        "Explanation: because option",
        "B) is the standard answer",  # looks like an option, must stay explanation
    ])
    questions, errors = parse_questions(extract_docx_lines(doc))
    assert errors == []
    assert questions[0].options["B"] == "2"
    assert "standard answer" in questions[0].explanation


def test_empty_document_gives_guidance():
    questions, errors = parse_questions(extract_docx_lines(make_docx(["hello"])))
    assert questions == []
    assert len(errors) == 1
    assert "No questions found" in errors[0]


def test_not_a_docx_raises():
    with pytest.raises(DocxParseError):
        extract_docx_lines(b"this is not a zip")
    # a zip without word/document.xml is also rejected
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("other.txt", "x")
    with pytest.raises(DocxParseError):
        extract_docx_lines(buf.getvalue())
