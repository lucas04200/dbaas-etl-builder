#!/bin/bash
# Script bash pour tester le déploiement d'une base DBaaS à chaud

echo "--- 🚀 Lancement test du playbook Ansible DBaaS ---"

# On passe des paramètres de test
INSTANCE="client_test"
DB_NAME="test_db"
DB_USER="admin_test"
DB_PASS="SecurePass123"

echo "Exécution pour l'instance: $INSTANCE"

# Assurez-vous d'être dans le dossier ansible ou de spécifier le chemin correct
ansible-playbook -i ansible/inventory.ini ansible/deploy_postgres.yml \
  --extra-vars "instance_name=$INSTANCE db_name=$DB_NAME db_user=$DB_USER db_password=$DB_PASS"

if [ $? -eq 0 ]; then
    echo "✅ Succès ! Tu peux vérifier en tapant: docker ps"
else
    echo "❌ Erreur de déploiement"
fi