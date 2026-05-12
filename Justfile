installation:
python3 -m venv .venv
python3 -m pip install --upgrade pip-tools
pip install --upgrade pip setuptools wheel

brew install libheif
brew install pango gdk-pixbuf libffi
brew install pkg-config

pip install --use-pep517 pyheif
pip install --upgrade -c requirements.txt 'uvicorn[standard]' websockets wsproto
pip install pip-tools
pip install gunicorn
pip-compile requirements.in
pip install -r requirements.txt

googletrans==4.0.2
httpx==0.21.0
httpcore==0.14.7
idna==3.3


requirements:
pip-compile --strip-extras requirements.in
pip install --use-pep517 -r requirements.txt
pip freeze > requirements.txt

# Exclude Editable Packages
pip install fastapi httpx pillow rembg
pip freeze | grep -v "^\-e" > requirements.txt

pip install onnxruntime
pip install onnxruntime-gpu


run:
uvicorn app:app --reload




# All-in-one fix (recommended)
./docker/docker-run.sh fix dev
# What it does:
# 1. Stops containers
# 2. Removes old containers/images
# 3. Rebuilds with fixes
# 4. Starts services
# 5. Tests API endpoints

# Other available commands
./docker/docker-run.sh fix prod     # For production
./docker/docker-run.sh fix local    # For local
./docker/docker-run.sh logs dev     # Check logs if needed
./docker/docker-run.sh status       # See container status

./docker/docker-run.sh seed dev

# Restart the app
./docker/docker-run.sh restart dev
# What it does:
# 1. Stops the services gracefully
# 2. Waits 2 seconds
# 3. Starts the services again



# Check if container is running
./docker/docker-run.sh status

# Check logs
./docker/docker-run.sh logs dev

# Open shell to debug manually
./docker/docker-run.sh shell dev
# Then inside container:
ls -la bash/seeds/
bash bash/seeds/run.seed-all.sh dev





# # Development Deployment
# ./docker/switch-env.sh development
# ./docker/docker-run.sh build dev
# ./docker/docker-run.sh up dev
# ./docker/docker-run.sh seed dev

# # Production Deployment
# ./docker/switch-env.sh production  
# ./docker/docker-run.sh build prod
# ./docker/docker-run.sh up prod
# ./docker/docker-run.sh seed prod


🌐 Access Points for SenatDigit APIs
🔧 SenatDigit Apps API
    # Local: http://localhost:5516
    # Health: http://localhost:5516/health
    # Docs: http://localhost:5516/docs
    # Admin: http://localhost:5516/admin


    # Development: http://localhost:5518
    # Health: http://localhost:5518/health
    # Docs: http://localhost:5518/docs
    # Admin: http://localhost:5518/admin


    # Production: http://localhost:5518 (same as dev)
    # Health: http://localhost:5518/health
    # Docs: http://localhost:5518/docs
    # Admin: http://localhost:5518/admin 


# 1. Check Container Status:
docker ps | grep senat_digit_api

# 2. Check Container Logs:
docker logs senat_digit_api_dev -f

docker logs senat_digit_api_dev --tail 20

# 3. Check if Container is Actually Running:
docker ps -a | grep senat_digit_api_dev
