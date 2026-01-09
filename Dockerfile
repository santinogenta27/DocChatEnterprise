FROM python:3.12-slim  # 🔹 Cambiado a 3.12

WORKDIR /app

# Dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential gcc portaudio19-dev libasound2-dev curl \
    && rm -rf /var/lib/apt/lists/*

# Actualizar pip
RUN python -m pip install --upgrade pip

# Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY . .

# Crear directorios
RUN mkdir -p data documents .docchat_cache .docchat_vectordb .docchat_memory .docchat_audit

# Exponer puerto
EXPOSE 7860

# Ejecutar app
CMD ["python", "app.py"]
