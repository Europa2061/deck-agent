import asyncio
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import AsyncMock

from backend.rpc import PiProcess


class RpcTests(unittest.IsolatedAsyncioTestCase):
    async def test_out_of_order_responses_and_unicode_line_separators(self):
        peer = Path(__file__).parent / "fixtures/rpc_peer.py"
        process = PiProcess([sys.executable, str(peer)], str(peer.parent), dict(os.environ), AsyncMock(), AsyncMock())
        try:
            await process.start()
            first, second = await asyncio.gather(process.call("first"), process.call("second"))
            self.assertEqual(first, {})
            self.assertEqual(second["text"], "a\u2028b\u2029c")
        finally:
            await process.close()
        self.assertIsNotNone(process.process.returncode)

    async def test_stop_clears_native_queue_before_abort(self):
        process = PiProcess([], "", {}, AsyncMock(), AsyncMock())
        process.call = AsyncMock(side_effect=[{"steering": ["old"], "followUp": []}, {}])
        queue = await process.stop()
        self.assertEqual([c.args[0] for c in process.call.await_args_list], ["clear_queue", "abort"])
        self.assertEqual(queue["steering"], ["old"])
