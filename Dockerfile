FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie les dossiers frontend et backend
COPY ./frontend /app/frontend
COPY ./generateurbackend /app/generateurbackend

# La commande de démarrage
CMD ["uvicorn", "generateurbackend.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Exposer le port sur lequel l'application va tourner
EXPOSE 8000

