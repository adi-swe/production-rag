import logging
import re
from typing import Optional

logger = logging.getLogger("rag_curator.processing.cleaner")


class TextPreprocessor:
    """
    A class for cleaning and preprocessing text extracted from PDFs.
    """

    def clean_text(self, text: str) -> str:
        if not text:
            logger.info("TextPreprocessor received empty text; returning empty string.")
            return ""

        logger.info("Starting text cleaning for %d characters", len(text))
        text = self._normalize_newlines(text)
        text = self._fix_hyphenated_words(text)
        text = self._remove_page_numbers(text)
        text = self._normalize_whitespace(text)

        cleaned = text.strip()
        logger.info("Text cleaning complete. Output length: %d characters", len(cleaned))
        return cleaned

    @staticmethod
    def _normalize_newlines(text: str) -> str:
        """
        Normalize different newline formats.
        """

        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        return text

    @staticmethod
    def _fix_hyphenated_words(text: str) -> str:
        """
        Join words broken across PDF line boundaries.

        Example:

            retriev-
            al

        becomes:

            retrieval
        """

        return re.sub(
            r"(\w)-\s*\n\s*(\w)",
            r"\1\2",
            text,
        )

    @staticmethod
    def _remove_page_numbers(text: str) -> str:
        """
        Remove lines containing only page numbers.
        """

        lines = text.split("\n")

        cleaned_lines = []

        for line in lines:
            if re.fullmatch(r"\s*\d+\s*", line):
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    @staticmethod
    def _normalize_whitespace(text: str) -> str:
        """
        Normalize excessive spaces and blank lines.
        """

        text = re.sub(r"[ \t]+", " ", text)

        text = re.sub(
            r"\n{3,}",
            "\n\n",
            text,
        )

        return text


    def remove_headers_and_footers(self, text: str) -> str:
        """
        Remove headers and footers based on provided regex patterns.

        Args:
            text (str): The input text.
        Returns:
            str: The text with headers and footers removed.
        """
        lines = text.split('\n')
        original_lines = len(lines)
        if len(lines) > 5:
            lines = lines[3:-3]
        logger.info(
            "Removed header/footer lines: %d -> %d",
            original_lines,
            len(lines),
        )
        return '\n'.join(lines)

    def extract_abstract(self, text: str, max_length: int = 300) -> Optional[str]:
        """
        Extract the abstract section from the text.

        Args:
            text (str): The input text.
            max_length (int): The maximum length of the extracted abstract.
        Returns:
            Optional[str]: The extracted abstract section, or None if not found.
        """
        patterns = [
            r'(?:Abstract|ABSTRACT|abstract)\s*[:\-]?\s*([^.!?]{50,}[.!?])',
            r'(?:Summary|SUMMARY|summary)\s*[:\-]?\s*([^.!?]{50,}[.!?])',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                extracted = match.group(1).strip()[:max_length]
                logger.info("Extracted abstract via pattern %s (%d chars)", pattern, len(extracted))
                return extracted

        logger.info("No abstract pattern matched the supplied text.")
        return None