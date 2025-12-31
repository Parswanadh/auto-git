#!/usr/bin/env python3
"""
Auto-GIT Night Monitor - Tracks progress of autonomous repo creation
"""
import os
import time
import json
from datetime import datetime
from pathlib import Path

def monitor():
    print("="*70)
    print("Auto-GIT NIGHT MONITOR")
    print("="*70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nMonitoring output/repos/ for new projects...\n")

    output_dir = Path("./output/repos")
    output_dir.mkdir(parents=True, exist_ok=True)

    last_count = 0
    check_interval = 60  # Check every minute

    while True:
        repos = list(output_dir.iterdir())
        current_count = len(repos)

        if current_count > last_count:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] NEW REPO CREATED!")
            for repo in repos[last_count:]:
                print(f"  - {repo.name}")
                files = list(repo.iterdir())
                print(f"    Files: {', '.join([f.name for f in files])}")

            last_count = current_count

            if current_count >= 5:
                print("\n" + "="*70)
                print("ALL 5 REPOS COMPLETED!")
                print("="*70)
                break

        time.sleep(check_interval)

if __name__ == "__main__":
    monitor()
