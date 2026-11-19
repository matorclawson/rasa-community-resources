"""Offline settings tests with synthetic values; no real environment reads."""
import unittest
from shop_demo.whatsapp_settings import Settings, ConfigurationError


class ConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.values = {"TWILIO_ACCOUNT_SID": "AC" + "1" * 32,
                       "TWILIO_AUTH_TOKEN": "offline-account-token",
                       "SHOP_WHATSAPP_CUSTOMER": "+15555550101", "SHOP_SHEET_ID": "a" * 25,
                       "GOOGLE_TOKEN_JSON": "offline-google", "OPENAI_API_KEY": "offline-model",
                       "RASA_PRO_LICENSE": "offline-license", "CODESPACE_NAME": "offline-venue"}

    def test_exact_account_token_names_and_configured_customer(self):
        settings = Settings.environment(self.values)
        self.assertEqual(settings.auth_token.get_secret_value(), "offline-account-token")
        self.assertEqual(settings.customer, "+15555550101")
        self.assertEqual(settings.sender, "+14155238886")
        self.assertEqual(settings.public_base, "https://offline-venue-8080.app.github.dev")

    def test_api_key_sid_refused_without_disclosing_it(self):
        self.values["TWILIO_ACCOUNT_SID"] = "SK" + "2" * 32
        with self.assertRaises(ConfigurationError) as error:
            Settings.environment(self.values)
        self.assertNotIn(self.values["TWILIO_ACCOUNT_SID"], str(error.exception))

    def test_no_automatic_customer_discovery(self):
        del self.values["SHOP_WHATSAPP_CUSTOMER"]
        with self.assertRaisesRegex(ConfigurationError, "SHOP_WHATSAPP_CUSTOMER"):
            Settings.environment(self.values)

    def test_no_sender_secret_or_api_key_sid_required(self):
        self.assertNotIn("TWILIO_API_KEY_SID", self.values)
        self.assertNotIn("TWILIO_WHATSAPP_FROM", self.values)
        Settings.environment(self.values)

    def test_legacy_api_key_secret_cannot_replace_account_auth_token(self):
        del self.values["TWILIO_AUTH_TOKEN"]
        self.values["TWILIO_API_KEY_SECRET"] = "offline-key-secret"
        with self.assertRaisesRegex(ConfigurationError, "TWILIO_AUTH_TOKEN"):
            Settings.environment(self.values)

    def test_missing_settings_error_contains_names_only(self):
        del self.values["GOOGLE_TOKEN_JSON"]
        with self.assertRaises(ConfigurationError) as error:
            Settings.environment(self.values)
        self.assertEqual(str(error.exception), "Missing settings: GOOGLE_TOKEN_JSON")


if __name__ == "__main__":
    unittest.main()
