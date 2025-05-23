import requests
import os


# Token del entorno seguro (secrets)
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


for run in data.get("workflow_runs", []):
    fecha_utc = run["created_at"]
    estado = run["conclusion"]
    link = run["html_url"]
    print(f"🕒 {fecha_utc} UTC | Estado: {estado} | 🔗 {link}")












