#!/bin/bash

# Sync all branches
git fetch --prune

# Delete merged feature/bugfix branches from dev
git branch --merged dev | grep -E 'feature/|bugfix/' | xargs -n 1 git branch -d

# Delete local release branches merged to main
git branch --merged main | grep -E 'release/' | xargs -n 1 git branch -d

# Force delete local experiment branches
git branch | grep -E 'experiment/|spike/' | xargs -n 1 git branch -D

# Optional: Delete remote merged branches
# git push origin --delete $(git branch -r --merged dev | grep -E 'feature/|bugfix/' | sed 's/origin\///')