"""Offline lifetime boundaries, without native Rasa or network startup."""
import asyncio
from types import SimpleNamespace
import unittest

from shop_demo.whatsapp_launcher import drive


class LifetimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_owned_turn_limit_stops_processing(self):
        calls = []
        async def handle():
            calls.append("turn")
            return True
        async def notify():
            calls.append("shipping-check")
        host = SimpleNamespace(assert_safe=lambda: None, handle_next=handle, notify_shipments=notify)
        self.assertEqual(await drive(host, asyncio.Event(), max_turns=2), 2)
        self.assertEqual(calls, ["turn", "shipping-check", "turn", "shipping-check"])

    async def test_stop_requested_before_run_does_not_process_or_notify(self):
        async def refused():
            raise AssertionError("No work should start")
        host = SimpleNamespace(assert_safe=lambda: None, handle_next=refused, notify_shipments=refused)
        stop = asyncio.Event()
        stop.set()
        self.assertEqual(await drive(host, stop), 0)

    async def test_time_limit_does_not_consume_another_saved_turn(self):
        async def refused():
            raise AssertionError("No work should start")
        host = SimpleNamespace(assert_safe=lambda: None, handle_next=refused, notify_shipments=refused)
        self.assertEqual(await drive(host, asyncio.Event(), seconds=0), 0)


if __name__ == "__main__":
    unittest.main()
