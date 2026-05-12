#!/bin/bash
# restart_app.sh - Forcefully restarts minfinance_fs_api_dev and cleans port 7495

APP_NAME="minfinance_fs_api_dev"
APP_PORT=7495
LOG_DIR="/var/log"
SUPERVISOR_CMD="sudo supervisorctl"

# 1. Kill any processes on port 7495
echo "Killing processes on port $APP_PORT..."
sudo fuser -k $APP_PORT/tcp >/dev/null 2>&1
sudo pkill -f "uvicorn.*$APP_PORT" >/dev/null 2>&1

# 2. Stop through Supervisor (if running)
echo "Stopping Supervisor service..."
$SUPERVISOR_CMD stop $APP_NAME >/dev/null 2>&1

# 3. Kill any remaining Python processes
echo "Cleaning up Python processes..."
sudo pkill -f "python.*$APP_NAME" >/dev/null 2>&1

# 4. Wait for port to be free
echo "Waiting for port to be released..."
timeout 5 bash -c "while sudo lsof -i :$APP_PORT >/dev/null; do sleep 0.5; done"

# 5. Restart through Supervisor
echo "Restarting application..."
$SUPERVISOR_CMD start $APP_NAME

# 6. Verify status
sleep 2
$SUPERVISOR_CMD status $APP_NAME

# 7. Show recent logs
echo -e "\n=== Tail of log files ==="
tail -n 5 $LOG_DIR/dev_min_finance_fs_api.{out,err}.log