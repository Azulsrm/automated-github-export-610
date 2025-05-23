import requests
import os
from datetime import datetime, timedelta, timezone


# Token desde los secrets del workflow
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


OWNER = "Azulsrm"
REPO = "automated-github-export-610"
WORKFLOW_FILENAME = "exportar_excel.yml"


headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json"
}


url = f"https://api.github.com/repos/{OWNER}/{REPO}/actions/workflows/{WORKFLOW_FILENAME}/runs"
response = requests.get(url, headers=headers)
data = response.json()


print(f"\n📋 Historial del workflow '{WORKFLOW_FILENAME}':\n")


# Zona horaria CDMX (UTC-6 sin horario de verano)
cdmx_offset = timezone(timedelta(hours=-6))


for run in data.get("workflow_runs", []):
    fecha_utc_raw = run["created_at"]
    estado = run["conclusion"]
    link = run["html_url"]


    # Parsear hora UTC
    dt_utc = datetime.strptime(fecha_utc_raw, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    dt_cdmx = dt_utc.astimezone(cdmx_offset)


    print(f"Hora UTC:   {dt_utc.strftime('%a %b %d %H:%M:%S UTC %Y')}")
    print(f"Hora CDMX:  {dt_cdmx.strftime('%a %b %d %H:%M:%S CST %Y')}")
    print(f"🔗 {link} | Estado: {estado}\n")









