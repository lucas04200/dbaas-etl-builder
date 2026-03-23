#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "  ██████╗  █████╗ ████████╗ █████╗ ███████╗ ██████╗ ██████╗  ██████╗ ███████╗"
echo "  ██╔══██╗██╔══██╗╚══██╔══╝██╔══██╗██╔════╝██╔═══██╗██╔══██╗██╔════╝ ██╔════╝"
echo "  ██║  ██║███████║   ██║   ███████║█████╗  ██║   ██║██████╔╝██║  ███╗█████╗  "
echo "  ██║  ██║██╔══██║   ██║   ██╔══██║██╔══╝  ██║   ██║██╔══██╗██║   ██║██╔══╝  "
echo "  ██████╔╝██║  ██║   ██║   ██║  ██║██║     ╚██████╔╝██║  ██║╚██████╔╝███████╗"
echo "  ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝ ╚══════╝"
echo ""

# ── 0. Environment secrets ───────────────────────────────────────────────────
# Load .env file if it exists (persists secrets across restarts)
ENV_FILE="$SCRIPT_DIR/.env"
if [ -f "$ENV_FILE" ]; then
    set -a
    source "$ENV_FILE"
    set +a
fi

# Database password for the internal DataForge database
export DATAFORGE_DB_PASS="${DATAFORGE_DB_PASS:-DataForge_Internal_2024!}"

# Master encryption key for service credentials at rest
if [ -z "$DATAFORGE_MASTER_KEY" ]; then
    echo "==> Premiere execution : generation de la MASTER_KEY..."
    export DATAFORGE_MASTER_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || echo "")
    if [ -z "$DATAFORGE_MASTER_KEY" ]; then
        pip install -q cryptography 2>/dev/null
        export DATAFORGE_MASTER_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
    fi
    # Persist to .env so the key survives restarts
    echo "DATAFORGE_MASTER_KEY='$DATAFORGE_MASTER_KEY'" >> "$ENV_FILE"
    echo "  MASTER_KEY generee et sauvegardee dans .env"
    echo ""
fi

# ── 1. Deploy internal database via Ansible ───────────────────────────────────
echo "==> [1/4] Deploiement de la base de donnees interne (Ansible)..."
cd "$SCRIPT_DIR/ansible"
ansible-playbook deploy_dataforge_db.yml
cd "$SCRIPT_DIR"

# ── 2. Wait for PostgreSQL to accept connections ───────────────────────────────
echo "==> [2/4] Attente du demarrage de PostgreSQL..."
MAX_RETRIES=20
COUNT=0
until docker exec dataforge_internal_db pg_isready -U dataforge -d dataforge -q 2>/dev/null; do
    COUNT=$((COUNT + 1))
    if [ "$COUNT" -ge "$MAX_RETRIES" ]; then
        echo "x PostgreSQL n'a pas demarre dans les temps. Verifiez le conteneur :"
        echo "    docker logs dataforge_internal_db"
        exit 1
    fi
    echo "  Tentative $COUNT/$MAX_RETRIES..."
    sleep 2
done
echo "v PostgreSQL pret"

# ── 3. Build frontend ─────────────────────────────────────────────────────────
echo "==> [3/4] Build du frontend Vue..."
cd "$SCRIPT_DIR/web/frontend"
npm install -q
npm run build
cd "$SCRIPT_DIR"

# ── 4. Install Python deps & start web server ─────────────────────────────────
echo "==> [4/4] Demarrage du serveur web DataForge..."
pip install -r "$SCRIPT_DIR/web/requirements.txt" -q

echo ""
echo "  -> Interface disponible sur : http://localhost:8080"
echo ""

cd "$SCRIPT_DIR/web"
python main.py
