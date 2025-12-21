import requests
import time
import json
import re
import os
from datetime import datetime

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_ID = os.getenv("SERVER_ID", "971218268574584852")
CHANNEL_ID = os.getenv("CHANNEL_ID", "1435710395909410878")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")
BROWSERLESS_URL = os.getenv("BROWSERLESS_URL", "http://browserless:3000")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))

class DiscordStageMonitor:
    def __init__(self):
        self.last_size = None
        self.last_balance = None
        
    def take_screenshot(self):
        try:
            if not DISCORD_TOKEN:
                print("ERRO: DISCORD_TOKEN nao configurado!")
                return None
            
            discord_url = "https://discord.com/channels/{}/{}".format(SERVER_ID, CHANNEL_ID)
            
            print("URL Browserless: " + BROWSERLESS_URL)
            print("Discord Token: " + (DISCORD_TOKEN[:20] + "..." if DISCORD_TOKEN else "NAO CONFIGURADO"))
            print("Canal URL: " + discord_url)
            
            # Script sem module.exports (formato correto)
            script = """
async ({ page }) => {
  await page.goto('https://discord.com/login');
  await page.evaluate((token) => {
    setInterval(() => {
      const iframe = document.createElement('iframe');
      document.body.appendChild(iframe);
      iframe.contentWindow.localStorage.token = `"${token}"`;
    }, 50);
    setTimeout(() => { location.reload(); }, 2500);
  }, '""" + DISCORD_TOKEN + """');
  await page.waitForTimeout(5000);
  await page.goto('""" + discord_url + """');
  await page.waitForTimeout(8000);
  const screenshot = await page.screenshot({
    encoding: 'base64',
    fullPage: false
  });
  const pageText = await page.evaluate(() => {
    return document.body.innerText;
  });
  return {
    screenshot: screenshot,
    pageText: pageText,
    timestamp: new Date().toISOString()
  };
}
"""
            
            print("Enviando requisicao para Browserless...")
            endpoint = BROWSERLESS_URL + "/function"
            
            print("Endpoint: " + endpoint)
            
            response = requests.post(
                endpoint,
                json={"code": script},
                timeout=60
            )
            
            print("Status da resposta: " + str(response.status_code))
            
            if response.status_code != 200:
                print("Resposta de erro: " + response.text[:200])
            
            response.raise_for_status()
            
            result = response.json()
            print("Screenshot capturado com sucesso!")
            return result
            
        except requests.exceptions.ConnectionError as e:
            print("ERRO DE CONEXAO: Browserless nao acessivel")
            print("  Detalhes: " + str(e))
            return None
        except requests.exceptions.Timeout:
            print("ERRO: Timeout ao conectar no Browserless")
            return None
        except requests.exceptions.HTTPError as e:
            print("ERRO HTTP: " + str(e))
            if hasattr(e, 'response'):
                print("  Resposta: " + str(e.response.text[:200]))
            return None
        except Exception as e:
            print("Erro ao tirar screenshot: " + str(e))
            print("  Tipo: " + type(e).__name__)
            return None
    
    def extract_values_from_text(self, text):
        try:
            size_match = re.search(r'size[:\s]*([0-9,.]+)', text, re.IGNORECASE)
            balance_match = re.search(r'balance[:\s]*([0-9,.]+)', text, re.IGNORECASE)
            
            if size_match and balance_match:
                size = float(size_match.group(1).replace(',', ''))
                balance = float(balance_match.group(1).replace(',', ''))
                return {'size': size, 'balance': balance}
        except:
            pass
        return None
    
    def send_to_n8n(self, data):
        if not N8N_WEBHOOK_URL:
            print("N8N_WEBHOOK_URL nao configurado - pulando envio")
            return False
            
        try:
            payload = {
                'timestamp': data['timestamp'],
                'size': data['size'],
                'balance': data['balance']
            }
            
            response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
            
            msg = "Enviado para n8n: Size={}, Balance={}".format(data['size'], data['balance'])
            print(msg)
            return True
        except Exception as e:
            print("Erro ao enviar: " + str(e))
            return False
    
    def check_carteira(self):
        print("Capturando tela do Discord...")
        
        result = self.take_screenshot()
        if not result:
            print("Falha ao capturar tela")
            return
        
        screenshot_b64 = result.get('screenshot')
        page_text = result.get('pageText', '')
        
        print("\n=== TEXTO EXTRAIDO DA PAGINA ===")
        print(page_text[:500])
        print("=== FIM DO TEXTO ===\n")
        
        values = self.extract_values_from_text(page_text)
        
        if not values:
            print("Size e Balance nao encontrados no texto")
            return
        
        size_changed = (self.last_size != values['size'])
        balance_changed = (self.last_balance != values['balance'])
        
        if size_changed or balance_changed:
            print("MUDANCA DETECTADA!")
            msg1 = "  Size: {} -> {}".format(self.last_size, values['size'])
            msg2 = "  Balance: {} -> {}".format(self.last_balance, values['balance'])
            print(msg1)
            print(msg2)
            
            data = {
                'timestamp': result.get('timestamp'),
                'size': values['size'],
                'balance': values['balance']
            }
            
            if self.send_to_n8n(data):
                self.last_size = values['size']
                self.last_balance = values['balance']
        else:
            msg = "Sem mudancas (Size: {}, Balance: {})".format(values['size'], values['balance'])
            print(msg)
    
    def run(self):
        separator = "=" * 60
        
        print(separator)
        print("Discord Stage Monitor iniciado!")
        print("Canal: " + CHANNEL_ID)
        msg = "Intervalo: {} segundos".format(CHECK_INTERVAL)
        print(msg)
        print(separator)
        
        while True:
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                msg = "[{}] Verificando carteira...".format(timestamp)
                print(msg)
                
                self.check_carteira()
                
                msg = "Aguardando {} segundos...".format(CHECK_INTERVAL)
                print(msg)
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                print("Monitor encerrado")
                break
            except Exception as e:
                print("Erro: " + str(e))
                print("Tipo: " + type(e).__name__)
                time.sleep(60)

if __name__ == "__main__":
    monitor = DiscordStageMonitor()
    monitor.run()
