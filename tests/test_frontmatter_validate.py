#!/usr/bin/env python3
"""
Tests for kb_frontmatter_validate.py

Run: python3 -m pytest tests/test_frontmatter_validate.py -v
  or: python3 tests/test_frontmatter_validate.py
"""

import sys
import os
import unittest
from pathlib import Path

# Add scripts dir to path
PLUGIN_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PLUGIN_ROOT / "skills" / "obsidian-nav" / "scripts"
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "frontmatter"
# Fake archive dir for tolerance tests
ARCHIVE_FIXTURE = FIXTURES_DIR / "_archives"

sys.path.insert(0, str(SCRIPTS_DIR))

from kb_frontmatter_validate import (
    parse_frontmatter,
    validate_frontmatter,
    is_archive_or_template,
    VALID_TYPES,
    VALID_STATUSES,
    DATE_PATTERN,
)


class TestParseFormatter(unittest.TestCase):
    """Tests for frontmatter parser"""

    def test_valid_frontmatter(self):
        fp = str(FIXTURES_DIR / "valid-fondation.md")
        fm, err = parse_frontmatter(fp)
        self.assertIsNone(err)
        self.assertIsNotNone(fm)
        self.assertEqual(fm["type"], "fondation")
        self.assertEqual(fm["status"], "actif")

    def test_missing_frontmatter(self):
        # Fichier sans frontmatter
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Just a title\nNo frontmatter here.\n")
            tmpfile = f.name
        try:
            fm, err = parse_frontmatter(tmpfile)
            self.assertIsNone(err)
            self.assertEqual(fm, {})
        finally:
            os.unlink(tmpfile)

    def test_invalid_yaml(self):
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("---\ntitle: [unclosed\ntype: note\n---\n")
            tmpfile = f.name
        try:
            fm, err = parse_frontmatter(tmpfile)
            self.assertIsNotNone(err)
        finally:
            os.unlink(tmpfile)


class TestValidTypes(unittest.TestCase):
    """Tests for type validation"""

    def test_known_types_in_registry(self):
        expected = {
            "fondation", "strategie", "marque", "spec", "ops",
            "decision", "chantier", "contenu", "persona", "rapport",
            "prompt", "template", "journal", "index", "note",
            "technique", "mission", "person", "interview", "recherche",
            "copy", "veille", "buffer", "inbox", "document-simule",
            "demo-script", "simulation"
        }
        self.assertEqual(VALID_TYPES, expected)

    def test_valid_statuses(self):
        expected = {
            "backlog", "draft", "exploration", "actif",
            "en-pause", "terminé", "publié", "abandonné", "archivé", "superseded"
        }
        self.assertEqual(VALID_STATUSES, expected)


class TestDatePattern(unittest.TestCase):
    """Tests for date format validation"""

    def test_valid_date(self):
        self.assertTrue(DATE_PATTERN.match("2026-05-18"))
        self.assertTrue(DATE_PATTERN.match("2024-01-01"))

    def test_invalid_dates(self):
        self.assertIsNone(DATE_PATTERN.match("18/05/2026"))
        self.assertIsNone(DATE_PATTERN.match("18-05-2026"))
        self.assertIsNone(DATE_PATTERN.match("2026/05/18"))
        self.assertIsNone(DATE_PATTERN.match("not-a-date"))


class TestArchiveTolerance(unittest.TestCase):
    """Tests for archive/template tolerance"""

    def test_non_archive(self):
        self.assertFalse(is_archive_or_template("/kb/00-fondations/file.md"))

    def test_archive_path(self):
        self.assertTrue(is_archive_or_template("/kb/_archives/old/file.md"))

    def test_template_path(self):
        self.assertTrue(is_archive_or_template("/kb/_templates/tmpl.md"))


class TestValidFixtures(unittest.TestCase):
    """Valid fixtures should return 0 critical violations"""

    def _assert_no_critical(self, filename):
        fp = str(FIXTURES_DIR / filename)
        violations = validate_frontmatter(fp, schemas_dir=None)
        criticals = [v for v in violations if v.level == "critical"]
        self.assertEqual(criticals, [],
            f"{filename}: unexpected critical violations: {[str(v) for v in criticals]}")

    def test_valid_fondation(self):
        self._assert_no_critical("valid-fondation.md")

    def test_valid_chantier(self):
        self._assert_no_critical("valid-chantier.md")

    def test_valid_decision(self):
        self._assert_no_critical("valid-decision.md")

    def test_valid_contenu(self):
        self._assert_no_critical("valid-contenu.md")

    def test_valid_person(self):
        self._assert_no_critical("valid-person.md")


class TestInvalidFixtures(unittest.TestCase):
    """Invalid fixtures should return at least 1 critical violation"""

    def _assert_has_critical(self, filename):
        fp = str(FIXTURES_DIR / filename)
        violations = validate_frontmatter(fp, schemas_dir=None)
        criticals = [v for v in violations if v.level == "critical"]
        self.assertGreater(len(criticals), 0,
            f"{filename}: should have critical violations but got none")

    def test_missing_required(self):
        self._assert_has_critical("invalid-missing-required.md")

    def test_unknown_type(self):
        self._assert_has_critical("invalid-unknown-type.md")

    def test_bad_date(self):
        self._assert_has_critical("invalid-bad-date.md")

    def test_bad_status(self):
        self._assert_has_critical("invalid-bad-status.md")

    def test_decision_superseded_no_replaced_by(self):
        self._assert_has_critical("invalid-decision-superseded-no-replaced-by.md")

    def test_archive_warning_not_critical(self):
        """Files in _archives/ get warnings not critical violations"""
        import tempfile
        import shutil
        # Create temp archive dir with incomplete frontmatter
        tmpdir = Path(tempfile.mkdtemp()) / "_archives"
        tmpdir.mkdir()
        tmpfile = tmpdir / "old.md"
        tmpfile.write_text("---\ntitle: Old\ntype: note\n---\n")
        try:
            violations = validate_frontmatter(str(tmpfile), schemas_dir=None)
            criticals = [v for v in violations if v.level == "critical"]
            warnings = [v for v in violations if v.level == "warning"]
            self.assertEqual(criticals, [],
                "Archive files should not produce critical violations")
            self.assertGreater(len(warnings), 0,
                "Archive files with incomplete frontmatter should produce warnings")
        finally:
            shutil.rmtree(str(tmpdir.parent))


if __name__ == "__main__":
    unittest.main(verbosity=2)
