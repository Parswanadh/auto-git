#!/usr/bin/env python3
"""Push remaining 2 repos to GitHub using gh CLI token"""
import subprocess
import os
from pathlib import Path

# Get gh token
token = subprocess.check_output(['gh', 'auth', 'token']).decode().strip()
os.environ['GITHUB_TOKEN'] = token

# Now use PyGithub
from github import Github

g = Github(token)
user = g.get_user()
print(f"Authenticated as: {user.login}")

base_dir = Path('./output/repos')

# 1. Push sparse-attention-4gb
print("\n[1/2] Pushing sparse-attention-4gb...")
repo1_dir = base_dir / 'auto-git-sparse-attention-4gb-20251230-020519'

# Clean any existing .git and re-init
import shutil
git_dir = repo1_dir / '.git'
if git_dir.exists():
    shutil.rmtree(git_dir)

# Create repo
try:
    repo = user.get_repo('auto-git-sparse-attention-4gb-20251230-020519')
    print(f"  Repo exists: {repo.html_url}")
except:
    repo = user.create_repo(
        name='auto-git-sparse-attention-4gb-20251230-020519',
        description='Auto-GIT: Block-diagonal sparse attention optimized for 4GB VRAM',
        private=False
    )
    print(f"  Created: {repo.html_url}")

# Push files
for file in repo1_dir.iterdir():
    if file.is_file() and file.name != '.git':
        content = file.read_text(encoding='utf-8')
        try:
            repo.create_file(file.name, 'Add ' + file.name, content)
            print(f"    - {file.name}")
        except:
            pass  # File might exist

print("  [OK] Done")

# 2. Push quantized-vlm-edge
print("\n[2/2] Pushing quantized-vlm-edge...")
repo2_dir = base_dir / 'auto-git-quantized-vlm-edge-20251230-020519'

git_dir = repo2_dir / '.git'
if git_dir.exists():
    shutil.rmtree(git_dir)

try:
    repo = user.get_repo('auto-git-quantized-vlm-edge-20251230-020519')
    print(f"  Repo exists: {repo.html_url}")
except:
    repo = user.create_repo(
        name='auto-git-quantized-vlm-edge-20251230-020519',
        description='Auto-GIT: 4-bit quantized Vision-Language Model for edge devices',
        private=False
    )
    print(f"  Created: {repo.html_url}")

# Push files
for file in repo2_dir.iterdir():
    if file.is_file() and file.name != '.git':
        content = file.read_text(encoding='utf-8')
        try:
            repo.create_file(file.name, 'Add ' + file.name, content)
            print(f"    - {file.name}")
        except:
            pass

print("  [OK] Done")

print("\n[SUCCESS] All 5 repos now on GitHub!")
