"""Pytest defaults for local/offline testing."""

import os

os.environ.setdefault("CLIENT_ID", "test-client-id")
os.environ.setdefault("CLIENT_SECRET", "test-client-secret")
os.environ.setdefault("ACCUBID_SCOPE", "openid accubid_agentic_ai")
