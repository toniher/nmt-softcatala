import email
import importlib.util
import os
import subprocess
import tempfile
import unittest
from unittest import mock

# process-batch.py is a script (hyphenated name), so load it by path.
_spec = importlib.util.spec_from_file_location("process_batch", os.path.join(os.path.dirname(__file__), "..", "process-batch.py"))
process_batch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(process_batch)


class FakeSMTP:
    sent = []

    def __init__(self, *args):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def sendmail(self, sender, to, body):
        FakeSMTP.sent.append((to, body))


def _text(body):
    '''Decoded text of every plain-text part of a sent message.'''
    parts = email.message_from_string(body).walk()
    return "".join(p.get_payload(decode=True).decode() for p in parts if p.get_content_type() == "text/plain")


class TestProcessJob(unittest.TestCase):

    def setUp(self):
        FakeSMTP.sent = []
        self.temp_dir = tempfile.TemporaryDirectory()
        self.source = os.path.join(self.temp_dir.name, "upload")
        self.record = os.path.join(self.temp_dir.name, "record")
        for path, text in ((self.source, "Hello\n"), (self.record, "")):
            with open(path, "w") as f:
                f.write(text)
        self.job = mock.Mock(filename=self.source, filename_dbrecord=self.record,
                             email="user@example.org", model_name="eng-cat")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _fake_translate(self, cmd, check):
        with open(cmd[cmd.index('-t') + 1], "w") as f:
            f.write("Hola\n")

    def test_success_emails_translation_and_cleans_up(self):
        with mock.patch.object(process_batch.smtplib, "SMTP", FakeSMTP), \
             mock.patch.object(process_batch.subprocess, "run", self._fake_translate):
            process_batch.process_job(self.job)

        self.assertEqual(1, len(FakeSMTP.sent))
        self.assertEqual("user@example.org", FakeSMTP.sent[0][0])
        self.assertEqual("Hola\n", _text(FakeSMTP.sent[0][1]))
        self.assertEqual([], os.listdir(self.temp_dir.name))

    def test_failure_sends_notice_and_cleans_up(self):
        error = subprocess.CalledProcessError(1, "model_to_txt")
        with mock.patch.object(process_batch.smtplib, "SMTP", FakeSMTP), \
             mock.patch.object(process_batch.subprocess, "run", side_effect=error):
            process_batch.process_job(self.job)

        self.assertEqual(1, len(FakeSMTP.sent))
        self.assertEqual("user@example.org", FakeSMTP.sent[0][0])
        self.assertIn("No hem pogut traduir", _text(FakeSMTP.sent[0][1]))
        self.assertEqual([], os.listdir(self.temp_dir.name))

    def test_smtp_down_does_not_raise(self):
        with mock.patch.object(process_batch.smtplib, "SMTP", side_effect=OSError("unreachable")), \
             mock.patch.object(process_batch.subprocess, "run", self._fake_translate):
            process_batch.process_job(self.job)

        self.assertEqual([], os.listdir(self.temp_dir.name))


if __name__ == '__main__':
    unittest.main()
