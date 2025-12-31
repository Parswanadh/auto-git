#!/usr/bin/env python3
"""Push all repos to GitHub"""
import os
from pathlib import Path
from datetime import datetime

try:
    from github import Github
except ImportError:
    print("Installing PyGithub...")
    os.system("pip install PyGithub -q")
    from github import Github

token = os.getenv("GITHUB_TOKEN")
if not token:
    print("ERROR: GITHUB_TOKEN not set")
    print("Please set it with: set GITHUB_TOKEN=your_token")
    exit(1)

print("="*70)
print("Pushing 5 repos to GitHub")
print("="*70)

g = Github(token)
user = g.get_user()
print(f"Authenticated as: {user.login}")

base_dir = Path("./output/repos")
repos = list(base_dir.iterdir())

print(f"\nFound {len(repos)} repos to push\n")

success_count = 0

for repo_dir in sorted(repos):
    if not repo_dir.is_dir():
        continue

    repo_name = repo_dir.name
    print(f"[{repos.index(repo_dir)+1}/{len(repos)}] Pushing {repo_name}...")

    try:
        repo = user.create_repo(
            name=repo_name,
            description=f"Auto-GIT: Novel deep learning architecture for 4GB VRAM constraint\nCreated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            private=False,
            auto_init=False
        )
        print(f"  Created: {repo.html_url}")

        for file in sorted(repo_dir.iterdir()):
            if file.is_file():
                content = file.read_text(encoding="utf-8")
                repo.create_file(file.name, f"Add {file.name}", content)
                print(f"    - {file.name}")

        success_count += 1
        print(f"  [SUCCESS]")

    except Exception as e:
        print(f"  [ERROR] {e}")

print("\n" + "="*70)
print(f"PUSHED: {success_count}/{len(repos)} repos to GitHub")
print("="*70)
