"""Host-owned review, order and send state for one admitted WhatsApp customer."""
from __future__ import annotations

import asyncio
import re

from zeo_core.integrations.twilio_whatsapp import ChannelInbound, ChannelReceipt, SendWhatsAppRequest

from .models import Order, Quote, money, review
from .whatsapp_webhook import IntakeHeld, Journal


class Conversation:
    def __init__(self, path, *, customer, sender, public_base, channel, assistant, orders, clock,
                 minimum_send_interval=3):
        self.journal = Journal(path)
        self.db = self.journal.db
        self.customer, self.sender = customer, sender
        self.public_base, self.channel = public_base.rstrip("/"), channel
        self.assistant, self.orders, self.clock = assistant, orders, clock
        self.minimum_send_interval = minimum_send_interval
        self.last_send_attempt = None
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS wa_outgoing (
                key TEXT PRIMARY KEY, recipient TEXT NOT NULL, body TEXT NOT NULL, receipt TEXT
            );
            CREATE TABLE IF NOT EXISTS wa_review (
                singleton INTEGER PRIMARY KEY CHECK(singleton=1), quote TEXT NOT NULL, receipt TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS wa_contacts (
                order_number TEXT PRIMARY KEY, recipient TEXT NOT NULL, notified INTEGER NOT NULL DEFAULT 0
            );
        """)

    def close(self):
        self.journal.close()

    def assert_safe(self):
        if self.db.execute("SELECT 1 FROM wa_inbox WHERE phase IN ('working','held')").fetchone():
            raise IntakeHeld("INSPECT_ORIGINAL_TURN")
        if self.db.execute("SELECT 1 FROM wa_outgoing WHERE receipt IS NULL").fetchone():
            raise IntakeHeld("INSPECT_ORIGINAL_SEND")

    async def send(self, key, text):
        if self.db.execute("SELECT 1 FROM wa_inbox WHERE phase='held'").fetchone():
            raise IntakeHeld("INSPECT_CHANGED_ORIGINAL_EVENT")
        if not isinstance(text, str) or not 0 < len(text) <= 1600:
            raise IntakeHeld("REPLY_EXCEEDS_CHANNEL_LIMIT")
        old = self.db.execute("SELECT recipient,body,receipt FROM wa_outgoing WHERE key=?", (key,)).fetchone()
        if old:
            if old[:2] != (self.customer, text) or old[2] is None:
                raise IntakeHeld("ORIGINAL_SEND_HELD_OR_CHANGED")
            return ChannelReceipt.model_validate_json(old[2])
        self.db.execute("INSERT INTO wa_outgoing VALUES(?,?,?,NULL)", (key, self.customer, text))
        request = SendWhatsAppRequest(to=self.customer, from_number=self.sender, body=text,
                                     status_callback=self.public_base + "/twilio/status")
        try:
            loop = asyncio.get_running_loop()
            if self.last_send_attempt is not None:
                await asyncio.sleep(max(0, self.minimum_send_interval - (loop.time() - self.last_send_attempt)))
            self.last_send_attempt = loop.time()
            receipt = await asyncio.to_thread(self.channel.send, request)
            if (receipt.to != self.customer
                    or not re.fullmatch(r"SM[0-9a-fA-F]{32}", receipt.provider_message_id)
                    or receipt.status not in {"queued", "accepted", "sending", "sent", "delivered", "read"}
                    or receipt.error_code is not None):
                raise IntakeHeld("SEND_RECEIPT_NOT_ADMITTED")
            self.db.execute("UPDATE wa_outgoing SET receipt=? WHERE key=?", (receipt.model_dump_json(), key))
            return receipt
        except BaseException:
            # Persisted NULL is an uncertain effect. A retry is never automatic.
            raise IntakeHeld("INSPECT_ORIGINAL_SEND") from None

    def latest_order(self):
        row = self.db.execute("SELECT order_number FROM wa_contacts ORDER BY rowid DESC LIMIT 1").fetchone()
        return row[0] if row else None

    async def handle_next(self):
        self.assert_safe()
        row = self.db.execute("SELECT event_id,event FROM wa_inbox WHERE phase='saved' ORDER BY sequence LIMIT 1").fetchone()
        if row is None:
            return False
        event_id, raw = row
        event = ChannelInbound.model_validate_json(raw)
        self.db.execute("UPDATE wa_inbox SET phase='working' WHERE event_id=?", (event_id,))
        try:
            if (event.sender_id != self.customer or event.conversation_id != self.customer
                    or event.recipient_id != self.sender):
                raise IntakeHeld("ORIGINAL_RECIPIENT_CHANGED")
            pending = self.db.execute("SELECT quote,receipt FROM wa_review WHERE singleton=1").fetchone()
            self.db.execute("DELETE FROM wa_review WHERE singleton=1")
            key = "reply:" + event_id
            affirmative = event.text.strip().casefold() == "confirm"
            if pending and affirmative and not event.media_count:
                quote = Quote.model_validate_json(pending[0])
                sent = ChannelReceipt.model_validate_json(pending[1])
                if (event.reply_to_message_id != sent.provider_message_id
                        or self.clock() >= quote.expires_at):
                    await self.send(key, "That confirmation is not bound to an active review. Ask for a new basket, then use WhatsApp Reply on its review.")
                else:
                    request_key = "whatsapp:" + event_id
                    if self.db.execute("SELECT phase FROM wa_inbox WHERE event_id=?", (event_id,)).fetchone() != ("working",):
                        raise IntakeHeld("ORIGINAL_EVENT_CHANGED_DURING_TURN")
                    order = await self.orders.place(quote.reference, request_key)
                    if (not isinstance(order, Order) or order.quote != quote or order.request_key != request_key):
                        raise IntakeHeld("ORIGINAL_ORDER_RESPONSE_CHANGED")
                    self.db.execute("INSERT INTO wa_contacts(order_number,recipient) VALUES(?,?)", (str(order.number), self.customer))
                    await self.send(key, f"Order {order.number} is placed. Total: {money(quote.total_cents, quote.currency)}.")
            elif affirmative:
                await self.send(key, "There is no active review. Ask for a basket, then use WhatsApp Reply on its review to confirm.")
            elif event.media_count or not event.text:
                await self.send(key, "Please send a new text message. The previous review is canceled.")
            elif event.text.strip().casefold() in {"cancel", "no", "stop"}:
                await self.send(key, "The review is canceled. No order was placed from it.")
            else:
                result = await self.assistant.respond(event, self.latest_order())
                if isinstance(result, Quote):
                    if self.clock() >= result.expires_at:
                        raise IntakeHeld("PRICE_REVIEW_EXPIRED")
                    lines = review(result).splitlines()
                    lines[-1] = "Use WhatsApp Reply on THIS review and send confirm before it expires. Any other message cancels it."
                    sent = await self.send(key, "\n".join(lines))
                    self.db.execute("INSERT INTO wa_review VALUES(1,?,?)", (result.model_dump_json(), sent.model_dump_json()))
                else:
                    await self.send(key, result)
            finished = self.db.execute("UPDATE wa_inbox SET phase='done' WHERE event_id=? AND phase='working'", (event_id,))
            if finished.rowcount != 1:
                raise IntakeHeld("ORIGINAL_EVENT_CHANGED_DURING_TURN")
            return True
        except BaseException:
            self.db.execute("UPDATE wa_inbox SET phase='held' WHERE event_id=?", (event_id,))
            raise

    async def notify_shipments(self):
        self.assert_safe()
        for number, recipient in self.db.execute("SELECT order_number,recipient FROM wa_contacts WHERE notified=0").fetchall():
            if recipient != self.customer:
                raise IntakeHeld("ORDER_RECIPIENT_CHANGED")
            order = await self.orders.lookup(number)
            if str(order.number) != number:
                raise IntakeHeld("ORDER_RESPONSE_CHANGED")
            if order.status == "shipped":
                await self.send("shipment:" + number, f"Your order {number} has shipped.")
                self.db.execute("UPDATE wa_contacts SET notified=1 WHERE order_number=?", (number,))

    def delivery_observations(self):
        # A queued/accepted/send result is never delivery evidence. Preserve all
        # signed callbacks; only expose those bound to our own saved SID/recipient.
        known = {}
        for key, recipient, raw in self.db.execute("SELECT key,recipient,receipt FROM wa_outgoing WHERE receipt IS NOT NULL"):
            receipt = ChannelReceipt.model_validate_json(raw)
            known[receipt.provider_message_id] = (key, recipient)
        result = []
        for (raw,) in self.db.execute("SELECT receipt FROM wa_callbacks ORDER BY sequence"):
            receipt = ChannelReceipt.model_validate_json(raw)
            own = known.get(receipt.provider_message_id)
            if own and own[1] == receipt.to:
                result.append({"key": own[0], "status": receipt.status,
                               "deliveryEvidence": receipt.status in {"delivered", "read"}})
        return result
