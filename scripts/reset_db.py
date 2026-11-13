"""Apaga o banco local (data/capimparking.db). Ele é recriado com o seed no próximo startup da API."""
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "capimparking.db"

removidos = 0
for sufixo in ("", "-journal", "-wal", "-shm"):
    arquivo = DB.with_name(DB.name + sufixo)
    if arquivo.exists():
        arquivo.unlink()
        removidos += 1

print(f"Banco removido ({removidos} arquivo(s)). Suba a API para recriar com o seed." if removidos
      else "Nenhum banco local encontrado; ele será criado no próximo startup.")
