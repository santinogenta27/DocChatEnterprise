FROM python:3.12-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data documents .docchat_cache .docchat_vectordb .docchat_memory .docchat_audit

# Cloud Run usa PORT environment variable (normalmente 8080)
# La aplicación detecta PORT automáticamente en app.py
EXPOSE 8080

# Run application
CMD ["python", "app.py"]



