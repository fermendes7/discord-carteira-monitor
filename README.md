# ?? Discord Carteira Monitor

Sistema de monitoramento automatizado 24/7 de carteira de trading no Discord com alertas via WhatsApp.

## ?? Funcionalidades

- ? **Captura automática** de tela do Discord (canal stage/palco)
- ? **Extração inteligente** de valores Size e Balance (regex + OCR fallback)
- ? **Detecção de mudanças** em tempo real
- ? **Alertas instantâneos** via webhook ? n8n ? WhatsApp
- ? **Deploy containerizado** no EasyPanel
- ? **Monitoramento 24/7** com intervalo configurável

## ??? Arquitetura

```
Discord Stage Channel
    ? (captura via Browserless)
Python Monitor (Docker)
    ? (webhook HTTP)
n8n Workflow
    +-? Google Sheets (histórico)
    +-? Evolution API ? WhatsApp
```

## ?? Deploy Rápido

### 1. Clone o Repositório
```bash
git clone https://github.com/fermendes7/discord-carteira-monitor.git
cd discord-carteira-monitor
```

### 2. Configure Variáveis de Ambiente

```env
DISCORD_TOKEN=seu_token_discord_aqui
SERVER_ID=971218268574584852
CHANNEL_ID=1435710395909410878
N8N_WEBHOOK_URL=https://seu-n8n.com/webhook/carteira
BROWSERLESS_URL=http://browserless:3000
CHECK_INTERVAL=300
```

### 3. Deploy no EasyPanel

1. Acesse **EasyPanel** ? Novo Serviço
2. Selecione **GitHub** como fonte
3. Configure:
   - Repositório: `fermendes7/discord-carteira-monitor`
   - Branch: `main`
   - Build: Dockerfile
4. Adicione as 6 variáveis de ambiente
5. Clique em **Implantar**

## ?? Estrutura do Projeto

```
discord-carteira-monitor/
+-- monitor.py           # Script principal Python
+-- Dockerfile          # Configuração Docker
+-- requirements.txt    # Dependências Python
+-- .dockerignore      # Arquivos ignorados no build
+-- README.md          # Este arquivo
```

## ?? Funcionamento Técnico

### Fluxo de Execução

1. **Autenticação Discord**
   - Injeta token no localStorage via Puppeteer
   - Navega para canal específico

2. **Captura de Tela**
   - Screenshot via Browserless (headless Chrome)
   - Extrai texto da página (DOM)

3. **Extração de Dados**
   - **Método 1:** Regex no texto do DOM (rápido)
   - **Método 2:** OCR com OCR.space (fallback)
   - Busca padrões: `size: 123.45` e `balance: 678.90`

4. **Detecção de Mudanças**
   - Compara com valores anteriores
   - Trigger apenas se houver diferença

5. **Envio de Alerta**
   - POST para webhook n8n
   - Payload JSON: `{timestamp, size, balance}`

### Exemplo de Saída

```
============================================================
Discord Stage Monitor iniciado!
Canal: 1435710395909410878
Intervalo: 300 segundos
============================================================
[2025-12-21 15:45:00] Verificando carteira...
Capturando tela do Discord...
MUDANCA DETECTADA!
  Size: 100.0 -> 150.5
  Balance: 5000.0 -> 5250.75
Enviado para n8n: Size=150.5, Balance=5250.75
Aguardando 300 segundos...
```

## ??? Tecnologias

- **Python 3.11** - Linguagem principal
- **Browserless** - Automação de navegador (Puppeteer/Chrome headless)
- **Docker** - Containerização
- **EasyPanel** - Plataforma de deploy
- **n8n** - Workflow automation
- **OCR.space** - Reconhecimento óptico de caracteres (fallback)

## ?? Integrações Futuras

- [ ] Google Sheets - Armazenamento de histórico
- [ ] Evolution API - Envio para WhatsApp
- [ ] Grafana - Dashboard de métricas
- [ ] Alertas de erro via Telegram

## ?? Segurança

- ?? **Nunca commite** o `DISCORD_TOKEN` no código
- ? Use variáveis de ambiente para secrets
- ? Token tem acesso apenas ao servidor específico
- ? Screenshot não é armazenado, apenas processado

## ?? Troubleshooting

### Erro: "Connection refused to Browserless"
```bash
# Verificar se Browserless está rodando
docker ps | grep browserless

# Se não estiver, iniciar:
docker run -d -p 3000:3000 browserless/chrome:latest
```

### Erro: "Size e Balance não encontrados"
- Verificar se canal Discord está correto
- Verificar se texto "size" e "balance" aparecem na tela
- Habilitar OCR fallback (já configurado)

### Erro: "Falha ao enviar para n8n"
- Verificar URL do webhook
- Testar webhook manualmente: `curl -X POST [N8N_WEBHOOK_URL] -d '{}'`

## ?? Logs

Logs são exibidos em tempo real no EasyPanel:
- **INFO:** Operações normais
- **ERRO:** Falhas na captura/envio
- **MUDANÇA DETECTADA:** Quando valores mudam

## ?? Contribuindo

1. Fork o projeto
2. Crie uma branch: `git checkout -b feature/nova-funcionalidade`
3. Commit: `git commit -m 'Add: nova funcionalidade'`
4. Push: `git push origin feature/nova-funcionalidade`
5. Abra um Pull Request

## ?? Licença

MIT License - Use livremente!

## ?? Autor

**Fernando Mendes**
- GitHub: [@fermendes7](https://github.com/fermendes7)

---

? **Se este projeto foi útil, deixe uma estrela no GitHub!**
