# Discord Stage Voice Monitor v8

Sistema automatizado para capturar tela compartilhada em Stage Voice Channel do Discord e enviar para n8n para processamento OCR.

## 🎯 Objetivo

Monitorar palco de voz "Clássica" no Discord que exibe uma carteira de trading 24/7, capturar screenshots a cada 5 minutos e extrair valores via OCR.

## 📋 Requisitos

- Docker
- Browserless (container)
- n8n (para processar screenshots)
- Token Discord válido

## 🚀 Deploy Rápido no EasyPanel

### Passo 1: Preparar Repositório GitHub

1. Fazer fork/clone deste repositório
2. Garantir que os arquivos estão presentes:
   - `monitor.py` ✅
   - `Dockerfile` ✅
   - `requirements.txt` ✅
   - `.gitignore` ✅

### Passo 2: Criar App no EasyPanel

1. EasyPanel → **New App** → **From GitHub**
2. Conectar repositório
3. Configurações:
   - **Name**: `discord-stage-monitor`
   - **Type**: `Docker`
   - **Dockerfile**: `Dockerfile`

### Passo 3: Configurar Environment Variables

No EasyPanel → App → **Environment**, adicionar:

```env
DISCORD_TOKEN=MTE3N........(seu token completo)
SERVER_ID=971218268574584852
CHANNEL_ID=1435710395909410878
N8N_WEBHOOK_URL=https://webhook.bola9.com.br/webhook/carteira-discord
BROWSERLESS_URL=http://browserless:3000
CHECK_INTERVAL=300
```

### Passo 4: Deploy

1. **Build** → Aguardar build completar
2. **Deploy** → Iniciar container
3. **Logs** → Verificar se está rodando

## 🔑 Como Obter Discord Token

1. Abrir Discord no navegador (não app desktop)
2. Login na sua conta
3. Abrir DevTools (F12)
4. Ir em **Network** tab
5. Recarregar página (F5)
6. Procurar requisição para `api/v9/users/@me` ou qualquer api/v9
7. Nos **Request Headers**, copiar o valor de `authorization`
8. Esse é seu token!

## 📊 Logs Esperados

Após deploy bem-sucedido, você verá:

```
======================================================================
🎭 DISCORD STAGE VOICE MONITOR v8
======================================================================
📍 Server: 971218268574584852
🎤 Stage Channel: 1435710395909410878 (Palco 'Clássica')
⏱️  Intervalo: 300s (5.0 min)
🔑 Token: ✅ Configurado
🌐 n8n: ✅ Configurado
======================================================================
🚀 Iniciando monitoramento...

🔄 Ciclo #1
🎭 Capturando Stage Voice Channel...
✅ Screenshot capturado! (245.3 KB)
📤 Enviando para n8n...
✅ Enviado com sucesso para n8n!
🎉 Ciclo completo com sucesso!
```

## 🐛 Troubleshooting

### Screenshot mostra tela de login
- ❌ Token inválido ou expirado
- ✅ Obter novo token
- ✅ Verificar DISCORD_TOKEN no Environment

### Timeout ao capturar
- ❌ Stream offline ou carregando devagar
- ✅ Verificar se stage está ativo
- ✅ Aumentar CHECK_INTERVAL

### Erro ao enviar para n8n
- ❌ N8N_WEBHOOK_URL incorreto
- ✅ Verificar URL do webhook
- ✅ Ativar workflow no n8n

### Container não inicia
- ❌ Erro no Dockerfile ou dependências
- ✅ Ver logs de build
- ✅ Verificar requirements.txt

## 📁 Estrutura de Arquivos

```
.
├── monitor.py              # Código principal (v8)
├── Dockerfile              # Container configuration
├── requirements.txt        # Python dependencies
├── .env.example           # Exemplo de variáveis
├── .gitignore             # Ignorar arquivos sensíveis
└── README.md              # Este arquivo
```

## 🔄 Fluxo de Funcionamento

1. **Monitor Python** captura screenshot do stage a cada 5 min
2. Converte para **base64**
3. Envia via **POST** para webhook n8n
4. **n8n** recebe e processa:
   - Node: Visualizar Imagem
   - Node: OCR (extrai texto)
   - Node: Extract Values (pega Size/Balance)
   - Node: Google Sheets (salva dados)
   - Node: WhatsApp (envia alertas)

## 🎯 Próximos Passos

Após deploy funcionando:

1. ✅ Verificar screenshot no n8n
2. ✅ Adicionar node "Visualizar Imagem"
3. ✅ Configurar OCR
4. ✅ Extrair valores (Size, Balance)
5. ✅ Integrar Google Sheets
6. ✅ Configurar WhatsApp

## 📝 Notas Importantes

- ⚠️ Token Discord **expira** - precisa renovar periodicamente
- ⚠️ Stage precisa estar **ativo** para capturar
- ⚠️ Stream demora ~10-20s para carregar
- ⚠️ Browserless precisa estar **rodando** no mesmo network

## 🆘 Suporte

Se encontrar problemas:

1. Verificar logs do container
2. Verificar environment variables
3. Testar token manualmente
4. Verificar se stage está ativo
5. Consultar arquivos de documentação na pasta

## 📜 Licença

Uso pessoal - Projeto de automação

## ✨ Versão

**v8** - Stage Voice Channel Optimized
- Data: 2025-12-23
- Otimizado para capturar tela compartilhada em Stage
