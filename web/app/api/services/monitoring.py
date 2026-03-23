"""
DataForge - Monitoring Docker (Live Stats)
"""

import subprocess
import json
from fastapi import APIRouter, Depends
from app.api.deps import require_admin

router = APIRouter(prefix="/api/monitoring", tags=["monitoring"])

@router.get("")
def get_docker_stats(_: dict = Depends(require_admin)):
    """
    Exécute `docker stats` pour récupérer le CPU/RAM des conteneurs en live.
    Restreint aux administrateurs.
    """
    try:
        res = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}"], 
            capture_output=True, text=True, check=True
        )
        containers = []
        for line in res.stdout.strip().split('\n'):
            if not line:
                continue
            try:
                data = json.loads(line)
                # On nettoie un peu le nom s'il commence par /
                c_name = data.get("Name", "")
                if c_name.startswith("/"):
                    c_name = c_name[1:]
                    
                containers.append({
                    "id": data.get("ID"),
                    "name": c_name,
                    "cpu": data.get("CPUPerc", "0.00%"),
                    "mem": data.get("MemUsage", "0B / 0B"),
                    "mem_perc": data.get("MemPerc", "0.00%"),
                    "net": data.get("NetIO", "0B / 0B"),
                    "block": data.get("BlockIO", "0B / 0B")
                })
            except json.JSONDecodeError:
                pass
                
        return sorted(containers, key=lambda c: c["name"])
    except Exception as e:
        return {"error": str(e)}
