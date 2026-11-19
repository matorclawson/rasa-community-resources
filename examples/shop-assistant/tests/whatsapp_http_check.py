"""Real local HTTP acknowledgement checks; synthetic keys and no provider calls."""
from http.client import HTTPConnection
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.parse import urlencode
from pydantic import SecretStr
from zeo_core.integrations.twilio_whatsapp import compute_signature
from shop_demo.whatsapp_webhook import Intake, Journal, server


class HttpChecks(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.journal = Journal(Path(self.tmp.name) / "private" / "inbox.sqlite3")
        self.base = "https://offline-example.app.github.dev"
        self.token = SecretStr("offline-token")
        self.params = {"AccountSid": "AC" + "1" * 32, "MessageSid": "SM" + "2" * 32,
                       "From": "whatsapp:+15555550101", "To": "whatsapp:+15555550102",
                       "Body": "synthetic", "NumMedia": "0"}
        intake = Intake(self.journal, public_base=self.base, account_sid=self.params["AccountSid"],
                        token=self.token, customer="+15555550101", sender="+15555550102")
        self.server = server(intake, port=0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()
        self.journal.close()
        self.tmp.cleanup()

    def post(self, signature):
        conn = HTTPConnection("127.0.0.1", self.server.server_port, timeout=5)
        conn.request("POST", "/twilio/inbound", urlencode(self.params),
                     {"Content-Type": "application/x-www-form-urlencoded", "X-Twilio-Signature": signature})
        response = conn.getresponse()
        result = response.status, response.read()
        conn.close()
        return result

    def test_signed_request_is_committed_before_empty_non_twiml_ack(self):
        signed = compute_signature(self.token, self.base + "/twilio/inbound", self.params)
        self.assertEqual(self.post(signed), (200, b""))
        self.assertEqual(self.journal.db.execute("SELECT COUNT(*) FROM wa_inbox").fetchone()[0], 1)

    def test_unsigned_request_is_rejected_without_persistence(self):
        self.assertEqual(self.post(""), (403, b""))
        self.assertEqual(self.journal.db.execute("SELECT COUNT(*) FROM wa_inbox").fetchone()[0], 0)


if __name__ == "__main__":
    unittest.main()
