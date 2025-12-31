#!/usr/bin/env python
"""Test if GitHub token loads correctly"""

from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

github_token = os.getenv("GITHUB_TOKEN")

if github_token:
    print("✅ GitHub Token loaded successfully!")
    print(f"   Token starts with: {github_token[:20]}...")
    print(f"   Token length: {len(github_token)} characters")
else:
    print("❌ GitHub Token NOT found!")
    print("   Make sure GITHUB_TOKEN is set in .env file")
