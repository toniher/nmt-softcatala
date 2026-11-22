from unittest import TestCase
import requests
import urllib.request, urllib.parse, urllib.error

class TestApertium(TestCase):

    OK = 200
    #URL = "https://www.softcatala.org/api/traductor"
    URL = "http://127.0.0.1:8700"

    TRANSLATE = "/translate"
    LISTPAIRS = "/listPairs"
    LANGUAGE_NAMES =  "/listLanguageNames"
    SOURCE = "How are you?"
    TRANSLATION = "Com estàs?"

    def test_listlanguagesname_languages(self):
        response = requests.get(self.URL + self.LANGUAGE_NAMES + "?locale=ca&languages=cat+eng")
        languages = response.json()

        self.assertEqual(self.OK, response.status_code)
        self.assertIn('eng', languages)
        self.assertIn('cat', languages)

    def test_listlanguagesname_languages_xxx(self):
        response = requests.get(self.URL + self.LANGUAGE_NAMES + "?locale=ca&languages=cat+xxx")
        languages = response.json()

        self.assertEqual(self.OK, response.status_code)
        self.assertNotIn('xxx', languages)
        self.assertIn('cat', languages)

    def test_listpairs(self):
        response = requests.get(self.URL + self.LISTPAIRS)
        status = response.json()['responseStatus']
        pairList = response.json()['responseData']
        languages = set()

        for pair in pairList:
            source = pair['sourceLanguage']
            target = pair['targetLanguage']
            languagePair = f"{source}-{target}"
            languages.add(languagePair)

        self.assertEqual(self.OK, status)
        self.assertIn('eng-cat', languages)
        self.assertIn('cat-eng', languages)
    
    def test_translate_post(self):

        payload = {"langpair" : "en|cat", "q" : self.SOURCE, "key": "NmQ3NmMyNThmM2JjNWQxMjkxN2N"}
        response = requests.post(self.URL + self.TRANSLATE, data = payload)
        status = response.json()['responseStatus']
        translation = response.json()['responseData']['translatedText']
       
        self.assertEqual(self.OK, status)
        self.assertEqual("Com ", translation[:4])

    def test_translate_post_additional_slash(self):

        payload = {"langpair" : "en|cat", "q" : self.SOURCE, "key": "NmQ3NmMyNThmM2JjNWQxMjkxN2N"}
        response = requests.post(self.URL + self.TRANSLATE + "/", data = payload)
        status = response.json()['responseStatus']
        translation = response.json()['responseData']['translatedText']

        self.assertEqual(self.OK, status)
        self.assertEqual("Com ", translation[:4])

    def test_translate_get_catalan_source(self):
        # Catalan source goes through different SRX segmentation rules than English
        response = requests.get(f"{self.URL}{self.TRANSLATE}?langpair=ca|en&q=Bon+dia...+Com+est%C3%A0s%3F")

        self.assertEqual(self.OK, response.status_code)
        self.assertEqual("Good morning", response.json()['responseData']['translatedText'][:12])

    def test_translate_get_basque_two_letter_codes(self):
        response = requests.get(self.URL + self.TRANSLATE, params={"langpair": "eu|ca", "q": "Kaixo, zer moduz?"})

        self.assertEqual(self.OK, response.status_code)
        self.assertEqual("Hola", response.json()['responseData']['translatedText'][:4])
        self.assertNotIn('message', response.json())

    def test_translate_get_basque_gender_bias_message(self):
        q = "Bingen Zupiria Segurtasun sailburuak Euskadi Irratian iragarri du."
        response = requests.get(self.URL + self.TRANSLATE, params={"langpair": "eu|ca", "q": q})

        self.assertEqual(self.OK, response.status_code)
        self.assertIn("en basc", response.json()['message'])
        self.assertIn("«sailburuak»", response.json()['message'])

    def test_translate_keeps_code_and_identifiers(self):
        # Issue #39: characters missing from the model's vocabulary (` _ @ ...) used to be mangled.
        spans = ["``ubports/24.6.x``", "``morph-browser``", "``24.6.x_-_PR_morph-browser_125``", "user@example.com"]
        q = (f"An MR numbered 125 made against the {spans[0]} branch of Git repository {spans[1]} "
             f"will have an APT archive named {spans[2]}. Ask {spans[3]} for help.")
        response = requests.get(self.URL + self.TRANSLATE, params={"langpair": "en|ca", "q": q})
        translated = response.json()["responseData"]["translatedText"]
        for span in spans:
            self.assertIn(span, translated)

    def test_translate_post_text_too_long(self):
        response = requests.post(self.URL + self.TRANSLATE + "/", data={"langpair": "en|ca", "q": "a" * 20001})

        self.assertEqual(400, response.status_code)
        self.assertIn("massa llarg", response.json()['explanation'])

    def test_translate_file_too_large(self):
        files = {"file": ("big.txt", b"a" * (9 * 1024 * 1024))}
        response = requests.post(self.URL + "/translate_file/", files=files,
                                 data={"email": "test@example.org", "model_name": "eng-cat"})

        self.assertEqual(413, response.status_code)
        self.assertIn("massa gran", response.json()['explanation'])

    def test_stats_bad_date(self):
        for query in ("", "?date=22-11-2026"):
            response = requests.get(self.URL + "/stats/" + query)

            self.assertEqual(400, response.status_code)
            self.assertIn("AAAA-MM-DD", response.json()['explanation'])

    def test_translate_file_missing_file(self):
        response = requests.post(self.URL + "/translate_file/", data={"email": "test@example.org", "model_name": "eng-cat"})

        self.assertEqual(400, response.status_code)
        self.assertEqual("No s'ha especificat el fitxer", response.json()['explanation'])

    def test_translate_get(self):

        text = urllib.parse.quote_plus(self.SOURCE.encode('utf-8'))
        url = f"{self.URL}{self.TRANSLATE}?langpair=en|cat&markUnknown=no&q={text}"

        response = requests.get(url)
        status = response.json()['responseStatus']
        translation = response.json()['responseData']['translatedText']
       
        self.assertEqual(self.OK, status)
        self.assertEqual("Com ", translation[:4])
