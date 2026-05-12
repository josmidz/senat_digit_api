# Fix for "No module named 'app.modules.RLS'" Error

## Problem
The application was failing to start with the error:
```
❌ Critical import failed: No module named 'app.modules.RLS'
```

## Root Cause
The startup script `run.dev.sh` was running Python import tests without properly setting the `PYTHONPATH` environment variable. When Python tried to import modules, it couldn't find the `app.modules.RLS` module because the project root wasn't in the Python path.

## Solution
The `run.dev.sh` script has been updated to export `PYTHONPATH` at the beginning of the script (line 14):

```bash
# Export PYTHONPATH to ensure Python can find the app module
export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
```

This ensures that all Python commands in the script can properly resolve module imports from the project root.

## Deployment Instructions

### On the Server

1. **Navigate to the project directory:**
   ```bash
   cd /var/www/APPS/DEV/dev_senat_digit_api
   ```

2. **Pull the latest changes:**
   ```bash
   git pull origin dev
   ```

3. **Verify the fix is in place:**
   ```bash
   grep -n "export PYTHONPATH" bash/runner/run.dev.sh
   ```
   You should see:
   ```
   14:export PYTHONPATH="$PROJECT_ROOT:$PYTHONPATH"
   ```

4. **Restart the service:**
   ```bash
   sudo supervisorctl restart dev_senat_digit_api
   ```

5. **Check the status:**
   ```bash
   sudo supervisorctl status dev_senat_digit_api
   ```
   Should show: `RUNNING`

6. **Monitor the logs:**
   ```bash
   sudo tail -f /var/log/dev_senat_digit_api.out.log
   ```
   You should see:
   ```
   ✅ Core config import successful
   ✅ Database imports successful
   ✅ Logging middleware import successful
   🚀 Starting development server on port 4518...
   ```

## Verification

The service should now start successfully without the "No module named 'app.modules.RLS'" error.

If you still see issues, check:
1. The virtual environment is properly activated
2. All dependencies are installed
3. The `.env.development` file exists and is properly configured
4. MongoDB connection is available

## Alternative: Update Supervisor Configuration

If the issue persists, you can also update the supervisor configuration to include PYTHONPATH:

```bash
sudo nano /etc/supervisor/conf.d/dev_senat_digit_api.conf
```

Add `PYTHONPATH` to the environment section:
```ini
environment=
    ENV="development",
    APP_PORT="4518",
    LOG_LEVEL="info",
    PYTHONUNBUFFERED="1",
    PYTHONPATH="/var/www/APPS/DEV/dev_senat_digit_api",
    PATH="/var/www/APPS/DEV/dev_senat_digit_api/.venv/bin:%(ENV_PATH)s"
```

Then reload supervisor:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl restart dev_senat_digit_api
```

## Testing Locally

To test the fix locally:

```bash
cd /path/to/senat_digit_api
bash/runner/run.dev.sh
```

The script should complete all import tests successfully and start the server.

