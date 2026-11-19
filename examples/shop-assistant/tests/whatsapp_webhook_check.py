"""Offline receiver checks against the actual Core WhatsApp signature/parser.

Run explicitly in the isolated whatsapp-proof environment. No provider call.
"""
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import urlencode

from pydantic import SecretStr
from zeo_core.integrations.twilio_whatsapp import compute_signature

from shop_demo.whatsapp_webhook import Intake, Journal


class WebhookTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = Path(self.directory.name) / "private" / "inbox.sqlite3"
        self.journal = Journal(self.path)
        self.token = SecretStr("offline-signature-fixture")
        self.base = "https://offline-example.app.github.dev"
        self.account = "AC" + "1" * 32
        self.customer, self.sender = "+15555550101", "+14155238886"
        self.intake = Intake(self.journal, public_base=self.base, account_sid=self.account,
                             token=self.token, customer=self.customer, sender=self.sender)
        self.params = {"AccountSid": self.account, "MessageSid": "SM" + "2" * 32,
                       "From": "whatsapp:" + self.customer, "To": "whatsapp:" + self.sender,
                       "Body": "confirm", "NumMedia": "0",
                       "OriginalRepliedMessageSid": "SM" + "3" * 32}

    def tearDown(self):
        self.journal.close()
        self.directory.cleanup()

    def post(self, params=None, *, path="/twilio/inbound", signed_path=None, signature=None):
        params = self.params if params is None else params
        if signature is None:
            signature = compute_signature(self.token, self.base + (signed_path or path), params)
        return self.intake.accept(path, "application/x-www-form-urlencoded",
                                  urlencode(params).encode(), signature)

    def test_success_is_durable_before_ack_and_preserves_reply_binding(self):
        self.assertEqual(self.post(), 200)
        other = Journal(self.path)
        try:
            row = other.db.execute("SELECT event,phase FROM wa_inbox").fetchone()
            self.assertEqual(row[1], "saved")
            self.assertEqual(json.loads(row[0])["reply_to_message_id"], self.params["OriginalRepliedMessageSid"])
        finally:
            other.close()

    def test_repeated_event_is_retained_once(self):
        self.assertEqual(self.post(), 200)
        self.assertEqual(self.post(), 200)
        self.assertEqual(self.journal.db.execute("SELECT COUNT(*) FROM wa_inbox").fetchone()[0], 1)

    def test_changed_duplicate_holds_original_without_overwrite(self):
        self.assertEqual(self.post(), 200)
        self.assertEqual(self.post({**self.params, "Body": "different"}), 409)
        original, phase = self.journal.db.execute("SELECT original,phase FROM wa_inbox").fetchone()
        self.assertEqual(json.loads(original)["Body"], "confirm")
        self.assertEqual(phase, "held")

    def test_signature_from_another_path_cannot_admit_event(self):
        self.assertEqual(self.post(signed_path="/different"), 403)
        self.assertIsNone(self.journal.db.execute("SELECT 1 FROM wa_inbox").fetchone())

    def test_missing_signature_cannot_admit_event(self):
        self.assertEqual(self.post(signature=""), 403)

    def test_wrong_customer_or_account_is_refused_even_when_signed(self):
        for patch in ({"From": "whatsapp:+15555550102"}, {"To": "whatsapp:+15555550103"},
                      {"AccountSid": "AC" + "4" * 32}):
            with self.subTest(patch=patch):
                self.assertEqual(self.post({**self.params, **patch}), 403)
        self.assertIsNone(self.journal.db.execute("SELECT 1 FROM wa_inbox").fetchone())

    def test_opaque_sids_have_no_inferred_timestamp_or_sort_order(self):
        self.assertEqual(self.post(), 200)
        self.assertEqual(self.post({**self.params, "MessageSid": "SM" + "0" * 32}), 200)
        ids = [r[0] for r in self.journal.db.execute("SELECT event_id FROM wa_inbox ORDER BY sequence")]
        self.assertEqual(ids, [self.params["MessageSid"], "SM" + "0" * 32])

    def test_callbacks_are_retained_without_marking_delivery_or_placing(self):
        params = {"AccountSid": self.account, "MessageSid": "SM" + "5" * 32,
                  "To": "whatsapp:" + self.customer, "MessageStatus": "queued"}
        self.assertEqual(self.post(params, path="/twilio/status"), 200)
        self.assertEqual(self.post(params, path="/twilio/status"), 200)
        self.assertEqual(self.post({**params, "MessageStatus": "delivered"}, path="/twilio/status"), 200)
        self.assertEqual(self.journal.db.execute("SELECT COUNT(*) FROM wa_callbacks").fetchone()[0], 2)
        self.assertIsNone(self.journal.db.execute("SELECT 1 FROM wa_inbox").fetchone())

    def test_ambiguous_or_unbounded_requests_are_refused(self):
        body = urlencode(self.params).encode() + b"&Body=second"
        self.assertEqual(self.intake.accept("/twilio/inbound", "application/x-www-form-urlencoded", body, "x"), 400)
        self.assertEqual(self.intake.accept("/twilio/inbound?other=1", "application/x-www-form-urlencoded", b"a=b", "x"), 404)
        self.assertEqual(self.intake.accept("/twilio/inbound", "application/json", b"{}", "x"), 415)
        self.assertEqual(self.intake.accept("/twilio/inbound", "application/x-www-form-urlencoded", b"x" * 65537, "x"), 413)

    def test_storage_failure_never_acknowledges(self):
        self.journal.close()
        self.assertEqual(self.post(), 503)
        # tearDown can close the closed connection again.


if __name__ == "__main__":
    unittest.main()
