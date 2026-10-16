#!/usr/bin/env bash
set -e

echo "=> Checking git status..."
git status

# Check if there are modified tracked files
if [[ -n $(git status -s | grep -E '^ [MADRC]') ]]; then
    echo "=> Modified tracked files detected. Stashing local changes..."
    git stash
    STASHED=true
else
    echo "=> Working tree clean or only untracked files. No stash needed."
    STASHED=false
fi

# Fetch instructor updates directly
echo "=> Fetching latest materials from instructor repository..."
git fetch https://github.com/aaron-recompile/AI_Finance.git main

# Merge instructor updates
echo "=> Merging updates..."
git merge FETCH_HEAD --no-edit

# Pop stash if we stashed earlier
if [ "$STASHED" = true ]; then
    echo "=> Restoring your stashed local changes..."
    git stash pop
fi

# Push updated workspace to your personal fork
echo "=> Pushing updates to your personal fork (danny38888)..."
git push origin main

echo "=> Weekly update complete!"
