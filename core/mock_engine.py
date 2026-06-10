"""Backward-compatible alias for the production response collector."""

from .response_collector import ResponseCollector


MockSpeechEngine = ResponseCollector

__all__ = ["MockSpeechEngine"]
