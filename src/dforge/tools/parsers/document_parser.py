"""Document intake parsers for free text, Markdown, TXT, and structured files (T-101)."""

from pathlib import Path
from typing import Union


class DocumentParser:
    """Extracts raw text and metadata from uploaded client brief files."""

    @staticmethod
    def parse_text(text: str, filename: str = "raw_input.txt") -> str:
        """Parse raw text or pasted email/meeting notes."""
        if not text or not text.strip():
            raise ValueError("Input text cannot be empty.")
        return text.strip()

    @classmethod
    def parse_file(cls, file_path: Union[str, Path]) -> str:
        """Parse text from file path supporting .txt, .md, .markdown."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        suffix = path.suffix.lower()
        if suffix in [".txt", ".md", ".markdown"]:
            return path.read_text(encoding="utf-8").strip()
        else:
            # Fallback for plain text readable files
            try:
                return path.read_text(encoding="utf-8").strip()
            except Exception as e:
                raise ValueError(f"Unsupported or unreadable file format '{suffix}': {e}")
