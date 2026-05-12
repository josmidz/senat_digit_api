# Database Seeding Scripts

This directory contains scripts for seeding the database after deployment.

## 🎯 Overview

The seed scripts are automatically triggered by the GitHub webhook after successful deployment.

## 📁 Structure

```
bash/seeds/
├── run.seed-all.sh          # Main seed script (called by webhook)
├── seedall_YYYYMMDD_HHMM.log  # Log files with timestamp
└── README.md                # This file
```

## 🚀 Automatic Execution

After each deployment, the webhook automatically runs:

```bash
cd /var/www/APPS/DEV/dev_senat_digit_api/bash/seeds
nohup ./run.seed-all.sh dev > seedall_20251120_1430.log 2>&1 &
```

**Features:**
- ✅ Runs in background (doesn't block deployment)
- ✅ Dynamic log file with timestamp
- ✅ Environment-aware (dev/prod)
- ✅ Deployment succeeds even if seed fails

## 📝 run.seed-all.sh Template

Create your `run.seed-all.sh` script like this:

```bash
#!/bin/bash

# Database Seeding Script
# Called automatically after deployment

ENV=$1

echo "========================================="
echo "🌱 Starting database seeding"
echo "Environment: $ENV"
echo "Time: $(date)"
echo "========================================="

# Validate environment
if [ -z "$ENV" ]; then
    echo "❌ ERROR: No environment specified"
    exit 1
fi

# Set project directory based on environment
case "$ENV" in
    dev)
        PROJECT_DIR="/var/www/APPS/DEV/dev_senat_digit_api"
        ;;
    prod)
        PROJECT_DIR="/var/www/APPS/PROD/prod_senat_digit_api"
        ;;
    *)
        echo "❌ ERROR: Unknown environment '$ENV'"
        exit 1
        ;;
esac

# Navigate to project
cd "$PROJECT_DIR" || exit 1

# Activate virtual environment
source .venv/bin/activate

# Run your seed commands here
echo "🌱 Seeding database..."

# Example: Run Python seed script
python -m app.seeds.seed_all

# Example: Run Alembic migrations
# alembic upgrade head

# Example: Run custom seed scripts
# python -m app.seeds.seed_users
# python -m app.seeds.seed_applications
# python -m app.seeds.seed_permissions

echo "========================================="
echo "✅ Database seeding completed!"
echo "Time: $(date)"
echo "========================================="
```

## 🔍 Monitoring

### View Seed Logs

```bash
# Latest log
tail -f bash/seeds/seedall_*.log

# Specific log
tail -f bash/seeds/seedall_20251120_1430.log

# All logs
ls -lh bash/seeds/seedall_*.log
```

### Check Seed Process

```bash
# Find running seed process
ps aux | grep run.seed-all.sh

# Check by PID (from webhook response)
ps -p <PID>
```

## ⚙️ Configuration

### Disable Automatic Seeding

If you don't want automatic seeding, simply remove or rename the `run.seed-all.sh` script:

```bash
mv run.seed-all.sh run.seed-all.sh.disabled
```

The webhook will skip seeding if the script doesn't exist.

### Manual Seeding

You can also run seeds manually:

```bash
cd /var/www/APPS/DEV/dev_senat_digit_api/bash/seeds
./run.seed-all.sh dev
```

## 📊 Webhook Response

The webhook returns seed information:

```json
{
  "message": "Deployment triggered for dev → dev",
  "log_file": "/var/log/deploy_dev_20251120_1430.log",
  "deploy_pid": 12345,
  "script": "/var/www/APPS/DEV/dev_senat_digit_api/bash/supervisor/rerun.sh",
  "environment": "dev",
  "seed_log_file": "/var/www/APPS/DEV/dev_senat_digit_api/bash/seeds/seedall_20251120_1430.log",
  "seed_pid": 12346
}
```

## 🐛 Troubleshooting

### Seed script not running

**Check if script exists:**
```bash
ls -la /var/www/APPS/DEV/dev_senat_digit_api/bash/seeds/run.seed-all.sh
```

**Make executable:**
```bash
chmod +x /var/www/APPS/DEV/dev_senat_digit_api/bash/seeds/run.seed-all.sh
```

### Seed script fails

**Check logs:**
```bash
tail -f bash/seeds/seedall_*.log
```

**Run manually to debug:**
```bash
cd /var/www/APPS/DEV/dev_senat_digit_api/bash/seeds
./run.seed-all.sh dev
```

## 🔐 Security

- Seed script runs as `senat_digit_admin` user
- Has access to database credentials via environment variables
- Logs are stored in project directory (not /var/log)
- Background process is detached from webhook

---

**Note:** Deployment will succeed even if seeding fails. Check logs to verify seed status.

