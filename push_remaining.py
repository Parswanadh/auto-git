#!/usr/bin/env python3
"""Push remaining 2 repos - just upload files via GitHub API"""
import subprocess
from pathlib import Path

# Get gh token
token = subprocess.check_output(['gh', 'auth', 'token']).decode().strip()

from github import Github
from github import Auth
from github import GithubException

g = Github(auth=Auth.Token(token))
user = g.get_user()

base_dir = Path('./output/repos')

# 1. sparse-attention-4gb
print("[1/2] sparse-attention-4gb...")
repo1_dir = base_dir / 'auto-git-sparse-attention-4gb-20251230-020519'

try:
    repo = user.get_repo('auto-git-sparse-attention-4gb-20251230-020519')
except GithubException:
    repo = user.create_repo(
        name='auto-git-sparse-attention-4gb-20251230-020519',
        description='Auto-GIT: Block-diagonal sparse attention for 4GB VRAM',
        private=False
    )

# Upload files
for file in repo1_dir.iterdir():
    if file.is_file() and file.suffix in ['.py', '.md', '.txt']:
        try:
            content = file.read_text(encoding='utf-8')
            repo.create_file(file.name, 'Upload ' + file.name, content)
            print(f"  {file.name}")
        except:
            pass  # File exists

# 2. quantized-vlm-edge
print("\n[2/2] quantized-vlm-edge...")
repo2_dir = base_dir / 'auto-git-quantized-vlm-edge-20251230-020519'

try:
    repo = user.get_repo('auto-git-quantized-vlm-edge-20251230-020519')
except GithubException:
    repo = user.create_repo(
        name='auto-git-quantized-vlm-edge-20251230-020519',
        description='Auto-GIT: 4-bit quantized VLM for edge devices',
        private=False
    )

# Upload files
for file in repo2_dir.iterdir():
    if file.is_file() and file.suffix in ['.py', '.md', '.txt']:
        try:
            content = file.read_text(encoding='utf-8')
            repo.create_file(file.name, 'Upload ' + file.name, content)
            print(f"  {file.name}")
        except:
            pass  # File exists

print("\n[SUCCESS] Done!")
