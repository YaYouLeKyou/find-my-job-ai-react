"""Tests unitaires pour shared/utils.py"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import unittest
from io import BytesIO
from utils import clean_job_title, generate_job_search_links


class TestCleanJobTitle(unittest.TestCase):
    """Tests pour clean_job_title."""

    def test_empty_string(self):
        self.assertEqual(clean_job_title(""), "")

    def test_none_value(self):
        self.assertEqual(clean_job_title(None), "")

    def test_basic_title(self):
        result = clean_job_title("Développeur Python")
        self.assertEqual(result, "Développeur python")

    def test_hf_removal(self):
        result = clean_job_title("Développeur H/F")
        self.assertEqual(result, "Développeur")

    def test_fh_removal(self):
        result = clean_job_title("Ingénieur F/H")
        self.assertEqual(result, "Ingénieur")

    def test_parenthesis_removal(self):
        result = clean_job_title("Développeur (Python, Django)")
        self.assertEqual(result, "Développeur")

    def test_list_input(self):
        result = clean_job_title(["Développeur", "Python"])
        self.assertEqual(result, "Développeur python")

    def test_metier_prefix(self):
        result = clean_job_title("Métier: Développeur Python")
        self.assertEqual(result, "Développeur python")


class TestGenerateJobSearchLinks(unittest.TestCase):
    """Tests pour generate_job_search_links."""

    def test_french_links(self):
        links = generate_job_search_links("Python Developer", "fr")
        self.assertIn("Welcome to the Jungle", links)
        self.assertIn("HelloWork", links)
        self.assertIn("Service Public", links)
        self.assertIn("Remote OK", links)  # Global

    def test_english_links(self):
        links = generate_job_search_links("Python Developer", "en")
        self.assertIn("LinkedIn US", links)
        self.assertIn("Reed.co.uk", links)
        self.assertIn("Dice (Tech US)", links)

    def test_global_links_always_present(self):
        links = generate_job_search_links("Test", "fr")
        self.assertIn("Remote OK", links)
        self.assertIn("Indeed Global", links)

    def test_url_encoding(self):
        links = generate_job_search_links("Data Scientist", "en")
        self.assertIn("Data%20Scientist", links["LinkedIn US"])
        self.assertNotIn(" ", links["LinkedIn US"])


if __name__ == '__main__':
    unittest.main()