#!/bin/bash

# Fonction pour créer un fichier d'environnement
create_env_file() {
    local env_file=$1
    local env_type=$2
    local port=$3
    local redis_port=$4

    cat > "$env_file" << EOF
# Ports d'application
${env_type^^}_PORT=${port}

# Ports Redis
REDIS_${env_type^^}_PORT=${redis_port}

# Configuration Redis
REDIS_HOST=redis-${env_type}
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=${env_type}_password

# Configuration de l'application
NODE_ENV=${env_type}
PORT=8000

# Autres variables d'environnement nécessaires
DATABASE_URL=postgresql://user:password@localhost:5432/${env_type}_db
SECRET_KEY=${env_type}_secret_key
EOF

    echo "✅ Fichier $env_file créé avec les paramètres par défaut"
}

# Fonction pour vérifier l'existence d'un fichier d'environnement
check_env_file() {
    local env_file=$1
    local env_type=$2
    local port=$3
    local redis_port=$4

    if [ ! -f "$env_file" ]; then
        echo "❌ Le fichier $env_file n'existe pas"
        read -p "Voulez-vous créer le fichier $env_file ? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            create_env_file "$env_file" "$env_type" "$port" "$redis_port"
        else
            echo "❌ Le fichier $env_file est requis pour continuer"
            exit 1
        fi
    else
        echo "✅ $env_file existe"
    fi
}

# Vérifier les fichiers d'environnement pour chaque service
echo "Vérification des fichiers d'environnement..."

# Vérifier les fichiers d'environnement de base avec leurs ports respectifs
check_env_file ".env.development" "development" "8001" "6389"
check_env_file ".env.production" "production" "8000" "6389"
check_env_file ".env.local" "local" "8002" "6389"
check_env_file ".env.stage" "stage" "8003" "6389"
check_env_file ".env.testing" "testing" "8004" "6389"

echo "✅ Tous les fichiers d'environnement sont présents"
echo "Vous pouvez maintenant lancer les conteneurs avec docker-compose"
echo ""
echo "Commandes disponibles :"
echo "docker-compose up app        # Pour l'environnement de développement"
echo "docker-compose up app-prod   # Pour l'environnement de production"
echo "docker-compose up app-local  # Pour l'environnement local"
echo "docker-compose up app-stage  # Pour l'environnement de staging"
