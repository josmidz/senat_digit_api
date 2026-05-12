# app/api/webhook.py
from datetime import datetime
import json
from fastapi import APIRouter, Request, Header, HTTPException
import hmac, hashlib, subprocess, os
from app.modules.core.configs.config import settings


router = APIRouter()


# SECRET = os.environ.get(settings.GITHUB_WEBHOOK_SECRET, settings.GITHUB_SHARED_SECRET)
@router.post("/webhook/deploy")
async def webhook_deploy(
    request: Request,
    x_hub_signature_256: str = Header(None),
    x_github_event: str = Header(None)
):
    # 1. SECURITY: Verify required headers exist
    if not x_hub_signature_256:
        raise HTTPException(status_code=403, detail="Missing signature header")
    
    # 2. Get raw body for signature verification
    try:
        body = await request.body()
        body_str = body.decode('utf-8')
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Body parsing failed: {str(e)}")

    # 3. Verify HMAC signature
    secret = settings.GITHUB_WEBHOOK_SECRET.encode()
    expected_signature = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    
    if not hmac.compare_digest(expected_signature, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # 4. Parse payload
    try:
        payload = await request.json()
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # 5. Determine event type
    if x_github_event == "ping":
        return {"message": "Webhook test successful"}
    
    if x_github_event not in ["push", "pull_request"]:
        raise HTTPException(status_code=400, detail="Unsupported event type")

    # 6. Process deployment
    ref = payload.get("ref", "")
    if not ref:
        raise HTTPException(status_code=400, detail="Missing ref in payload")

    branch = None
    if ref.startswith("refs/heads/"):
        branch = ref.split("/")[-1]
    elif ref.startswith("refs/tags/"):
        # Handle tag releases if needed
        return {"message": "Tag release detected (no deployment)"}

    # 7. Validate and trigger deployment
    if branch in ["dev", "main", "prod"]:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        log_file = f"/var/log/deploy_{branch}_{timestamp}.log"

        try:
            # Map GitHub branch to deployment environment
            # GitHub: "main" → Script: "prod"
            # GitHub: "dev" → Script: "dev"
            if branch == "dev":
                deploy_script = "/var/www/APPS/DEV/dev_senat_digit_api/bash/supervisor/rerun.sh"
                seed_script = "/var/www/APPS/DEV/dev_senat_digit_api/bash/seeds/run.seed-all.sh"
                seed_dir = "/var/www/APPS/DEV/dev_senat_digit_api/bash/seeds"
                script_arg = "dev"
            elif branch in ["main", "prod"]:
                deploy_script = "/var/www/APPS/PROD/prod_senat_digit_api/bash/supervisor/rerun.sh"
                seed_script = "/var/www/APPS/PROD/prod_senat_digit_api/bash/seeds/run.seed-all.sh"
                seed_dir = "/var/www/APPS/PROD/prod_senat_digit_api/bash/seeds"
                script_arg = "prod"
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported branch: {branch}")

            if not os.path.exists(deploy_script):
                raise HTTPException(status_code=500, detail=f"Deployment script missing: {deploy_script}")

            # Run deployment script
            # Webhook runs as senat_digit_admin (supervisor service owner)
            # Script will use sudo for supervisorctl commands (passwordless via sudoers)
            with open(log_file, "a") as log:
                deploy_process = subprocess.Popen(
                    [deploy_script, script_arg],
                    stdout=log,
                    stderr=log,
                    env={
                        **os.environ,
                        "DEPLOY_BRANCH": branch,
                        "DEPLOY_ENV": script_arg,
                        "GIT_COMMIT": payload.get("after", "")[:8],
                    },
                    cwd=os.path.dirname(deploy_script)
                )

            # Run seed script in background (after deployment)
            seed_log_file = None
            seed_pid = None
            if os.path.exists(seed_script):
                seed_log_file = f"{seed_dir}/seedall_{timestamp}.log"
                try:
                    # Run seed script in background with nohup
                    with open(seed_log_file, "w") as seed_log:
                        seed_process = subprocess.Popen(
                            ["nohup", seed_script, script_arg],
                            stdout=seed_log,
                            stderr=subprocess.STDOUT,
                            cwd=seed_dir,
                            preexec_fn=os.setpgrp  # Detach from parent process group
                        )
                        seed_pid = seed_process.pid
                except Exception as seed_error:
                    # Don't fail deployment if seed fails
                    with open(log_file, "a") as log:
                        log.write(f"\n⚠️  Seed script failed: {str(seed_error)}\n")

            return {
                "message": f"Deployment triggered for {branch} → {script_arg}",
                "log_file": log_file,
                "deploy_pid": deploy_process.pid,
                "script": deploy_script,
                "environment": script_arg,
                "seed_log_file": seed_log_file,
                "seed_pid": seed_pid
            }

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Deployment failed: {str(e)}")

    return {"message": f"No deployment for branch: {branch}"}
# @router.post("/webhook/deploy")
# async def webhook_deploy(
#     request: Request,
#     x_hub_signature_256: str = Header(None)
# ):
#     # print(f"\n\n\n x_hub_signature_256 : {x_hub_signature_256}\n\n\n")
#     body = await request.body()
#     expected_signature = "sha256=" + hmac.new(
#         settings.GITHUB_WEBHOOK_SECRET.encode(), body, hashlib.sha256
#     ).hexdigest()

#     # print(f"\n\n\n expected_signature : {expected_signature}\n\n\n")
#     # print(f"\n\n\n x_hub_signature_256 : {x_hub_signature_256}\n\n\n")

#     if not hmac.compare_digest(expected_signature, x_hub_signature_256):
#         raise HTTPException(status_code=403, detail="Invalid signature")

#     payload = await request.json()
#     ref = payload.get("ref")  # like "refs/heads/dev" or "refs/heads/main"
#     branch = ref.split("/")[-1]

#     if branch in ["dev", "main"]:
#         with open(f"/tmp/deploy_{branch}.log", "a") as log:
#             subprocess.Popen(
#                 ["/home/cobilgo_adm_vps025/BASH/FINANCE_SH/deploy.sh", branch],
#                 stdout=log,
#                 stderr=log
#             )
#         # subprocess.Popen(["/home/cobilgo_adm_vps025/BASH/FINANCE_SH/deploy.sh", branch])
#         return {"message": f"Deployment triggered for {branch}"}
    
#     return {"message": f"No deployment for {branch}"}
