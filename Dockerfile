FROM python:3.12-slim

WORKDIR /app

# Dependencias del sistema necesarias para PDF, imágenes, etc. (sin PyAudio)
RUN apt-get update && apt-get install -y \
    build-essential \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Actualizar pip
RUN python -m pip install --upgrade pip

# Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Crear directorios necesarios
RUN mkdir -p data documents .docchat_cache .docchat_vectordb .docchat_memory .docchat_audit

# Exponer puerto
EXPOSE 7860

# Ejecutar app
CMD ["python", "app.py"]
