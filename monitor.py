import requests
import time
import json
import re
import os
from datetime import datetime

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_ID = os.getenv("SERVER_ID", "971218268574584852")
CHANNEL_ID = os.getenv("CHANNEL_ID", "1435710395909410878")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL")
BROWSERLESS_URL = os.getenv("BROWSERLESS_URL", "http://browserless:3000")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))

class DiscordStageMonitor:
    def __init__(self):
        self.last_size = None
        self.last_balance = None
        
    def get_browser_script(self):
        return {
            "token": DISCORD_TOKEN,
            "url": "https://discord.com/channels/{}/{}".format(SERVER_ID, CHANNEL_ID)
        }
        
    def take_screenshot(self):
        try:
            params = self.get_browser_script()
            
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
            
            response = requests.post(
                BROWSERLESS_URL + "/function",
                json={"code": browser_script},
                timeout=60
            )
            
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print("Erro ao tirar screenshot: " + str(e))
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
    
    def ocr_screenshot(self, screenshot_base64):
        try:
            response = requests.post(
                'https://api.ocr.space/parse/image',
                data={
                    'base64Image': 'data:image/png;base64,' + screenshot_base64,
                    'language': 'eng',
                    'isOverlayRequired': False,
                    'OCREngine': 2
                },
                timeout=30
            )
            
            result = response.json()
            if result.get('ParsedResults'):
                text = result['ParsedResults'][0]['ParsedText']
                print("Texto OCR extraido com sucesso")
                return text
        except Exception as e:
            print("OCR falhou: " + str(e))
        return None
    
    def send_to_n8n(self, data):
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
        
        values = self.extract_values_from_text(page_text)
        
        if not values and screenshot_b64:
            print("Usando OCR para ler imagem...")
            ocr_text = self.ocr_screenshot(screenshot_b64)
            if ocr_text:
                values = self.extract_values_from_text(ocr_text)
        
        if not values:
            print("Size e Balance nao encontrados")
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
                time.sleep(60)

if __name__ == "__main__":
    monitor = DiscordStageMonitor()
    monitor.run()
