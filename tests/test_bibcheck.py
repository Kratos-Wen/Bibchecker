#!/usr/bin/env python3
"""Unit tests for BibCheck."""

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bibtex_refiner import (
    normalize_text,
    similarity,
    titles_match_exactly,
    authors_match_strictly,
    author_similarity,
    author_tokens,
    generate_citation_key,
    CanonicalBib,
    BibliographicResolver,
)


class TestUtilFunctions(unittest.TestCase):
    """Test utility functions."""

    def test_normalize_text_basic(self) -> None:
        """Test basic text normalization."""
        self.assertEqual(normalize_text("Hello World"), "hello world")
        self.assertEqual(normalize_text("Test-123"), "test 123")
        self.assertEqual(normalize_text("  Multiple   Spaces  "), "multiple spaces")

    def test_normalize_text_special_chars(self) -> None:
        """Test normalization of special characters."""
        # Special chars are removed/converted to spaces
        self.assertEqual(normalize_text("Façade"), "fa ade")
        self.assertEqual(normalize_text("Über"), "ber")

    def test_similarity_perfect_match(self) -> None:
        """Test similarity for identical strings."""
        self.assertGreaterEqual(similarity("hello", "hello"), 0.99)

    def test_similarity_partial_match(self) -> None:
        """Test similarity for similar strings."""
        sim = similarity("hello world", "hello word")
        self.assertGreater(sim, 0.7)
        self.assertLess(sim, 1.0)

    def test_similarity_empty_strings(self) -> None:
        """Test similarity for empty strings."""
        self.assertEqual(similarity("", ""), 1.0)
        self.assertEqual(similarity("hello", ""), 0.0)
        self.assertEqual(similarity("", "world"), 0.0)

    def test_author_tokens(self) -> None:
        """Test author tokenization."""
        tokens = author_tokens("John Smith and Jane Doe")
        self.assertIn("john smith", tokens)
        self.assertIn("jane doe", tokens)

    def test_author_similarity_same_authors(self) -> None:
        """Test author similarity for identical author lists."""
        sim = author_similarity("John Smith and Jane Doe", "John Smith and Jane Doe")
        self.assertGreater(sim, 0.95)

    def test_titles_match_exactly_identical(self) -> None:
        """Test exact title matching for identical titles."""
        self.assertTrue(titles_match_exactly("A Novel Method", "a novel method"))
        self.assertTrue(titles_match_exactly("Test Paper 2024", "test paper 2024"))

    def test_titles_match_exactly_different(self) -> None:
        """Test exact title matching rejects different titles."""
        self.assertFalse(titles_match_exactly("A Novel Method", "A Novel Approach"))
        self.assertFalse(titles_match_exactly("Paper A", "Paper B"))
        self.assertFalse(titles_match_exactly("Test", ""))

    def test_titles_match_exactly_special_chars(self) -> None:
        """Test exact matching handles special characters."""
        self.assertTrue(titles_match_exactly("Test {Title}", "test title"))
        self.assertTrue(titles_match_exactly("A*B", "a b"))

    def test_authors_match_strictly_identical(self) -> None:
        """Test author matching for identical author lists."""
        self.assertTrue(authors_match_strictly(
            "John Smith and Jane Doe",
            "John Smith and Jane Doe"
        ))
        # Different formats (comma-separated vs space-separated) are not considered identical
        self.assertFalse(authors_match_strictly(
            "Smith, John and Doe, Jane",
            "John Smith and Jane Doe"
        ))

    def test_authors_match_strictly_order_matters(self) -> None:
        """Test that author order matters."""
        self.assertFalse(authors_match_strictly(
            "John Smith and Jane Doe",
            "Jane Doe and John Smith"
        ))

    def test_authors_match_strictly_missing_author(self) -> None:
        """Test that missing author is rejected."""
        self.assertFalse(authors_match_strictly(
            "John Smith and Jane Doe",
            "John Smith and Jane Doe and Bob Johnson"
        ))
        self.assertFalse(authors_match_strictly(
            "John Smith and Jane Doe",
            "John Smith"
        ))

    def test_authors_match_strictly_et_al_input(self) -> None:
        """Test et al. handling in input."""
        # Input with et al. can match database with same first author + more authors
        self.assertTrue(authors_match_strictly(
            "John Smith et al.",
            "John Smith and Jane Doe and Bob Johnson"
        ))
        # But the first author must match exactly
        self.assertFalse(authors_match_strictly(
            "Smith et al.",
            "John Smith and Jane Doe and Bob Johnson"
        ))

    def test_authors_match_strictly_et_al_database(self) -> None:
        """Test et al. handling in database record."""
        # Database with et al. can match input with same first author + more authors
        self.assertTrue(authors_match_strictly(
            "John Smith and Jane Doe and Bob Johnson",
            "John Smith et al."
        ))
        # But the first author must match exactly
        self.assertFalse(authors_match_strictly(
            "John Smith and Jane Doe and Bob Johnson",
            "Smith et al."
        ))

    def test_generate_citation_key(self) -> None:
        """Test citation key generation."""
        entry = {
            "author": "Smith, John",
            "title": "A Novel Method for Something",
            "year": "2024",
        }
        key = generate_citation_key(entry)
        self.assertIsInstance(key, str)
        self.assertGreater(len(key), 0)
        self.assertIn("smith", key.lower())
        self.assertIn("24", key)


class TestCanonicalBib(unittest.TestCase):
    """Test CanonicalBib dataclass."""

    def test_to_entry_basic(self) -> None:
        """Test conversion to BibTeX entry."""
        bib = CanonicalBib(
            source="dblp",
            bibtex_type="inproceedings",
            title="Test Paper",
            author="John Smith",
            year="2024",
        )
        entry = bib.to_entry()
        self.assertEqual(entry["ENTRYTYPE"], "inproceedings")
        self.assertEqual(entry["title"], "Test Paper")
        self.assertEqual(entry["author"], "John Smith")

    def test_to_entry_empty_fields(self) -> None:
        """Test that empty fields are not included."""
        bib = CanonicalBib(
            source="dblp",
            bibtex_type="article",
            title="",
            author="",
        )
        entry = bib.to_entry()
        self.assertNotIn("title", entry)
        self.assertNotIn("author", entry)


class TestBibliographicResolver(unittest.TestCase):
    """Test BibliographicResolver."""

    def setUp(self) -> None:
        """Set up test fixtures."""
        self.resolver = BibliographicResolver(timeout=5)

    def test_resolve_entry_no_candidates(self) -> None:
        """Test resolving an entry with no candidates."""
        entry = {"ID": "test2024", "ENTRYTYPE": "article"}
        with patch.object(self.resolver, "_collect_candidates", return_value=[]):
            result = self.resolver.resolve_entry(entry)
        
        self.assertEqual(result.key, "test2024")
        self.assertFalse(result.changed)
        self.assertEqual(result.confidence, 0.0)

    def test_resolve_entry_with_high_confidence_candidate(self) -> None:
        """Test resolving with a high-confidence candidate."""
        entry = {
            "ID": "test2024",
            "ENTRYTYPE": "inproceedings",
            "title": "A Test Paper",
            "author": "John Smith and Jane Doe",
            "year": "2024",
        }
        
        candidate = CanonicalBib(
            source="dblp",
            bibtex_type="inproceedings",
            title="A Test Paper",
            author="John Smith and Jane Doe",
            year="2024",
            confidence=0.85,
        )
        
        with patch.object(self.resolver, "_collect_candidates", return_value=[candidate]):
            result = self.resolver.resolve_entry(entry)
        
        # With publication-grade verification, exact matches should have high confidence
        self.assertTrue(result.confidence > 0.7 or result.changed)

    def test_score_candidate_doi_match(self) -> None:
        """Test candidate scoring with DOI match."""
        entry = {
            "title": "Test Paper",
            "author": "John Smith",
            "year": "2024",
            "doi": "10.1234/example",
        }
        
        candidate = CanonicalBib(
            source="dblp",
            bibtex_type="article",
            title="Test Paper",
            author="John Smith",
            year="2024",
            doi="10.1234/example",
        )
        
        score = self.resolver._score_candidate(entry, candidate)
        self.assertGreater(score, 0.7)

    def test_score_candidate_doi_mismatch(self) -> None:
        """Test candidate scoring with DOI mismatch."""
        entry = {
            "title": "Test Paper",
            "doi": "10.1234/wrong",
        }
        
        candidate = CanonicalBib(
            source="dblp",
            bibtex_type="article",
            title="Test Paper",
            doi="10.1234/correct",
        )
        
        score = self.resolver._score_candidate(entry, candidate)
        self.assertEqual(score, 0.0)

    def test_score_candidate_title_mismatch(self) -> None:
        """Test candidate scoring with non-identical title (publication-grade)."""
        entry = {
            "title": "A Novel Method",
            "author": "John Smith",
            "year": "2024",
        }
        
        candidate = CanonicalBib(
            source="dblp",
            bibtex_type="article",
            title="A Novel Approach",  # Different from input
            author="John Smith",
            year="2024",
        )
        
        score = self.resolver._score_candidate(entry, candidate)
        self.assertEqual(score, 0.0)  # Must be exact match

    def test_score_candidate_author_order_matters(self) -> None:
        """Test that author order matters in scoring."""
        entry = {
            "title": "Test Paper",
            "author": "John Smith and Jane Doe",
            "year": "2024",
        }
        
        candidate = CanonicalBib(
            source="dblp",
            bibtex_type="article",
            title="Test Paper",
            author="Jane Doe and John Smith",  # Wrong order
            year="2024",
        )
        
        score = self.resolver._score_candidate(entry, candidate)
        self.assertEqual(score, 0.0)  # Wrong order = rejection

    def test_score_candidate_exact_match(self) -> None:
        """Test candidate scoring with exact match (publication-grade)."""
        entry = {
            "title": "A Novel Method",
            "author": "John Smith and Jane Doe",
            "year": "2024",
        }
        
        candidate = CanonicalBib(
            source="dblp",
            bibtex_type="inproceedings",
            title="A Novel Method",
            author="John Smith and Jane Doe",
            year="2024",
        )
        
        score = self.resolver._score_candidate(entry, candidate)
        self.assertGreater(score, 0.7)  # Exact match should pass


class TestIntegration(unittest.TestCase):
    """Integration tests."""

    def test_full_resolution_workflow(self) -> None:
        """Test a complete resolution workflow."""
        resolver = BibliographicResolver()
        entry = {
            "ID": "smith2024",
            "ENTRYTYPE": "article",
            "title": "Test Paper",
            "author": "John Smith",
            "year": "2024",
        }
        
        # This will not find real candidates, but should not crash
        result = resolver.resolve_entry(entry)
        
        self.assertEqual(result.key, "smith2024")
        self.assertIsNotNone(result.confidence)


if __name__ == "__main__":
    unittest.main()
