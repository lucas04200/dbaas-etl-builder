import subprocess
import argparse
import sys
import os
import shutil

def deploy_database(instance_name, db_name, db_user, db_password, host_port):
    if os.name == 'nt' and shutil.which('ansible-playbook') is None:
        pass # We'll check the platform later, but catching windows native ansible failure is better
        
    if os.name == 'nt' or sys.platform == 'win32':
        print("\n❌ ERREUR MOTEUR : Ansible ne fonctionne pas nativement sous l'environnement Windows !")
        print("💡 Explication : L'erreur `AttributeError: module 'os' has no attribute 'get_blocking'` est due au fait qu'Ansible cherche des fonctionnalités propres à Linux.")
        print("\n👉 SOLUTIONS POUR TON ORCHESTRATEUR :")
        print("   1. Si tu as WSL (Ubuntu) installé : Relance cette commande depuis ton terminal WSL/Ubuntu.")
        print("   2. Si ton app doit tourner sous Windows : Ton script Python doit préfixer la commande par `wsl`.")
        sys.exit(1)

    print(f"\n--- 🚀 Déploiement DBaaS (PostgreSQL) ---")
    print(f"📦 Instance : {instance_name}")
    print(f"🗄️  Base     : {db_name}")
    print(f"👤 Utilisateur : {db_user}")
    print(f"🔌 Port hôte   : {host_port}\n")
    
    # Chemin vers le playbook (relatif au script)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    inventory = os.path.join(base_dir, "ansible", "inventory.ini")
    playbook = os.path.join(base_dir, "ansible", "deploy_postgres.yml")
    
    # Construction de la ligne de commande Ansible
    ansible_cmd = [
        "ansible-playbook",
        "-i", inventory,
        playbook,
        "--extra-vars",
        f"instance_name={instance_name} db_name={db_name} db_user={db_user} db_password={db_password} host_port={host_port}"
    ]
    
    try:
        print(f"⏳ Exécution de la commande : {' '.join(ansible_cmd)}\n")
        
        # Lancement du processus
        # Note: Sur Windows pur, ansible-playbook n'existe pas nativement, cela s'exécute typiquement dans WSL
        process = subprocess.Popen(
            ansible_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Affichage des logs Ansible en temps réel
        stdout = process.stdout
        if stdout is not None:
            for line in stdout:
                print(line, end='')
            
        process.wait()
        
        if process.returncode == 0:
            print(f"\n✅ Succès ! L'instance PostgreSQL '{instance_name}' a été instanciée avec succès.")
            print(f"   ► Docker Container : pg_{instance_name}")
            print(f"   ► Docker Volume    : pg_data_{instance_name}")
            print(f"   ► DBeaver URL      : localhost:{host_port}")
        else:
            print(f"\n❌ Le déploiement a échoué. Code d'erreur : {process.returncode}")
            sys.exit(process.returncode)
            
    except FileNotFoundError:
        print("\n❌ Erreur : La commande 'ansible-playbook' est introuvable sur ta machine.")
        print("💡 Astuce : Sur Windows, lance ce script dans WSL (Ubuntu) ou assure-toi qu'Ansible est dans ton PATH.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Créer une instance PostgreSQL à la volée (Pilotage Ansible)")
    parser.add_argument("--name", required=True, help="ID unique de l'instance (ex: client_a)")
    parser.add_argument("--dbname", required=True, help="Nom de la base de données")
    parser.add_argument("--user", required=True, help="Nom d'utilisateur administrateur (ex: admin)")
    parser.add_argument("--password", required=True, help="Mot de passe robuste")
    parser.add_argument("--port", required=True, help="Port exposé sur l'hôte (ex: 5432, 5433)")
    
    args = parser.parse_args()
    
    deploy_database(args.name, args.dbname, args.user, args.password, args.port)
