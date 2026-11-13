"""
Roda a coleção Postman com o Newman contra uma API local com banco NOVO e temporário
(não toca em data/). Requer Node.js (usa `npx`, nada é adicionado ao projeto).

Uso: python scripts/run_newman.py [porta]
"""
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PORTA = sys.argv[1] if len(sys.argv) > 1 else "8000"
BASE = f"http://127.0.0.1:{PORTA}"


def porta_ocupada() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(1)
        return s.connect_ex(("127.0.0.1", int(PORTA))) == 0


def main() -> int:
    if porta_ocupada():
        print(f"Porta {PORTA} já está em uso; pare a API que está nela ou passe outra porta "
              f"(python scripts/run_newman.py 8010). Abortando para não testar a API errada.")
        return 2
    tmp = Path(tempfile.mkdtemp(prefix="capim_newman_"))
    env = dict(os.environ, CAPIM_DB_URL=f"sqlite:///{(tmp / 'newman.db').as_posix()}")
    api = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", PORTA],
        cwd=RAIZ, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    try:
        for _ in range(40):
            if api.poll() is not None:
                print(f"O uvicorn encerrou (código {api.returncode}) antes de ficar pronto; "
                      f"verifique se a porta {PORTA} está livre. Abortando.")
                return 2
            try:
                urllib.request.urlopen(f"{BASE}/health", timeout=1)
                break
            except Exception:
                time.sleep(0.5)
        else:
            print("API não subiu a tempo.")
            return 2
        npx = shutil.which("npx") or "npx"
        cmd = [npx, "-y", "newman", "run",
               "postman/hackarun-estacionamento.postman_collection.json",
               "-e", "postman/local.postman_environment.json",
               "--env-var", f"baseUrl={BASE}"]
        # Opcional (usado no CI): NEWMAN_JSON=caminho gera também o relatório JSON.
        relatorio = os.environ.get("NEWMAN_JSON")
        if relatorio:
            cmd += ["--reporters", "cli,json", "--reporter-json-export", relatorio]
        return subprocess.call(cmd, cwd=RAIZ)
    finally:
        if api.poll() is None:
            api.terminate()
            api.wait(timeout=10)
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
