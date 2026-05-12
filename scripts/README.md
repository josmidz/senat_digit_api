# Git Hooks Package

hooks/
 ├── pre-checkout          # Validate new branch creation name
 ├── post-checkout         # Auto-install hooks if missing
 ├── pre-commit            # Prevent commit to protected branches
 ├── pre-push              # Validate branch before push
 ├── pre-merge-commit      # Validate merges locally
scripts/
 └── install-git-hooks.sh  # Installer for .git/hooks/*


This package includes:
- Automated Git hooks installer
- Branch validation hooks
- Commit message prefix enforcement
- Merge validation
- Cleanup utility
- Logging system

Run:
```
bash scripts/install-git-hooks.sh
```

Logs stored in `.git_hooks_logs/`.




chmod +x hooks/pre-merge-commit
chmod +x hooks/pre-push
chmod +x hooks/pre-commit

chmod +x scripts/install-git-hooks.sh

bash scripts/install-git-hooks.sh

scripts/cleanup.sh
chmod +x scripts/cleanup.sh

git rm -r --cached .git_hooks_logs

