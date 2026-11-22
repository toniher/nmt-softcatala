import unittest
from languages import langpair_to_iso639_3, language_name


class TestLanguages(unittest.TestCase):

    def test_langpair_two_letter(self):
        self.assertEqual("eng-cat", langpair_to_iso639_3("en|ca"))
        self.assertEqual("cat-eus", langpair_to_iso639_3("ca|eu"))
        self.assertEqual("spa-cat", langpair_to_iso639_3("es|ca"))

    def test_langpair_three_letter_and_mixed(self):
        self.assertEqual("eng-cat", langpair_to_iso639_3("eng|cat"))
        self.assertEqual("eng-cat", langpair_to_iso639_3("en|cat"))

    def test_langpair_unknown_and_internal_key_pass_through(self):
        self.assertEqual("xx-yy", langpair_to_iso639_3("xx|yy"))
        self.assertEqual("eng-cat", langpair_to_iso639_3("eng-cat"))

    def test_language_name(self):
        self.assertEqual("Basque", language_name("eus"))
        self.assertEqual("basc", language_name("eus", "ca"))
        self.assertIsNone(language_name("xxx", "ca"))


if __name__ == '__main__':
    unittest.main()
