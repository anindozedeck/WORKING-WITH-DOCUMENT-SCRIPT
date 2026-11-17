"""Ask questions about a text-based PDF using local keyword search."""

from __future__ import annotations

import argparse
import math
import re
import sys
from collections import Counter
from pathlib import Path

try:
    from pypdf import PdfReader
    from pypdf.errors import PdfReadError
except ImportError as exc:
    raise SystemExit(
        "Missing dependency: pypdf. Install it with: python -m pip install -r requirements.txt"
    ) from exc


STOP_WORDS = frozenset(
    {
        "a",
        "about",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "can",
        "could",
        "did",
        "do",
        "does",
        "for",
        "from",
        "give",
        "how",
        "i",
        "in",
        "is",
        "it",
        "me",
        "of",
        "on",
        "or",
        "please",
        "tell",
        "that",
        "the",
        "this",
        "to",
        "was",
        "were",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
        "would",
        "you",
        "your",
    }
)
MAX_SNIPPET_LENGTH = 700


def tokenize(text: str) -> list[str]:
    """Return searchable words, excluding common question filler."""
    return [
        word
        for word in re.findall(r"\b[\w'-]+\b", text.lower())
        if word not in STOP_WORDS
    ]


def split_into_snippets(page_text: str, page_number: int) -> list[tuple[int, str]]:
    """Split extracted page text into readable, bounded passages."""
    normalized = page_text.replace("-\n", "")
    normalized = re.sub(r"\s*\n\s*", " ", normalized).strip()
    sentences = re.split(r"(?<=[.!?])\s+", normalized)

    snippets: list[tuple[int, str]] = []
    current = ""
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        if current and len(current) + len(sentence) + 1 > MAX_SNIPPET_LENGTH:
            snippets.append((page_number, current))
            current = ""

        while len(sentence) > MAX_SNIPPET_LENGTH:
            split_at = sentence.rfind(" ", 0, MAX_SNIPPET_LENGTH)
            if split_at < 1:
                split_at = MAX_SNIPPET_LENGTH
            piece, sentence = sentence[:split_at].strip(), sentence[split_at:].strip()
            if piece:
                snippets.append((page_number, piece))

        current = f"{current} {sentence}".strip()

    if current:
        snippets.append((page_number, current))
    return snippets


def extract_pdf_snippets(pdf_path: Path) -> list[tuple[int, str]]:
    """Extract text passages from a PDF, retaining one-based page numbers."""
    if not pdf_path.is_file():
        raise FileNotFoundError(f"PDF file not found: {pdf_path}")

    reader = PdfReader(str(pdf_path))
    if reader.is_encrypted:
        raise ValueError("This PDF is encrypted; provide an unencrypted PDF.")

    snippets: list[tuple[int, str]] = []
    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text() or ""
        snippets.extend(split_into_snippets(page_text, page_number))

    if not snippets:
        raise ValueError(
            "No selectable text was found. If this is a scanned PDF, run OCR on it first."
        )
    return snippets


def find_relevant_snippets(
    snippets: list[tuple[int, str]], question: str, top_k: int = 3
) -> list[tuple[int, str]]:
    """Rank passages by weighted keyword overlap with the question."""
    query_terms = set(tokenize(question))
    if not query_terms:
        return []

    document_terms = [set(tokenize(text)) for _, text in snippets]
    document_frequency = Counter(
        term for terms in document_terms for term in terms
    )
    total_documents = len(snippets)
    query_weight = {
        term: math.log(1 + total_documents / (1 + document_frequency[term]))
        for term in query_terms
    }
    total_query_weight = sum(query_weight.values())

    ranked: list[tuple[float, int, str]] = []
    for (page_number, text), terms in zip(snippets, document_terms):
        matched_weight = sum(query_weight[term] for term in query_terms & terms)
        if matched_weight:
            ranked.append((matched_weight / total_query_weight, page_number, text))

    ranked.sort(key=lambda result: result[0], reverse=True)
    return [(page_number, text) for _, page_number, text in ranked[:top_k]]


def ask_questions(snippets: list[tuple[int, str]], top_k: int) -> None:
    print("PDF loaded. Ask a question, or type 'quit' to exit.")
    while True:
        try:
            question = input("\nQuestion: ").strip()
        except EOFError:
            print()
            return

        if question.lower() in {"quit", "exit", "q"}:
            return
        if not question:
            continue

        results = find_relevant_snippets(snippets, question, top_k)
        if not results:
            print("No matching terms found. Try using words that appear in the PDF.")
            continue

        print("Relevant passages (check the cited pages for context):")
        for page_number, text in results:
            print(f"\n[Page {page_number}] {text}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Find relevant passages in a PDF and answer questions with page citations."
    )
    parser.add_argument(
        "pdf",
        nargs="?",
        help="PDF file path (if omitted, you'll be prompted for it)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="number of passages to show for each question (default: 3)",
    )
    args = parser.parse_args()
    if args.top_k < 1:
        parser.error("--top-k must be at least 1")

    pdf_input = args.pdf
    if not pdf_input:
        pdf_input = input("Enter the path to your PDF: ").strip().strip('"')
    if not pdf_input:
        parser.error("a PDF path is required")

    try:
        snippets = extract_pdf_snippets(Path(pdf_input).expanduser())
    except (FileNotFoundError, OSError, ValueError, PdfReadError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    ask_questions(snippets, args.top_k)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())