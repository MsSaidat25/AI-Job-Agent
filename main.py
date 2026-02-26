#!/usr/bin/env python3
"""
Entry point for the AI Job Application Agent.

Usage:
    python main.py

Environment variables:
    ANTHROPIC_API_KEY   — required
    AGENT_MODEL         — optional, defaults to claude-sonnet-4-6
    ENCRYPT_USER_DATA   — optional, defaults to true
"""
import sys

# Ensure project root is on the path regardless of how the script is invoked
import os
sys.path.insert(0, os.path.dirname(__file__))

from src.ui import run

if __name__ == "__main__":
    run()
