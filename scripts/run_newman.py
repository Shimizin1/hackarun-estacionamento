"""
Roda a coleção Postman com o Newman contra uma API local com banco NOVO e temporário
(não toca em data/). Requer Node.js (usa `npx`, nada é adicionado ao projeto).

Uso: python scripts/run_newman.py [porta]
"""
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PORTA = sys.argv[1] if len(sys.argv) > 1 else "8000"
BASE = f"http://localhost:{PORTA}"


def main() -> int:
    tmp = Path(tempfile.mkdtemp(prefix="capim_newman_"))
    env = dict(os.environ, CAPIM_DB_URL=f"sqlite:///{(tmp / 'newman.db').as_posix()}")
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", PORTA],
        cwd=RAIZ, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(40):
            try:
                urllib.request.urlopen(f"{BASE}/health", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            print("API não subiu a tempo.")
            return 2
        npx = shutil.which("npx") or "npx"
        return subprocess.call(
            [npx, "-y", "newman", "run",
             "postman/hackarun-estacionamento.postman_collection.json",
             "-e", "postman/local.postman_environment.json",
             "--env-var", f"baseUrl={BASE}"],
            cwd=RAIZ,
        )
    finally:
        api.terminate()
        api.wait(timeout=10)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
