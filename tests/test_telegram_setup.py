import unittest
from unittest.mock import patch
from telegram_setup import validate_bot, find_private_recipient


class TelegramSetupTests(unittest.TestCase):
    def test_token_must_belong_to_expected_bot(self):
        with patch("telegram_setup.api_call", return_value={"username": "adam_mirror_007_bot"}):
            validate_bot("test", "@adam_mirror_007_bot")
            with self.assertRaises(ValueError):
                validate_bot("test", "another_bot")

    def test_pairing_does_not_guess_latest_or_group_chat(self):
        updates = [{"message": {"chat": {"type": "private", "id": 11}, "text": "/start"}},
                   {"message": {"chat": {"type": "group", "id": -22}, "text": "/start ADAM12345"}},
                   {"message": {"chat": {"type": "private", "id": 33}, "text": "/start ADAM12345"}}]
        with patch("telegram_setup.api_call", return_value=updates):
            self.assertEqual(find_private_recipient("test", "ADAM12345"), "33")
        updates.append({"message": {"chat": {"type": "private", "id": 44}, "text": "/start ADAM12345"}})
        with patch("telegram_setup.api_call", return_value=updates), self.assertRaises(ValueError):
            find_private_recipient("test", "ADAM12345")
