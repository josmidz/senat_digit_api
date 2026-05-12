#!/bin/bash

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Fonction pour afficher les messages
log() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

# Vérification des arguments
if [ $# -ne 1 ]; then
    error "Usage: $0 <environment> (dev|staging|prod)"
    exit 1
fi

ENV=$1
ENV_FILE=".env.$ENV"

# Vérification de l'existence du fichier d'environnement
if [ ! -f "$ENV_FILE" ]; then
    error "Le fichier d'environnement $ENV_FILE n'existe pas"
    exit 1
fi

# Chargement des variables d'environnement
log "Chargement des variables d'environnement depuis $ENV_FILE"
source "$ENV_FILE"

# Configuration dynamique de Redis
REDIS_PORT=${REDIS_PORT:-6379}
REDIS_HOST=${REDIS_HOST:-localhost}

# Configuration dynamique de Gunicorn
GUNICORN_PORT=${GUNICORN_PORT:-9282}
GUNICORN_WORKERS=${GUNICORN_WORKERS:-$(nproc)}

# Fonction pour démarrer Redis
start_redis() {
    log "Démarrage de Redis sur le port $REDIS_PORT"
    redis-server --port $REDIS_PORT --daemonize yes
}

# Fonction pour démarrer l'application
start_app() {
    log "Démarrage de l'application sur le port $GUNICORN_PORT avec $GUNICORN_WORKERS workers"
    gunicorn -b 0.0.0.0:$GUNICORN_PORT \
             -w $GUNICORN_WORKERS \
             --worker-class uvicorn.workers.UvicornWorker \
             --log-level info \
             --access-logfile - \
             --error-logfile - \
             --timeout 120 \
             app.main:app
}

# Fonction pour arrêter les services
stop_services() {
    log "Arrêt des services"
    pkill -f redis-server
    pkill -f gunicorn
}

# Gestion des signaux
trap stop_services SIGINT SIGTERM

# Démarrage des services
start_redis
