#!/bin/bash

LOG=".git_hooks_logs/cleanup.log"
mkdir -p .git_hooks_logs

echo "$(date) - Starting cleanup..." >> $LOG

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No color

echo -e "${YELLOW}🔄 Fetching latest remote branches...${NC}"
git fetch --prune

echo -e "${GREEN}---------------------------------------"
echo -e " 🧹 Cleaning up local branches"
echo -e "---------------------------------------${NC}"

# Protected branches
PROTECTED_BRANCHES="^(main|dev|local)$"
CURRENT_BRANCH=$(git branch --show-current)

echo -e "${YELLOW}Skipping protected branches: main, dev, local${NC}"
echo -e "${BLUE}Current branch: $CURRENT_BRANCH${NC}"

# -------------------------
# FUNCTION: safe_delete
# -------------------------
safe_delete() {
  branch="$1"
  reason="$2"

  # Remove leading spaces from branch name
  branch=$(echo "$branch" | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')

  if [[ "$branch" =~ $PROTECTED_BRANCHES ]]; then
    echo -e "${YELLOW}⏭  Skipping protected branch: $branch${NC}"
    return
  fi

  if [[ "$branch" == "$CURRENT_BRANCH" ]]; then
    echo -e "${YELLOW}⏭  Skipping current branch: $branch${NC}"
    return
  fi

  if [[ -z "$branch" ]]; then
    return
  fi

  echo -e "${RED}🗑  Deleting branch: $branch (Reason: $reason)${NC}"
  echo "$(date) - Deleted $branch - $reason" >> $LOG

  git branch -D "$branch"
}

# -------------------------
# 1. Delete merged dev feature/bugfix/hotfix branches
# -------------------------
echo -e "${GREEN}🧪 Removing merged development branches (feature/, bugfix/, hotfix/)...${NC}"

for branch in $(git branch --merged dev | grep -E '(feature/|bugfix/|hotfix/)' | grep -v '^\*'); do
  safe_delete "$branch" "merged into dev"
done

# -------------------------
# 2. Delete merged refactor/chore/docs/task branches
# -------------------------
echo -e "${GREEN}🧪 Removing merged secondary branches (chore/, task/, refactor/, docs/)...${NC}"

for branch in $(git branch --merged dev | grep -E '(chore/|task/|refactor/|docs/)' | grep -v '^\*'); do
  safe_delete "$branch" "merged into dev"
done

# -------------------------
# 3. Delete release branches (always safe after merging)
# -------------------------
echo -e "${GREEN}🏷  Removing release/* branches...${NC}"

for branch in $(git branch | grep -E '^[[:space:]]*release/' | grep -v '^\*'); do
  # Check if release branch is merged to main or dev
  if git branch --merged main | grep -q "$branch" || git branch --merged dev | grep -q "$branch"; then
    safe_delete "$branch" "release branch merged"
  else
    echo -e "${YELLOW}⏭  Keeping unmerged release branch: $branch${NC}"
  fi
done

# -------------------------
# 4. Delete experiment branches (local only)
# -------------------------
echo -e "${GREEN}🧪 Cleaning experiment branches (experiment/*)...${NC}"

for branch in $(git branch | grep -E '^[[:space:]]*experiment/' | grep -v '^\*'); do
  safe_delete "$branch" "experiment branch"
done

# -------------------------
# 5. Show remaining branches that weren't cleaned up
# -------------------------
echo -e "${GREEN}---------------------------------------"
echo -e " 📊 Cleanup Summary"
echo -e "---------------------------------------${NC}"

echo -e "${BLUE}Remaining branches:${NC}"
git branch

# Check why specific branches remain
echo -e "${YELLOW}🔍 Analyzing remaining branches...${NC}"

for branch in $(git branch | grep -v '^\*' | sed 's/^[[:space:]]*//'); do
  if [[ "$branch" =~ $PROTECTED_BRANCHES ]]; then
    continue
  fi
  
  if ! git branch --merged dev | grep -q "$branch"; then
    echo -e "${YELLOW}  • $branch - Not merged into dev${NC}"
  fi
done

echo -e "${GREEN}✨ Cleanup completed!${NC}"
echo "$(date) - Cleanup finished." >> $LOG