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
BROWSERLESS_TOKEN = os.getenv("BROWSERLESS_TOKEN", "")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))

class DiscordStageMonitor:
    def __init__(self):
        self.last_size = None
        self.last_balance = None
        
    def test_browserless_connection(self):
        """Testa conexao com Browserless em diferentes formatos"""
        print("\n=== TESTE DE CONEXAO BROWSERLESS ===")
        
        if BROWSERLESS_TOKEN:
            print("Token Browserless: " + BROWSERLESS_TOKEN[:20] + "...")
        
        # Testa diferentes formatos de autenticacao
        test_configs = [
            {"url": BROWSERLESS_URL, "params": {"token": BROWSERLESS_TOKEN}},
            {"url": BROWSERLESS_URL + "?token=" + BROWSERLESS_TOKEN, "params": {}},
            {"url": BROWSERLESS_URL, "headers": {"Authorization": "Bearer " + BROWSERLESS_TOKEN}},
            {"url": BROWSERLESS_URL, "headers": {"X-API-KEY": BROWSERLESS_TOKEN}},
        ]
        
        for i, config in enumerate(test_configs):
            try:
                print("\nTentativa {}: {}".format(i+1, config["url"][:50]))
                response = requests.get(
                    config["url"],
                    params=config.get("params", {}),
                    headers=config.get("headers", {}),
                    timeout=5
                )
                print("  Status: {} - OK!".format(response.status_code))
                if response.status_code in [200, 404]:
                    return True
            except Exception as e:
                print("  Erro: {}".format(str(e)))
        
        print("FALHA: Nenhuma configuracao funcionou!")
        return False
        
    def get_browser_script(self):
        if not DISCORD_TOKEN:
            print("ERRO: DISCORD_TOKEN nao configurado!")
            return None
            
        return {
            "token": DISCORD_TOKEN,
            "url": "https://discord.com/channels/{}/{}".format(SERVER_ID, CHANNEL_ID)
        }
        
    def take_screenshot(self):
        try:
            params = self.get_browser_script()
            if not params:
                return None
            
            print("URL Browserless: " + BROWSERLESS_URL)
            print("Discord Token: " + (DISCORD_TOKEN[:20] + "..." if DISCORD_TOKEN else "NAO CONFIGURADO"))
            print("Canal URL: " + params["url"])
            
            script_parts = []
            script_parts.append("module.exports = async ({ page }) => {")
            script_parts.append("  await page.goto('https://discord.com/login');")
            script_parts.append("  await page.evaluate((token) => {")
            script_parts.append("    setInterval(() => {")
            script_parts.append("      const iframe = document.createElement('iframe');")
            script_parts.append("      document.body.appendChild(iframe);")
            script_parts.append('      iframe.contentWindow.localStorage.token = `"${token}"`;')
            script_parts.append("    }, 50);")
            script_parts.append("    setTimeout(() => { location.reload(); }, 2500);")
            script_parts.append("  }, '" + params["token"] + "');")
            script_parts.append("  await page.waitForTimeout(5000);")
            script_parts.append("  await page.goto('" + params["url"] + "');")
            script_parts.append("  await page.waitForTimeout(8000);")
            script_parts.append("  const screenshot = await page.screenshot({")
            script_parts.append("    encoding: 'base64',")
            script_parts.append("    fullPage: false")
            script_parts.append("  });")
            script_parts.append("  const pageText = await page.evaluate(() => {")
            script_parts.append("    return document.body.innerText;")
            script_parts.append("  });")
            script_parts.append("  return {")
            script_parts.append("    screenshot: screenshot,")
            script_parts.append("    pageText: pageText,")
            script_parts.append("    timestamp: new Date().toISOString()")
            script_parts.append("  };")
            script_parts.append("};")
            
            browser_script = "\n".join(script_parts)
            
            print("Enviando requisicao para Browserless...")
            
            # Tenta com token na query string
            if BROWSERLESS_TOKEN:
                endpoint = BROWSERLESS_URL + "/function?token=" + BROWSERLESS_TOKEN
            else:
                endpoint = BROWSERLESS_URL + "/function"
            
            print("Endpoint: " + endpoint[:80] + "...")
            
            response = requests.post(
                endpoint,
                json={"code": browser_script},
                timeout=60
            )
            
            print("Status da resposta: " + str(response.status_code))
            
            # Se der 401, tenta remover o token (sem autenticacao)
            if response.status_code == 401 and BROWSERLESS_TOKEN:
                print("401 com token - Tentando SEM autenticacao...")
                endpoint_no_auth = BROWSERLESS_URL + "/function"
                response = requests.post(
                    endpoint_no_auth,
                    json={"code": browser_script},
                    timeout=60
                )
                print("Status sem auth: " + str(response.status_code))
            
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
            print("  Resposta: " + str(e.response.text[:200]) if hasattr(e, 'response') else "")
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
        
        print("Texto extraido da pagina (primeiros 200 caracteres):")
        print(page_text[:200])
        
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
        print("Discord Stage Monitor iniciado! (MODO DEBUG v2)")
        print("Canal: " + CHANNEL_ID)
        msg = "Intervalo: {} segundos".format(CHECK_INTERVAL)
        print(msg)
        print(separator)
        
        # Teste inicial de conexao
        self.test_browserless_connection()
        
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
