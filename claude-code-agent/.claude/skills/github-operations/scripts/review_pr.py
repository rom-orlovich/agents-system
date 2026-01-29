#!/usr/bin/env python3
"""
Review a GitHub PR using the GitHub API.
Usage: python review_pr.py OWNER REPO PR_NUMBER
"""
import sys
import asyncio
import os
from pathlib import Path

# Add project root to path dynamically
# This works whether running from Docker, local, or cloud
script_dir = Path(__file__).parent.absolute()
project_root = script_dir.parent.parent.parent.parent  # Go up 4 levels from scripts/
sys.path.insert(0, str(project_root))

from core.github_client import github_client


def should_skip_file(filename: str, additions: int, deletions: int) -> tuple[bool, str]:
    """
    Determine if a file should be skipped from detailed review.

    Returns:
        (should_skip, reason)
    """
    # Skip large dependency lock files
    if filename.endswith(('package-lock.json', 'yarn.lock', 'pnpm-lock.yaml', 'Gemfile.lock', 'poetry.lock', 'Cargo.lock')):
        return True, "dependency lock file"

    # Skip minified/bundled files
    if '.min.' in filename or '.bundle.' in filename:
        return True, "minified/bundled file"

    # Skip very large files (>1000 line changes)
    total_changes = additions + deletions
    if total_changes > 1000:
        return True, f"very large file ({total_changes} line changes)"

    # Skip binary files (images, fonts, etc.)
    binary_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.woff', '.woff2', '.ttf', '.eot', '.svg', '.mp4', '.webm')
    if filename.lower().endswith(binary_extensions):
        return True, "binary file"

    # Skip generated documentation
    if 'node_modules/' in filename or 'dist/' in filename or 'build/' in filename or '.next/' in filename:
        return True, "generated/build artifact"

    return False, ""


async def review_pr(owner: str, repo: str, pr_number: int):
    """
    Fetch and display PR information for analysis.

    Args:
        owner: Repository owner
        repo: Repository name
        pr_number: PR number
    """
    try:
        # Get PR details
        pr = await github_client.get_pull_request(owner, repo, pr_number)

        # Get files changed
        all_files = await github_client.get_pr_files(owner, repo, pr_number)

        # Filter files
        reviewable_files = []
        skipped_files = []
        for file in all_files:
            should_skip, reason = should_skip_file(
                file['filename'],
                file['additions'],
                file['deletions']
            )
            if should_skip:
                skipped_files.append((file, reason))
            else:
                reviewable_files.append(file)

        files = reviewable_files
        
        # Print PR info for agent to analyze
        print(f"# PR #{pr_number}: {pr['title']}")
        print(f"\n## Details")
        print(f"- **State**: {pr['state']}")
        print(f"- **Author**: {pr['user']['login']}")
        print(f"- **Base**: {pr['base']['ref']}")
        print(f"- **Head**: {pr['head']['ref']}")
        print(f"- **Mergeable**: {pr.get('mergeable', 'unknown')}")
        print(f"- **Additions**: +{pr['additions']}")
        print(f"- **Deletions**: -{pr['deletions']}")
        print(f"- **Changed Files**: {pr['changed_files']}")
        
        print(f"\n## Description")
        print(pr.get('body', 'No description provided'))
        
        print(f"\n## Reviewable Files ({len(files)} files)")
        if skipped_files:
            print(f"\n### ⏭️ Skipped Files ({len(skipped_files)} files - too large or not reviewable)")
            for file, reason in skipped_files:
                print(f"- `{file['filename']}` - {reason} (+{file['additions']} -{file['deletions']})")

        print(f"\n### 📋 Files to Review")
        for file in files:
            status_emoji = {
                'added': '🆕',
                'modified': '📝',
                'removed': '🗑️',
                'renamed': '📛'
            }.get(file['status'], '📄')
            
            print(f"\n### {status_emoji} {file['filename']}")
            print(f"- Status: {file['status']}")
            print(f"- Changes: +{file['additions']} -{file['deletions']}")
            
            # Print patch if available (first 500 chars)
            if 'patch' in file and file['patch']:
                patch_preview = file['patch'][:500]
                if len(file['patch']) > 500:
                    patch_preview += "\n... (truncated)"
                print(f"- Patch preview:\n```diff\n{patch_preview}\n```")
        
        return pr, files
        
    except Exception as e:
        print(f"Error fetching PR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python review_pr.py OWNER REPO PR_NUMBER", file=sys.stderr)
        print("Example: python review_pr.py rom-orlovich agents-system 14", file=sys.stderr)
        sys.exit(1)
    
    owner = sys.argv[1]
    repo = sys.argv[2]
    try:
        pr_number = int(sys.argv[3])
    except ValueError:
        print(f"Error: PR_NUMBER must be an integer, got '{sys.argv[3]}'", file=sys.stderr)
        sys.exit(1)
    
    asyncio.run(review_pr(owner, repo, pr_number))
