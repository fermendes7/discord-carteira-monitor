FROM python:3.9-slim

WORKDIR /app

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY monitor.py .

# Variáveis de ambiente (serão sobrescritas no EasyPanel)
ENV DISCORD_TOKEN=""
ENV SERVER_ID="971218268574584852"
ENV CHANNEL_ID="1435710395909410878"
ENV N8N_WEBHOOK_URL=""
ENV BROWSERLESS_URL="http://browserless:3000"
ENV CHECK_INTERVAL="300"

# Healthcheck
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
  CMD python -c "import sys; sys.exit(0)"

# Executar monitor
CMD ["python", "-u", "monitor.py"]
