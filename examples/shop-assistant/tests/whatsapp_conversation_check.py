"""Offline business-boundary tests; actual Core records, no provider or model."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from uuid import uuid4

from zeo_core.integrations.twilio_whatsapp import ChannelInbound, ChannelReceipt

from shop_demo.models import Order, PricedItem, Product, Quote
from shop_demo.whatsapp_conversation import Conversation
from shop_demo.whatsapp_webhook import IntakeHeld


class FakeChannel:
    def __init__(self):
        self.requests = []
        self.fail = False

    def send(self, request):
        self.requests.append(request)
        if self.fail:
            raise TimeoutError("offline uncertain effect")
        return ChannelReceipt(provider_message_id="SM" + f"{len(self.requests):032x}",
                              status="queued", to=request.to)


class Boundaries(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.now = datetime(2026, 11, 19, 6, tzinfo=timezone.utc)
        self.quote = Quote(reference=uuid4(), currency="MXN", expires_at=self.now + timedelta(minutes=5),
                           items=(PricedItem(product=Product(code="NOTEBOOK", name="Notebook", price_cents=12900, stock=12), quantity=2),))
        self.order = None
        self.placements = []
        async def respond(event, latest):
            return self.quote
        async def place(reference, key):
            self.placements.append((reference, key))
            self.order = Order(number=uuid4(), quote=self.quote, status="placed", created_at=self.now, request_key=key)
            return self.order
        async def lookup(number):
            return self.order
        self.channel = FakeChannel()
        self.conversation = Conversation(Path(self.directory.name) / "private" / "inbox.sqlite3",
            customer="+15555550101", sender="+14155238886", public_base="https://offline.app.github.dev",
            channel=self.channel, assistant=SimpleNamespace(respond=respond),
            orders=SimpleNamespace(place=place, lookup=lookup), clock=lambda: self.now,
            minimum_send_interval=0)
        self.counter = 10

    async def asyncTearDown(self):
        self.conversation.close()
        self.directory.cleanup()

    def retain(self, text, reply=None):
        self.counter += 1
        event = ChannelInbound(event_id="SM" + f"{self.counter:032x}", sender_id="+15555550101",
                               recipient_id="+14155238886", conversation_id="+15555550101",
                               text=text, reply_to_message_id=reply)
        self.conversation.journal.retain(event, {"MessageSid": event.event_id, "Body": text})
        return event

    async def review(self):
        self.retain("two notebooks")
        await self.conversation.handle_next()
        return "SM" + f"{len(self.channel.requests):032x}"

    async def test_review_has_exact_amount_and_no_order(self):
        await self.review()
        self.assertIn("MXN 258.00", self.channel.requests[-1].body)
        self.assertIn("WhatsApp Reply on THIS review", self.channel.requests[-1].body)
        self.assertEqual(self.placements, [])

    async def test_only_exact_review_bound_confirmation_places_once(self):
        review = await self.review()
        event = self.retain("confirm", review)
        await self.conversation.handle_next()
        self.assertEqual(self.placements, [(self.quote.reference, "whatsapp:" + event.event_id)])
        self.conversation.journal.retain(event, {"MessageSid": event.event_id, "Body": "confirm"})
        self.assertFalse(await self.conversation.handle_next())
        self.assertEqual(len(self.placements), 1)

    async def test_plain_confirmation_cannot_place(self):
        await self.review()
        self.retain("confirm")
        await self.conversation.handle_next()
        self.assertEqual(self.placements, [])

    async def test_wrong_review_or_expired_quote_cannot_place(self):
        review = await self.review()
        self.now += timedelta(minutes=6)
        self.retain("confirm", review)
        await self.conversation.handle_next()
        self.assertEqual(self.placements, [])
        self.now -= timedelta(minutes=6)
        await self.review()
        self.retain("confirm", "SM" + "f" * 32)
        await self.conversation.handle_next()
        self.assertEqual(self.placements, [])

    async def test_any_intervening_message_cancels_old_review(self):
        review = await self.review()
        self.retain("cancel")
        await self.conversation.handle_next()
        self.retain("confirm", review)
        await self.conversation.handle_next()
        self.assertEqual(self.placements, [])

    async def test_unknown_send_is_retained_and_never_retried(self):
        self.channel.fail = True
        self.retain("two notebooks")
        with self.assertRaises(IntakeHeld):
            await self.conversation.handle_next()
        self.assertIsNone(self.conversation.db.execute("SELECT receipt FROM wa_outgoing").fetchone()[0])
        with self.assertRaises(IntakeHeld):
            await self.conversation.handle_next()
        self.assertEqual(len(self.channel.requests), 1)

    async def test_oversized_reply_refuses_before_provider(self):
        with self.assertRaises(IntakeHeld):
            await self.conversation.send("large", "x" * 1601)
        self.assertEqual(self.channel.requests, [])

    async def test_changed_duplicate_during_model_turn_stays_held(self):
        event = self.retain("two notebooks")
        async def respond(message, latest):
            # A concurrent signed HTTP retry changes the original while the
            # asynchronous model turn is open. Its 409 must survive completion.
            with self.assertRaises(IntakeHeld):
                self.conversation.journal.retain(event, {"MessageSid": event.event_id, "Body": "changed"})
            return self.quote
        self.conversation.assistant = SimpleNamespace(respond=respond)
        with self.assertRaises(IntakeHeld):
            await self.conversation.handle_next()
        self.assertEqual(self.channel.requests, [])
        self.assertEqual(self.placements, [])
        self.assertEqual(self.conversation.db.execute("SELECT phase FROM wa_inbox").fetchone()[0], "held")

    async def test_shipping_is_one_same_recipient_attempt_not_delivery_claim(self):
        review = await self.review()
        self.retain("confirm", review)
        await self.conversation.handle_next()
        self.order = self.order.model_copy(update={"status": "shipped"})
        await self.conversation.notify_shipments()
        await self.conversation.notify_shipments()
        shipments = [r for r in self.channel.requests if "has shipped" in r.body]
        self.assertEqual(len(shipments), 1)
        self.assertEqual(shipments[0].to, "+15555550101")
        self.assertEqual(self.conversation.delivery_observations(), [])

    async def test_delivery_callback_must_bind_owned_sid_and_recipient(self):
        sid = await self.review()
        def callback(sid, to, status):
            r = ChannelReceipt(provider_message_id=sid, to=to, status=status)
            self.conversation.journal.callback(r, {"sid": sid, "to": to, "status": status})
        callback("SM" + "f" * 32, "+15555550101", "delivered")
        callback(sid, "+15555550102", "delivered")
        self.assertEqual(self.conversation.delivery_observations(), [])
        callback(sid, "+15555550101", "queued")
        callback(sid, "+15555550101", "delivered")
        self.assertEqual([r["deliveryEvidence"] for r in self.conversation.delivery_observations()], [False, True])


if __name__ == "__main__":
    unittest.main()
