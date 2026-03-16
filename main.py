#!/usr/bin/env python3
"""
Copyright 2026 AVIEN SOLUTIONS INC (www.aviensolutions.com).
All Rights Reserved.
No part of this software or any of its contents may be reproduced, copied,
modified or adapted, without the prior written consent of the author, unless
otherwise indicated for stand-alone materials.
For permission requests, write to the publisher at the email address below:
avien@aviensolutions.com
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.

Entry point for the AI Job Application Agent.

Usage:
    python main.py

Environment variables:
    ANTHROPIC_API_KEY   — required
    AGENT_MODEL         — optional, defaults to claude-sonnet-4-6
    ENCRYPT_USER_DATA   — optional, defaults to true
"""
import os
import sys

# Ensure project root is on the path regardless of how the script is invoked
sys.path.insert(0, os.path.dirname(__file__))

from src.ui import run  # noqa: E402

if __name__ == "__main__":
    run()
