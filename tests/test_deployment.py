from __future__ import annotations

import os
import unittest
from unittest.mock import Mock, patch

from outsidequest.adventure import generate_adventure
from outsidequest.deployment import is_public_mode
from outsidequest.models import validate_preferences


class PublicModeDetectionTests(unittest.TestCase):
    def test_defaults_to_local_mode(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(is_public_mode())

    def test_explicit_flag_enables_public_mode(self) -> None:
        with patch.dict(os.environ, {"OUTSIDEQUEST_PUBLIC_MODE": "true"}, clear=True):
            self.assertTrue(is_public_mode())

    def test_render_environment_enables_public_mode(self) -> None:
        with patch.dict(os.environ, {"RENDER": "true"}, clear=True):
            self.assertTrue(is_public_mode())

    def test_explicit_false_overrides_render(self) -> None:
        with patch.dict(os.environ, {"RENDER": "true", "OUTSIDEQUEST_PUBLIC_MODE": "false"}, clear=True):
            self.assertFalse(is_public_mode())


class PublicGenerationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.preferences = validate_preferences(30, "Medium", ["Nature"], 0, "Outside")

    @patch("outsidequest.adventure.requests.post")
    def test_public_mode_uses_labeled_fallback_without_calling_ollama(self, post: Mock) -> None:
        with patch.dict(os.environ, {"OUTSIDEQUEST_PUBLIC_MODE": "true"}, clear=True):
            result = generate_adventure(self.preferences)
        post.assert_not_called()
        self.assertEqual(result.source, "fallback")
        self.assertIn("public deployment", result.notice or "")

    @patch("outsidequest.adventure.requests.post", side_effect=OSError)
    def test_local_mode_still_tries_ollama(self, post: Mock) -> None:
        import requests

        post.side_effect = requests.ConnectionError()
        with patch.dict(os.environ, {}, clear=True):
            result = generate_adventure(self.preferences)
        post.assert_called()
        self.assertEqual(result.source, "fallback")


if __name__ == "__main__":
    unittest.main()
