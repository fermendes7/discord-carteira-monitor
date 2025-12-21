FROM python:3.11-slim

WORKDIR /app

# Copia e instala dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o codigo
COPY monitor.py .

# Comando de execucao
CMD ["python", "-u", "monitor.py"]
