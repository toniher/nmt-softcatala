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

    def test_translate_get(self):

        text = urllib.parse.quote_plus(self.SOURCE.encode('utf-8'))
        url = f"{self.URL}{self.TRANSLATE}?langpair=en|cat&markUnknown=no&q={text}"

        response = requests.get(url)
        status = response.json()['responseStatus']
        translation = response.json()['responseData']['translatedText']
       
        self.assertEqual(self.OK, status)
        self.assertEqual("Com ", translation[:4])
