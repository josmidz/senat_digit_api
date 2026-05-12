
<!-- 1. Set Up Log Rotation (Prevents log files from consuming disk space) -->

# WARNING: This will DELETE untracked files
git clean -fd  # -f: force, -d: directories
git reset --hard
git pull

# Create the log directory
sudo mkdir -p /var/log/deployments

# Create logrotate configuration
sudo nano /etc/logrotate.d/deployments

<!-- Paste this configuration: -->
/var/log/deployments/*.log {
    daily
    rotate 30
    compress
    missingok
    notifempty
    create 0644 deploy_user deploy_user  # Change to your user/group
}

<!-- Verify it works: -->
# Test configuration
sudo logrotate -d /etc/logrotate.d/deployments

# Force immediate rotation (for testing)
sudo logrotate -vf /etc/logrotate.d/deployments

<!-- 2. Add Deployment Notifications (Optional) -->
<!-- A) For Slack: -->
# Add to the END of deploy.sh (before final success message)
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "text": "🚀 Deployment to '$BRANCH' completed\n• Commit: '${GIT_COMMIT:-unknown}'\n• Log: $(tail -n 5 '$LOG_FILE' | sed 's/\"/\\"/g')"
  }' \
  https://hooks.slack.com/services/YOUR/WEBHOOK/URL

  <!-- B) For Email (using mailutils): -->
  # Install mailutils
sudo apt install mailutils

# Add to deploy.sh
echo "Deployment to $BRANCH completed at $(date)" | \
  mail -s "Deployment Notification" admin@yourdomain.com

<!-- 3. Set Secure Permissions -->
# Make the script executable
sudo chmod +x /home/cobilgo_adm_vps025/BASH/FINANCE_SH/deploy.sh

# Set ownership (adjust user/group as needed)
sudo chown your_user:your_group /home/cobilgo_adm_vps025/BASH/FINANCE_SH/deploy.sh

# Restrict access
sudo chmod 750 /home/cobilgo_adm_vps025/BASH/FINANCE_SH/deploy.sh  # Only owner can edit/execute

<!-- 4. Verify Supervisor Permissions -->
# Edit sudoers file
sudo visudo

# Add this line (replace 'your_user' with actual username)
your_user ALL=(ALL) NOPASSWD: /usr/bin/supervisorctl restart minfinance_api_*
<!-- 5. Test the Full Flow -->
# Manually trigger a test deployment
/home/cobilgo_adm_vps025/BASH/FINANCE_SH/deploy.sh dev

# Check logs
tail -f /var/log/deployments/latest_dev.log

<!-- Troubleshooting Checklist -->
<!-- If something fails: -->

<!-- Check permissions: -->
```bash
ls -la /home/cobilgo_adm_vps025/BASH/FINANCE_SH/deploy.sh
# Verify logs exist:
ls -la /var/log/deployments/

# Test supervisor commands manually:
sudo supervisorctl status
sudo supervisorctl restart minfinance_api_dev
```

