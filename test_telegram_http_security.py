import io
import json
import os
import unittest
from unittest.mock import patch
from urllib.error import URLError

import bot


class TelegramHTTPSecurityTests(unittest.TestCase):

    def setUp(self):
        self.env = patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": "SECRET_TEST_TOKEN_123",
                "TELEGRAM_CHAT_ID": "-100123456789"
            }
        )
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_success_response(self):
        response = io.BytesIO(json.dumps({
            "ok": True,
            "result": {"message_id": 123}
        }).encode())

        with patch("bot.urlopen", return_value=response) as mock:
            bot.notify("test", telegram=True)

        mock.assert_called_once()

    def test_network_error_hides_token(self):
        with patch(
            "bot.urlopen",
            side_effect=URLError(
                "https://api.telegram.org/"
                "botSECRET_TEST_TOKEN_123/sendMessage"
            )
        ):
            with self.assertRaises(RuntimeError) as caught:
                bot.notify("test", telegram=True)

        self.assertNotIn(
            "SECRET_TEST_TOKEN_123",
            str(caught.exception)
        )

    def test_rejected_response(self):
        response = io.BytesIO(b'{"ok":false}')

        with patch("bot.urlopen", return_value=response):
            with self.assertRaises(RuntimeError):
                bot.notify("test", telegram=True)

    def test_invalid_json(self):
        response = io.BytesIO(b'not valid json')

        with patch("bot.urlopen", return_value=response):
            with self.assertRaises(RuntimeError):
                bot.notify("test", telegram=True)

    def test_private_chat_blocked(self):
        with patch.dict(
            os.environ,
            {"TELEGRAM_CHAT_ID": "12345"}
        ):
            with patch("bot.urlopen") as mock:
                with self.assertRaises(RuntimeError):
                    bot.notify("test", telegram=True)
                mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
