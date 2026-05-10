"""
Chunking Strategy: Fixed-size with overlap + sentence boundary awareness.

Strategy:
- Split text into chunks of ~500 tokens (~2000 chars) with 10% overlap (~200 chars)
- Overlap ensures context is not lost at chunk boundaries
- Sentence boundary snapping: after computing the raw split point, we walk
  backward to the nearest sentence end ('. ', '! ', '? ') so chunks
  never cut mid-sentence.
- Each chunk carries metadata: doc_id, filename, page (if available), chunk_index
"""

import re
from typing import List
from dataclasses import dataclass

from app.config import Settings


@dataclass
class Chunk:
    """A single chunk of text with its metadata."""
    text: str
    doc_id: str
    filename: str
    chunk_index: int
    page: int | None = None


def _snap_to_sentence_end(text: str, pos: int, window: int) -> int:
    """
    Given a raw split position, walk backwards within `window` chars
    to find the nearest sentence boundary. Returns adjusted position.
    """
    search_start = max(0, pos - window)
    segment = text[search_start:pos]
    # Find last sentence-ending punctuation followed by space or end
    matches = list(re.finditer(r"[.!?][\s]", segment))
    if matches:
        last = matches[-1]
        return search_start + last.end()
    return pos  # fallback: use raw position


def chunk_text(
    text: str,
    doc_id: str,
    filename: str,
    settings: Settings,
    page: int | None = None,
) -> List[Chunk]:
    """
    Chunk a block of text using fixed-size + overlap + sentence snapping.
    Returns a list of Chunk objects.
    """
    text = text.strip()
    if not text:
        return []

    chunk_size = settings.CHUNK_SIZE
    chunk_overlap = settings.CHUNK_OVERLAP
    snap_window = settings.SNAP_WINDOW

    chunks = []
    start = 0
    chunk_index = 0

    while start < len(text):
        end = start + chunk_size

        if end < len(text):
            # Snap end to nearest sentence boundary
            end = _snap_to_sentence_end(text, end, snap_window)

        chunk_text_content = text[start:end].strip()
        if chunk_text_content:
            chunks.append(Chunk(
                text=chunk_text_content,
                doc_id=doc_id,
                filename=filename,
                chunk_index=chunk_index,
                page=page,
            ))
            chunk_index += 1

        # Move start forward by (chunk_size - chunk_overlap)
        start += chunk_size - chunk_overlap

    return chunks


def chunk_pages(
    pages: List[dict],
    doc_id: str,
    filename: str,
    settings: Settings,
) -> List[Chunk]:
    """
    Chunk a list of page dicts: [{"page": 1, "text": "..."}]
    Each page is chunked independently so page metadata is preserved.
    """
    all_chunks = []
    for page_data in pages:
        page_chunks = chunk_text(
            text=page_data["text"],
            doc_id=doc_id,
            filename=filename,
            settings=settings,
            page=page_data.get("page"),
        )
        all_chunks.extend(page_chunks)
    return all_chunks
