FROM python:3.11-slim

WORKDIR /app

# Instala Tesseract OCR e dependencias
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o codigo
COPY monitor.py .

# Comando de execucao
CMD ["python", "-u", "monitor.py"]
