FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /srv

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY frontend ./frontend
COPY scripts ./scripts

# Usuário não-root; data/ guarda o banco SQLite (montar volume para persistir).
RUN useradd --create-home --uid 1000 capim \
    && mkdir -p /srv/data \
    && chown -R capim:capim /srv
USER capim

EXPOSE 8000

# 0.0.0.0 é necessário dentro do container (a porta é publicada pelo Docker).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
