import unittest
from unittest.mock import patch

import bot


class ProviderSecurityTests(unittest.TestCase):

    def test_api_key_never_appears_in_error(self):
        secret = "TEST_SECRET_DO_NOT_LEAK"

        with patch(
            "bot.urlopen",
            side_effect=OSError("Request failed: " + secret)
        ):
            with self.assertRaises(RuntimeError) as result:
                bot.fetch_twelve_data(secret)

        self.assertNotIn(secret, str(result.exception))

    def test_provider_error_does_not_leak(self):
        with patch(
            "bot.urlopen",
            side_effect=ValueError("sensitive-provider-detail")
        ):
            with self.assertRaises(RuntimeError) as result:
                bot.fetch_twelve_data("fake-key")

        self.assertNotIn(
            "sensitive-provider-detail",
            str(result.exception)
        )


if __name__ == "__main__":
    unittest.main()
