#!/usr/bin/env python3
"""Refine BibTeX entries using free bibliographic sources.

This tool is designed for computer-science and computer-vision papers where
DBLP is often the most stable source, while Crossref and OpenAlex provide
additional verification.

Usage:
  python bibtex_refiner.py input.bib -o output.bib
  python bibtex_refiner.py input.bib --report report.json

The tool does not use Google Scholar because Scholar has no stable public API.
Instead, it cross-checks across DBLP, Crossref, and OpenAlex and chooses the
most plausible canonical record.
"""

from __future__ import annotations

import argparse
import dataclasses
import difflib
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

try:
    import bibtexparser
    from bibtexparser.bwriter import BibTexWriter
except ImportError as exc:  # pragma: no cover - runtime dependency hint
    print(
        "Missing dependency: bibtexparser. Install it with `pip install -r requirements.txt`.",
        file=sys.stderr,
    )
    raise

try:
    import requests
except ImportError as exc:  # pragma: no cover - runtime dependency hint
    print(
        "Missing dependency: requests. Install it with `pip install -r requirements.txt`.",
        file=sys.stderr,
    )
    raise

LOGGER = logging.getLogger("bibtex_refiner")
USER_AGENT = "bibcheck/1.0 (+https://example.invalid)"
DEFAULT_TIMEOUT = 15

SOURCE_WEIGHTS = {
    "dblp": 1.00,
    "crossref": 0.92,
    "openalex": 0.90,
}


@dataclasses.dataclass
class CanonicalBib:
    source: str
    bibtex_type: str
    title: str = ""
    author: str = ""
    year: str = ""
    booktitle: str = ""
    journal: str = ""
    volume: str = ""
    number: str = ""
    pages: str = ""
    doi: str = ""
    url: str = ""
    publisher: str = ""
    institution: str = ""
    address: str = ""
    note: str = ""
    keywords: str = ""
    raw: Dict[str, Any] = dataclasses.field(default_factory=dict)
    confidence: float = 0.0

    def to_entry(self, entry_type: Optional[str] = None) -> Dict[str, str]:
        data: Dict[str, str] = {}
        bibtype = entry_type or self.bibtex_type or "misc"
        data["ENTRYTYPE"] = bibtype
        if self.author:
            data["author"] = self.author
        if self.title:
            data["title"] = self.title
        if self.year:
            data["year"] = self.year
        if self.booktitle:
            data["booktitle"] = self.booktitle
        if self.journal:
            data["journal"] = self.journal
        if self.volume:
            data["volume"] = self.volume
        if self.number:
            data["number"] = self.number
        if self.pages:
            data["pages"] = self.pages
        if self.doi:
            data["doi"] = self.doi
        if self.url:
            data["url"] = self.url
        if self.publisher:
            data["publisher"] = self.publisher
        if self.institution:
            data["institution"] = self.institution
        if self.address:
            data["address"] = self.address
        if self.note:
            data["note"] = self.note
        if self.keywords:
            data["keywords"] = self.keywords
        return data


@dataclasses.dataclass
class ResolutionResult:
    key: str
    resolved_key: str
    original: Dict[str, Any]
    resolved: Dict[str, Any]
    chosen_source: str = ""
    confidence: float = 0.0
    changed: bool = False
    reason: str = ""
    candidates: List[CanonicalBib] = dataclasses.field(default_factory=list)


class BibliographicResolver:
    def __init__(self, timeout: int = DEFAULT_TIMEOUT) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept": "application/json"})
        self.timeout = timeout

    def resolve_entry(self, entry: Dict[str, Any], force: bool = False, rewrite_keys: bool = False) -> ResolutionResult:
        key = entry.get("ID", "")
        candidates = self._collect_candidates(entry)
        best = self._choose_best_candidate(entry, candidates)
        resolved = dict(entry)
        resolved_key = key
        changed = False
        reason = "no candidate found"
        chosen_source = ""
        confidence = 0.0

        if best is not None and best.confidence >= 0.72:
            chosen_source = best.source
            confidence = best.confidence
            canonical_fields = best.to_entry(entry.get("ENTRYTYPE"))
            if force:
                resolved = {**entry, **{k: v for k, v in canonical_fields.items() if k != "ENTRYTYPE"}}
                resolved["ENTRYTYPE"] = canonical_fields["ENTRYTYPE"]
                changed = resolved != entry
                reason = f"forced replacement from {chosen_source}"
            else:
                resolved = self._merge_entry(entry, canonical_fields)
                changed = resolved != entry
                reason = f"merged with {chosen_source}"
        elif best is not None:
            chosen_source = best.source
            confidence = best.confidence
            reason = f"low confidence candidate from {chosen_source}"

        if rewrite_keys:
            resolved_key = generate_citation_key(resolved)
            if resolved_key and resolved_key != key:
                changed = True
                reason = f"{reason}; rewritten key"

        return ResolutionResult(
            key=key,
            resolved_key=resolved_key,
            original=entry,
            resolved=resolved,
            chosen_source=chosen_source,
            confidence=confidence,
            changed=changed,
            reason=reason,
            candidates=candidates,
        )

    def _merge_entry(self, original: Dict[str, Any], canonical: Dict[str, Any]) -> Dict[str, Any]:
        resolved = dict(original)
        entrytype = canonical.get("ENTRYTYPE", original.get("ENTRYTYPE", "misc"))
        resolved["ENTRYTYPE"] = entrytype

        # Replace only fields we can verify with high confidence.
        for field in ["author", "title", "year", "booktitle", "journal", "volume", "number", "pages", "doi", "url", "publisher", "institution", "address"]:
            value = canonical.get(field, "")
            if value:
                if field not in resolved or self._field_is_weaker(resolved.get(field, ""), value, field):
                    resolved[field] = value

        return resolved

    def _field_is_weaker(self, old: str, new: str, field: str) -> bool:
        old_norm = normalize_text(old)
        new_norm = normalize_text(new)
        if not old_norm:
            return True
        if old_norm == new_norm:
            return False
        if field == "author":
            # Prefer canonical author ordering if titles and identifiers match.
            return True
        return len(new_norm) > len(old_norm) or similarity(old_norm, new_norm) > 0.85

    def _collect_candidates(self, entry: Dict[str, Any]) -> List[CanonicalBib]:
        candidates: List[CanonicalBib] = []
        title = entry.get("title", "")
        doi = entry.get("doi", "")
        year = entry.get("year", "")

        if doi:
            candidates.extend(filter(None, [
                self._candidate_from_crossref_by_doi(doi),
                self._candidate_from_openalex_by_doi(doi),
            ]))

        if title:
            candidates.extend(filter(None, [
                *self._search_crossref(title),
                *self._search_openalex(title),
                *self._search_dblp(title),
            ]))

        # Deduplicate by normalized title + author.
        unique: Dict[Tuple[str, str, str], CanonicalBib] = {}
        for cand in candidates:
            key = (normalize_text(cand.title), normalize_text(cand.author), cand.year)
            if key not in unique or cand.confidence > unique[key].confidence:
                unique[key] = cand

        # Boost confidence if multiple sources agree on the same canonical record.
        grouped: Dict[Tuple[str, str], List[CanonicalBib]] = {}
        for cand in unique.values():
            group_key = (normalize_text(cand.title), cand.year)
            grouped.setdefault(group_key, []).append(cand)

        merged: List[CanonicalBib] = []
        for group in grouped.values():
            if len(group) == 1:
                merged.append(group[0])
                continue
            best = max(group, key=lambda c: (c.confidence, SOURCE_WEIGHTS.get(c.source, 0.0)))
            consensus_bonus = 0.04 * (len(group) - 1)
            best.confidence = min(0.99, best.confidence + consensus_bonus)
            merged.append(best)

        # Slightly prefer DBLP for conference/CS papers.
        for cand in merged:
            if cand.source == "dblp" and ("conference" in entry.get("ENTRYTYPE", "").lower() or entry.get("booktitle") or entry.get("pages")):
                cand.confidence = min(0.99, cand.confidence + 0.03)

        return sorted(merged, key=lambda c: c.confidence, reverse=True)

    def _choose_best_candidate(self, entry: Dict[str, Any], candidates: Sequence[CanonicalBib]) -> Optional[CanonicalBib]:
        if not candidates:
            return None
        scored: List[Tuple[float, CanonicalBib]] = []
        for cand in candidates:
            score = self._score_candidate(entry, cand)
            cand.confidence = score
            scored.append((score, cand))
        scored.sort(key=lambda item: item[0], reverse=True)
        return scored[0][1] if scored else None

    def _score_candidate(self, entry: Dict[str, Any], cand: CanonicalBib) -> float:
        """Score candidate for publication-grade bibliography verification.
        
        All checks are binary pass/fail (reject if mismatch):
        - Title must match exactly (100% after normalization)
        - Authors must match in order with exact names
        - Year must match
        - DOI must match if present
        """
        base = SOURCE_WEIGHTS.get(cand.source, 0.75)
        score = 0.20 * base
        
        # DOI match (highest priority)
        input_doi = clean_doi(entry.get("doi", ""))
        if input_doi and cand.doi:
            if input_doi == cand.doi:
                score += 0.35
            else:
                return 0.0  # DOI mismatch = reject
        
        # Title match: must be exact (100% requirement for publication)
        if not titles_match_exactly(entry.get("title", ""), cand.title):
            return 0.0
        score += 0.30
        
        # Author match: must be in order with exact names
        input_auth = entry.get("author", "")
        cand_auth = cand.author or ""
        if input_auth and cand_auth:
            if not authors_match_strictly(input_auth, cand_auth):
                return 0.0
            score += 0.20
        elif input_auth or cand_auth:
            return 0.0  # One has authors, other doesn't
        
        # Year match
        input_year = normalize_text(entry.get("year", ""))
        if input_year and cand.year:
            if input_year == normalize_text(cand.year):
                score += 0.10
            else:
                return 0.0  # Year mismatch = reject
        elif input_year or cand.year:
            return 0.0
        
        # Venue (bonus, not rejection)
        input_venue = normalize_text(entry.get("booktitle", "") or entry.get("journal", ""))
        cand_venue = normalize_text(cand.booktitle or cand.journal)
        if input_venue and cand_venue:
            venue_sim = similarity(input_venue, cand_venue)
            if venue_sim > 0.70:
                score += 0.05 * venue_sim
        
        return min(score, 0.99)

    def _candidate_from_crossref_by_doi(self, doi: str) -> Optional[CanonicalBib]:
        doi = clean_doi(doi)
        if not doi:
            return None
        data = self._get_json(f"https://api.crossref.org/works/{doi}")
        if not data or "message" not in data:
            return None
        return canonical_from_crossref(data["message"], source="crossref")

    def _candidate_from_openalex_by_doi(self, doi: str) -> Optional[CanonicalBib]:
        doi = clean_doi(doi)
        if not doi:
            return None
        data = self._get_json(f"https://api.openalex.org/works/https://doi.org/{doi}")
        if not data:
            return None
        return canonical_from_openalex(data, source="openalex")

    def _search_crossref(self, title: str) -> List[CanonicalBib]:
        params = {"query.title": title, "rows": 5}
        data = self._get_json("https://api.crossref.org/works", params=params)
        items = data.get("message", {}).get("items", []) if data else []
        return [canonical_from_crossref(item, source="crossref") for item in items if item]

    def _search_openalex(self, title: str) -> List[CanonicalBib]:
        params = {"search": title, "per-page": 5}
        data = self._get_json("https://api.openalex.org/works", params=params)
        results = data.get("results", []) if data else []
        return [canonical_from_openalex(item, source="openalex") for item in results if item]

    def _search_dblp(self, title: str) -> List[CanonicalBib]:
        params = {"q": title, "format": "json", "h": 5}
        data = self._get_json("https://dblp.org/search/publ/api", params=params)
        hits = (((data or {}).get("result", {}) or {}).get("hits", {}) or {}).get("hit", [])
        entries: List[CanonicalBib] = []
        for hit in hits:
            info = (hit or {}).get("info", {})
            if info:
                entries.append(canonical_from_dblp(info, source="dblp"))
        return entries

    def _get_json(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        try:
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            LOGGER.debug("Request failed for %s: %s", url, exc)
            return {}


def canonical_from_crossref(item: Dict[str, Any], source: str) -> CanonicalBib:
    authors = item.get("author", []) or []
    return CanonicalBib(
        source=source,
        bibtex_type=crossref_type_to_bibtex(item.get("type", "article-journal")),
        title=first_str(item.get("title")),
        author=format_authors_crossref(authors),
        year=extract_year(item.get("published-print") or item.get("published-online") or item.get("issued") or {}),
        journal=first_str(item.get("container-title")),
        volume=str(item.get("volume", "") or ""),
        number=str(item.get("issue", "") or ""),
        pages=first_str(item.get("page")),
        doi=clean_doi(item.get("DOI", "")),
        url=item.get("URL", "") or "",
        publisher=item.get("publisher", "") or "",
        raw=item,
    )


def canonical_from_openalex(item: Dict[str, Any], source: str) -> CanonicalBib:
    authorships = item.get("authorships", []) or []
    authors = []
    for auth in authorships:
        author = (auth or {}).get("author", {})
        name = author.get("display_name") or ""
        if name:
            authors.append(name)
    primary_location = item.get("primary_location", {}) or {}
    source_meta = primary_location.get("source", {}) or {}
    venue = source_meta.get("display_name", "") or ""
    doi = clean_doi(item.get("doi", ""))
    return CanonicalBib(
        source=source,
        bibtex_type=openalex_type_to_bibtex(item.get("type", "article")),
        title=item.get("title", "") or "",
        author=" and ".join(authors),
        year=str(item.get("publication_year", "") or ""),
        journal=venue if item.get("type", "") in {"journal-article", "article"} else "",
        booktitle=venue if item.get("type", "") not in {"journal-article", "article"} else "",
        volume=str(item.get("biblio", {}).get("volume", "") or ""),
        number=str(item.get("biblio", {}).get("issue", "") or ""),
        pages=pages_from_biblio(item.get("biblio", {}) or {}),
        doi=doi,
        url=item.get("id", "") or item.get("doi", "") or "",
        publisher=(item.get("host_venue", {}) or {}).get("publisher", "") or "",
        raw=item,
    )


def canonical_from_dblp(info: Dict[str, Any], source: str) -> CanonicalBib:
    authors = info.get("authors", {}).get("author", []) or []
    if isinstance(authors, dict):
        authors = [authors]
    author_names: List[str] = []
    for a in authors:
        if isinstance(a, dict):
            author_names.append(a.get("text", "") or "")
        elif isinstance(a, str):
            author_names.append(a)
    venue = info.get("venue", "") or ""
    year = str(info.get("year", "") or "")
    doi = clean_doi(info.get("doi", "") or "")
    url = info.get("url", "") or info.get("ee", "") or ""
    typ = dblp_type_to_bibtex(info.get("type", ""), venue=venue)
    pages = info.get("pages", "") or ""
    return CanonicalBib(
        source=source,
        bibtex_type=typ,
        title=info.get("title", "") or "",
        author=" and ".join(author_names),
        year=year,
        booktitle=venue if typ in {"inproceedings", "proceedings", "incollection"} else "",
        journal=venue if typ in {"article", "journal"} else "",
        pages=pages,
        doi=doi,
        url=url,
        publisher=info.get("publisher", "") or "",
        raw=info,
    )


def crossref_type_to_bibtex(type_name: str) -> str:
    type_name = (type_name or "").lower()
    if "proceedings" in type_name or "conference" in type_name or "book-part" in type_name:
        return "inproceedings"
    if "journal" in type_name or "article" in type_name:
        return "article"
    if "book" in type_name:
        return "book"
    return "misc"


def openalex_type_to_bibtex(type_name: str) -> str:
    type_name = (type_name or "").lower()
    if type_name in {"journal-article", "article"}:
        return "article"
    if type_name in {"proceedings-article", "conference-paper", "paper"}:
        return "inproceedings"
    if type_name == "book-chapter":
        return "incollection"
    return "misc"


def dblp_type_to_bibtex(type_name: str, venue: str = "") -> str:
    type_name = (type_name or "").lower()
    venue = (venue or "").lower()
    if type_name in {"journal articles", "article"} or "journal" in venue:
        return "article"
    if type_name in {"conference and workshop papers", "conference papers", "inproceedings"} or venue:
        return "inproceedings"
    return "misc"


def format_authors_crossref(authors: Sequence[Dict[str, Any]]) -> str:
    out: List[str] = []
    for author in authors:
        given = author.get("given", "") or ""
        family = author.get("family", "") or ""
        if family and given:
            out.append(f"{given} {family}")
        else:
            out.append(family or given)
    return " and ".join([name for name in out if name])


def extract_year(parts: Any) -> str:
    if isinstance(parts, dict):
        date_parts = parts.get("date-parts", []) or []
        if date_parts and isinstance(date_parts[0], list) and date_parts[0]:
            return str(date_parts[0][0])
    return ""


def pages_from_biblio(biblio: Dict[str, Any]) -> str:
    start = biblio.get("first_page", "") or ""
    end = biblio.get("last_page", "") or ""
    if start and end and start != end:
        return f"{start}--{end}"
    return start or end or ""


def first_str(value: Any) -> str:
    if isinstance(value, list):
        return str(value[0]) if value else ""
    if value is None:
        return ""
    return str(value)


def clean_doi(doi: Any) -> str:
    text = str(doi or "").strip()
    if not text:
        return ""
    text = re.sub(r"^https?://(dx\.)?doi\.org/", "", text, flags=re.I)
    return text.lower().strip()


def normalize_text(text: Any) -> str:
    value = str(text or "").lower()
    value = re.sub(r"[{}\\\\'`~^]", "", value)
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return value.strip()


def similarity(a: str, b: str) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def titles_match_exactly(title1: str, title2: str) -> bool:
    """Check if titles match exactly after normalization.
    
    For publication submission accuracy, titles must be 100% identical.
    """
    t1 = normalize_text(title1)
    t2 = normalize_text(title2)
    return bool(t1 and t2 and t1 == t2)


def authors_match_strictly(input_authors: str, db_authors: str) -> bool:
    """Check if authors match with strict order and name requirements.
    
    For publication submission:
    - Author order must be identical
    - All author names must match exactly (after normalization)
    - Missing even one author is a mismatch
    - Special: 'et al.' indicates there are more authors
    
    Args:
        input_authors: Authors from input BibTeX
        db_authors: Authors from database
    
    Returns:
        True if authors match sufficiently for publication
    """
    if not input_authors or not db_authors:
        return False
    
    # Detect et al before splitting (preserves "et al" as indicator)
    input_has_et_al = bool(re.search(r'\bet\s+al\.?', input_authors, re.IGNORECASE))
    db_has_et_al = bool(re.search(r'\bet\s+al\.?', db_authors, re.IGNORECASE))
    
    # Remove "et al" markers before splitting authors
    input_clean = re.sub(r'\s*\bet\s+al\.?', '', input_authors, flags=re.IGNORECASE).strip()
    db_clean = re.sub(r'\s*\bet\s+al\.?', '', db_authors, flags=re.IGNORECASE).strip()
    
    # Split by 'and' first - this separates actual authors
    # Both "and" AND "and" surrounded by spaces
    input_parts = [p.strip() for p in re.split(r'\s+and\s+', input_clean)]
    db_parts = [p.strip() for p in re.split(r'\s+and\s+', db_clean)]
    
    # Normalize each author as a single entity (don't split by comma within author name)
    input_list = [normalize_text(author) for author in input_parts if author]
    db_list = [normalize_text(author) for author in db_parts if author]
    
    if not input_list or not db_list:
        return False
    
    # Both lists should have the same length if neither has et al
    if not input_has_et_al and not db_has_et_al:
        if len(input_list) != len(db_list):
            return False
    
    # If input has et al, database must have at least as many authors as input list
    if input_has_et_al and len(db_list) < len(input_list):
        return False
    
    # If database has et al, input must have at least as many authors as database list
    if db_has_et_al and len(input_list) < len(db_list):
        return False
    
    # Compare authors in order by normalized names
    min_len = min(len(input_list), len(db_list))
    for i in range(min_len):
        if input_list[i] != db_list[i]:
            return False
    
    return True


def author_similarity(a: str, b: str) -> float:
    """Deprecated: Use authors_match_strictly() for publication-grade checking."""
    a_parts = author_tokens(a)
    b_parts = author_tokens(b)
    if not a_parts or not b_parts:
        return 0.0
    overlap = len(set(a_parts) & set(b_parts))
    denom = max(len(set(a_parts)), len(set(b_parts)), 1)
    return overlap / denom


def author_tokens(text: str) -> List[str]:
    parts = re.split(r"\s+and\s+|,", text)
    tokens: List[str] = []
    for part in parts:
        normalized = normalize_text(part)
        if normalized:
            tokens.append(normalized)
    return tokens


def generate_citation_key(entry: Dict[str, Any]) -> str:
    author = str(entry.get("author", "") or "")
    title = str(entry.get("title", "") or "")
    year = str(entry.get("year", "") or "")

    first_author = "unknown"
    if author:
        first = re.split(r"\s+and\s+|,", author)[0].strip()
        if first:
            tokens = [t for t in re.split(r"\s+", normalize_text(first)) if t]
            if tokens:
                first_author = tokens[-1]

    title_words = [w for w in re.split(r"\s+", normalize_text(title)) if w]
    title_stub = "".join(title_words[:3]) if title_words else "untitled"
    title_stub = re.sub(r"[^a-z0-9]+", "", title_stub)

    year_stub = year[-2:] if len(year) >= 2 else year
    key = f"{first_author}{year_stub}{title_stub}".strip()
    key = re.sub(r"[^a-z0-9]+", "", key.lower())
    return key or "entry"


def load_bibtex(path: Path) -> bibtexparser.bibdatabase.BibDatabase:
    with path.open("r", encoding="utf-8") as fh:
        return bibtexparser.load(fh)


def dump_bibtex(path: Path, db: bibtexparser.bibdatabase.BibDatabase) -> None:
    writer = BibTexWriter()
    writer.indent = "    "
    writer.order_entries_by = ("ID",)
    writer.align_values = False
    writer.display_order = [
        "author",
        "title",
        "journal",
        "booktitle",
        "year",
        "volume",
        "number",
        "pages",
        "publisher",
        "address",
        "doi",
        "url",
        "note",
    ]
    with path.open("w", encoding="utf-8") as fh:
        fh.write(writer.write(db))


def process_file(input_path: Path, output_path: Path, force: bool = False, rewrite_keys: bool = False) -> List[ResolutionResult]:
    db = load_bibtex(input_path)
    resolver = BibliographicResolver()
    results: List[ResolutionResult] = []
    used_keys = {entry.get("ID", "") for entry in db.entries if entry.get("ID")}

    for entry in db.entries:
        result = resolver.resolve_entry(entry, force=force, rewrite_keys=rewrite_keys)
        if rewrite_keys:
            desired = result.resolved_key or result.key
            unique_key = desired
            counter = 2
            while unique_key in used_keys:
                unique_key = f"{desired}{counter}"
                counter += 1
            result.resolved_key = unique_key
            used_keys.add(unique_key)
        results.append(result)
        if result.changed:
            entry.clear()
            entry.update(result.resolved)
            entry["ID"] = result.resolved_key or result.key

    dump_bibtex(output_path, db)
    return results


def build_report(results: List[ResolutionResult]) -> Dict[str, Any]:
    low_confidence_threshold = 0.80
    report: Dict[str, Any] = {
        "metadata": {
            "version": "1.0",
            "generated": __import__("datetime").datetime.utcnow().isoformat(),
            "low_confidence_threshold": low_confidence_threshold,
        },
        "entries": [],
        "summary": {
            "total": len(results),
            "changed": sum(1 for r in results if r.changed),
            "unchanged": sum(1 for r in results if not r.changed),
            "low_confidence": sum(1 for r in results if r.confidence < low_confidence_threshold),
            "high_confidence": sum(1 for r in results if r.confidence >= low_confidence_threshold and r.changed),
        },
    }
    
    # Field names to compare in before/after
    compare_fields = [
        "title", "author", "year", "booktitle", "journal", "volume", 
        "number", "pages", "doi", "url", "publisher", "address"
    ]
    
    for result in results:
        # Build a comprehensive change log
        changes = []
        for field in compare_fields:
            before = result.original.get(field, "")
            after = result.resolved.get(field, "")
            if normalize_text(before) != normalize_text(after):
                changes.append({
                    "field": field,
                    "before": before,
                    "after": after,
                    "changed": before != after,
                })
        
        entry_report = {
            "id": result.key,
            "resolved_id": result.resolved_key,
            "changed": result.changed,
            "chosen_source": result.chosen_source,
            "confidence": round(result.confidence, 4),
            "is_low_confidence": result.confidence < low_confidence_threshold,
            "reason": result.reason,
            "changes": changes,
            "entry_type_before": result.original.get("ENTRYTYPE", ""),
            "entry_type_after": result.resolved.get("ENTRYTYPE", ""),
        }
        report["entries"].append(entry_report)
    
    # Sort by confidence to highlight low-confidence entries
    report["entries"].sort(key=lambda x: (x["is_low_confidence"], -x["confidence"]))
    
    return report


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate more accurate BibTeX using free bibliographic sources.")
    parser.add_argument("input", type=Path, help="Input .bib file")
    parser.add_argument("-o", "--output", type=Path, help="Output .bib file (default: overwrite input)")
    parser.add_argument("--report", type=Path, help="Write a JSON report with per-entry decisions")
    parser.add_argument("--force", action="store_true", help="Replace fields using the best candidate even when merging is conservative")
    parser.add_argument("--rewrite-keys", action="store_true", help="Rewrite cite keys to canonical author-year-title keys")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")

    input_path = args.input.resolve()
    output_path = (args.output or args.input).resolve()

    if not input_path.exists():
        LOGGER.error("Input file does not exist: %s", input_path)
        return 1

    try:
        results = process_file(input_path, output_path, force=args.force, rewrite_keys=args.rewrite_keys)
    except Exception as exc:
        LOGGER.exception("Failed to process BibTeX file: %s", exc)
        return 2

    if args.report:
        report = build_report(results)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    changed = sum(1 for r in results if r.changed)
    LOGGER.info("Processed %d entries; updated %d entries.", len(results), changed)
    LOGGER.info("Wrote %s", output_path)
    if args.report:
        LOGGER.info("Wrote report %s", args.report.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
