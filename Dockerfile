# Multi-stage build para reducir tamaño
FROM python:3.12-slim as builder

WORKDIR /app

# Instalar solo dependencias de compilación necesarias
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage final: imagen mínima
FROM python:3.12-slim

WORKDIR /app

# Instalar solo runtime dependencies (sin compiladores)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copiar dependencias instaladas desde builder
COPY --from=builder /root/.local /root/.local

# Asegurar que Python use las dependencias instaladas
ENV PATH=/root/.local/bin:$PATH

# Copiar solo código de la aplicación (excluye archivos grandes por .dockerignore)
COPY docchat/ ./docchat/
COPY app.py .
COPY requirements.txt .

# Crear directorios necesarios
RUN mkdir -p data documents .docchat_cache .docchat_vectordb .docchat_memory .docchat_audit

# Exponer puerto
EXPOSE 7860

# Ejecutar aplicación
CMD ["python", "app.py"]



