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

# ── 1. Deploy internal database via Ansible ───────────────────────────────────
echo "==> [1/3] Déploiement de la base de données interne (Ansible)…"
cd "$SCRIPT_DIR/ansible"
ansible-playbook deploy_dataforge_db.yml
cd "$SCRIPT_DIR"

# ── 2. Wait for PostgreSQL to accept connections ───────────────────────────────
echo "==> [2/3] Attente du démarrage de PostgreSQL…"
MAX_RETRIES=20
COUNT=0
until docker exec dataforge_internal_db pg_isready -U dataforge -d dataforge -q 2>/dev/null; do
    COUNT=$((COUNT + 1))
    if [ "$COUNT" -ge "$MAX_RETRIES" ]; then
        echo "✗ PostgreSQL n'a pas démarré dans les temps. Vérifiez le conteneur :"
        echo "    docker logs dataforge_internal_db"
        exit 1
    fi
    echo "  Tentative $COUNT/$MAX_RETRIES…"
    sleep 2
done
echo "✓ PostgreSQL prêt"

# ── 3. Build frontend ─────────────────────────────────────────────────────────
echo "==> [3/4] Build du frontend Vue…"
cd "$SCRIPT_DIR/web/frontend"
/usr/bin/npm install -q
/usr/bin/npm run build
cd "$SCRIPT_DIR"

# ── 4. Install Python deps & start web server ─────────────────────────────────
echo "==> [4/4] Démarrage du serveur web DataForge…"
pip install -r "$SCRIPT_DIR/web/requirements.txt" -q

echo ""
echo "  → Interface disponible sur : http://localhost:8080"
echo "  → Credentials par défaut   : admin / admin123"
echo ""

cd "$SCRIPT_DIR/web"
python main.py
