import os
import sys
import shutil
import argparse
import subprocess

def deploy_etl(instance_name, host_port, target_db, db_name, db_user, db_password):
    if os.name == 'nt' and shutil.which('ansible-playbook') is None:
        pass
        
    if os.name == 'nt' or sys.platform == 'win32':
        print("\n❌ ERREUR MOTEUR : Ansible ne fonctionne pas nativement sous l'environnement Windows !")
        print("💡 Explication : Lance cette commande depuis ton terminal WSL/Ubuntu.")
        sys.exit(1)

    print(f"\n--- 🚀 Déploiement ETL (n8n) ---")
    print(f"📦 Instance n8n : n8n_{instance_name}")
    print(f"🔌 Port hôte    : {host_port}")
    print(f"🔗 Base cible   : {target_db} ({db_name})\n")
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    inventory = os.path.join(base_dir, "ansible", "inventory.ini")
    playbook = os.path.join(base_dir, "ansible", "deploy_n8n.yml")
    
    ansible_cmd = [
        "ansible-playbook",
        "-i", inventory,
        playbook,
        "--extra-vars",
        f"instance_name={instance_name} host_port={host_port} target_db_host={target_db} target_db_name={db_name} target_db_user={db_user} target_db_password={db_password}"
    ]
    
    try:
        print(f"⏳ Exécution de la commande Ansible : {' '.join(ansible_cmd)}\n")
        
        process = subprocess.Popen(
            ansible_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        stdout = process.stdout
        if stdout is not None:
            for line in stdout:
                print(line, end='')
            
        process.wait()
        
        if process.returncode == 0:
            print(f"\n✅ Succès ! L'instance ETL '{instance_name}' a été déployée avec succès.")
            print(f"   ► Studio n8n       : http://localhost:{host_port}")
            print(f"   ► Docker Container : n8n_{instance_name}")
            print(f"   ► Connecté à la DB : {target_db} sur le réseau privé Docker")
        else:
            print(f"\n❌ Le déploiement a échoué. Code d'erreur : {process.returncode}")
            sys.exit(process.returncode)
            
    except FileNotFoundError:
        print("\n❌ Erreur : La commande 'ansible-playbook' est introuvable sur ta machine.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Créer une instance n8n à la volée branchée sur DBaaS")
    parser.add_argument("--name", required=True, help="ID unique de l'instance ETL (ex: etl_paca)")
    parser.add_argument("--port", required=True, help="Port exposé pour ouvrir l'interface n8n (ex: 5678)")
    parser.add_argument("--target-db", required=True, dest="target_db", help="Nom du conteneur DB cible (ex: pg_paca)")
    parser.add_argument("--dbname", required=True, help="Nom de la base de données")
    parser.add_argument("--user", required=True, help="Nom d'utilisateur de la DB cible")
    parser.add_argument("--password", required=True, help="Mot de passe de la DB cible")
    
    args = parser.parse_args()
    
    deploy_etl(args.name, args.port, args.target_db, args.dbname, args.user, args.password)
