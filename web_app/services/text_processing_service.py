"""
Enhanced text processing service for Family Wiki Tools

Provides improved text cleaning and smart chunking using:
- Dutch genealogy-specific text cleaning
- LangChain RecursiveCharacterTextSplitter with generous overlap
- Daitch-Mokotoff Soundex generation for genealogy name matching
"""

import re

from abydos.phonetic import DaitchMokotoff
from langchain_text_splitters import RecursiveCharacterTextSplitter

from web_app.services.exceptions import handle_service_exceptions
from web_app.shared.logging_config import get_project_logger
from web_app.shared.text_cleaning import clean_corpus_text


logger = get_project_logger(__name__)


class TextProcessingService:
    """Service for advanced text cleaning and chunking"""

    def __init__(self):
        self.logger = get_project_logger(__name__)
        self.dm_soundex = DaitchMokotoff()

    @handle_service_exceptions(logger)
    def clean_text_for_rag(self, raw_text: str, *, spellfix: bool = True, remove_headers: bool = True) -> str:
        """
        Clean text using Dutch genealogy-specific preprocessing
        
        Args:
            raw_text: Raw input text
            spellfix: Whether to apply OCR spell correction
            remove_headers: Whether to remove page headers/footers
            
        Returns:
            Cleaned text ready for chunking
        """
        cleaned = clean_corpus_text(
            raw_text,
            spellfix=spellfix,
            remove_headers=remove_headers
        )

        self.logger.debug(f"Text cleaning: {len(raw_text)} -> {len(cleaned)} chars")
        return cleaned

    @handle_service_exceptions(logger)
    def smart_chunk_text(self, text: str, chunk_size: int = 1000, overlap_percentage: float = 0.15) -> list[str]:
        """
        Chunk text using LangChain's RecursiveCharacterTextSplitter with generous overlap
        
        Args:
            text: Cleaned text to chunk
            chunk_size: Target size for each chunk
            overlap_percentage: Overlap as percentage (0.15 = 15%)
            
        Returns:
            List of text chunks with smart boundaries
        """
        # Calculate overlap size (15% of chunk size)
        chunk_overlap = int(chunk_size * overlap_percentage)

        # Initialize the text splitter with genealogy-appropriate separators
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            is_separator_regex=False,
            # Genealogy-friendly separators (most important first)
            separators=[
                "\n\n\n",      # Triple line breaks (major sections)
                "\n\n",        # Double line breaks (paragraphs)
                "\n",          # Single line breaks
                ".",           # Sentences
                "!",           # Exclamations
                "?",           # Questions
                ";",           # Semicolons
                ",",           # Commas
                " ",           # Spaces
                "",            # Characters (last resort)
            ]
        )

        chunks = text_splitter.split_text(text)

        self.logger.info(f"Smart chunking: {len(text)} chars -> {len(chunks)} chunks "
                       f"(size: {chunk_size}, overlap: {chunk_overlap} = {overlap_percentage:.1%})")

        return chunks

    @handle_service_exceptions(logger)
    def _fallback_chunk_text(self, text: str, chunk_size: int, overlap_percentage: float) -> list[str]:
        """
        Fallback chunking method if LangChain fails
        
        Args:
            text: Text to chunk
            chunk_size: Target chunk size
            overlap_percentage: Overlap percentage
            
        Returns:
            List of text chunks using simple overlap
        """
        chunks = []
        chunk_overlap = int(chunk_size * overlap_percentage)
        start = 0

        while start < len(text):
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundaries
            if end < len(text) and '.' in chunk:
                last_period = chunk.rfind('.')
                if last_period > chunk_size // 2:  # Only if period is in latter half
                    end = start + last_period + 1
                    chunk = text[start:end]

            chunks.append(chunk.strip())
            start = end - chunk_overlap

            if start >= len(text):
                break

        self.logger.info(f"Fallback chunking: {len(text)} chars -> {len(chunks)} chunks")
        return chunks

    @handle_service_exceptions(logger)
    def process_corpus_content(self, raw_content: str, chunk_size: int = 1000,
                              overlap_percentage: float = 0.15, spellfix: bool = True) -> dict:
        """
        Complete pipeline: clean text and create smart chunks
        
        Args:
            raw_content: Raw corpus text
            chunk_size: Target chunk size
            overlap_percentage: Overlap percentage (0.15 = 15%)
            spellfix: Whether to apply spell correction
            
        Returns:
            Dict with cleaned_text, chunks, and processing stats
        """
        self.logger.info(f"Processing corpus content: {len(raw_content)} chars, "
                        f"chunk_size={chunk_size}, overlap={overlap_percentage:.1%}")

        # Step 1: Clean the text
        cleaned_text = self.clean_text_for_rag(raw_content, spellfix=spellfix)

        # Step 2: Create smart chunks
        try:
            chunks = self.smart_chunk_text(cleaned_text, chunk_size, overlap_percentage)
        except Exception as e:
            self.logger.warning(f"Smart chunking failed: {e}, falling back to simple chunking")
            chunks = self._fallback_chunk_text(cleaned_text, chunk_size, overlap_percentage)

        # Step 3: Generate processing statistics
        stats = {
            'original_length': len(raw_content),
            'cleaned_length': len(cleaned_text),
            'chunk_count': len(chunks),
            'avg_chunk_size': sum(len(chunk) for chunk in chunks) / len(chunks) if chunks else 0,
            'chunk_size_target': chunk_size,
            'overlap_percentage': overlap_percentage,
            'spellfix_applied': spellfix
        }

        self.logger.info(f"Processing complete: {stats['chunk_count']} chunks, "
                        f"avg size: {stats['avg_chunk_size']:.0f} chars")

        return {
            'cleaned_text': cleaned_text,
            'chunks': chunks,
            'stats': stats
        }

    @handle_service_exceptions(logger)
    def generate_daitch_mokotoff_codes(self, text: str) -> list[str]:
        """
        Generate Daitch-Mokotoff Soundex codes from text for genealogy name matching
        
        Args:
            text: Input text to extract names and generate soundex codes
            
        Returns:
            List of unique DM soundex codes found in the text
        """
        # Extract potential names from text (words that start with capital letters)
        # This is a simple heuristic for genealogy texts
        name_pattern = r'\b[A-Z][a-z]{2,}\b'  # Capitalized words with 3+ letters
        potential_names = re.findall(name_pattern, text)

        dm_codes = set()

        for name in potential_names:
            try:
                # Generate DM codes for this name
                codes = self.dm_soundex.encode(name)
                # DM soundex can return multiple codes, handle string, list, tuple, or set
                if isinstance(codes, str):
                    if codes:  # Only add non-empty codes
                        dm_codes.add(codes)
                elif isinstance(codes, (list, tuple, set)):
                    for code in codes:
                        if code:  # Only add non-empty codes
                            dm_codes.add(str(code))
            except Exception as e:
                self.logger.warning(f"Failed to generate DM codes for '{name}': {e}")
                continue

        unique_codes = list(dm_codes)
        self.logger.debug(f"Generated {len(unique_codes)} unique DM codes from {len(potential_names)} potential names")

        return unique_codes
