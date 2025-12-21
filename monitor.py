import requests
import time
import json
import re
import os
from datetime import datetime
import base64
from io import BytesIO

try:
    from PIL import Image
    import pytesseract
    TESSERACT_AVAILABLE = True
except ImportError:
    TESSERACT_AVAILABLE = False

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
        
    def take_screenshot_puppeteer(self):
        """Usa Puppeteer via endpoint /screenshot com goto e evaluate"""
        try:
            if not DISCORD_TOKEN:
                print("ERRO: DISCORD_TOKEN nao configurado!")
                return None
            
            discord_url = "https://discord.com/channels/{}/{}".format(SERVER_ID, CHANNEL_ID)
            
            print("Capturando com Puppeteer via /screenshot...")
            
            endpoint = BROWSERLESS_URL + "/screenshot"
            
            # Payload com gotoOptions e addScriptTag
            payload = {
                "url": "https://discord.com/login",
                "gotoOptions": {
                    "waitUntil": "networkidle0",
                    "timeout": 30000
                },
                "options": {
                    "type": "png",
                    "fullPage": False
                },
                "waitFor": 3000
            }
            
            print("Etapa 1: Indo para login do Discord...")
            print("Endpoint: " + endpoint)
            
            # Primeira requisicao: vai para login
            response = requests.post(endpoint, json=payload, timeout=60)
            print("Status: " + str(response.status_code))
            
            if response.status_code != 200:
                print("Erro: " + response.text[:300])
                return None
            
            # Como nao conseguimos injetar token facilmente,
            # vamos tentar acessar o canal diretamente
            # (Discord pode ter cookies/sessao)
            
            print("\nEtapa 2: Tentando acessar canal diretamente...")
            
            payload2 = {
                "url": discord_url,
                "gotoOptions": {
                    "waitUntil": "networkidle0",
                    "timeout": 30000
                },
                "options": {
                    "type": "png",
                    "fullPage": False
                },
                "waitFor": 8000
            }
            
            response2 = requests.post(endpoint, json=payload2, timeout=60)
            print("Status: " + str(response2.status_code))
            
            if response2.status_code == 200:
                screenshot_bytes = response2.content
                
                # Salva para debug
                try:
                    with open('/tmp/screenshot_direct.png', 'wb') as f:
                        f.write(screenshot_bytes)
                    print("Screenshot salvo: /tmp/screenshot_direct.png")
                except:
                    pass
                
                return {
                    'screenshot_bytes': screenshot_bytes,
                    'screenshot_b64': base64.b64encode(screenshot_bytes).decode('utf-8'),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                print("Erro: " + response2.text[:300])
            
            return None
            
        except Exception as e:
            print("Erro: " + str(e))
            print("Tipo: " + type(e).__name__)
            return None
    
    def ocr_local(self, image_bytes):
        try:
            if not TESSERACT_AVAILABLE:
                return None
                
            print("\nTesseract OCR...")
            image = Image.open(BytesIO(image_bytes))
            
            # Melhora a imagem antes do OCR
            # Converte para escala de cinza e aumenta contraste
            from PIL import ImageEnhance
            image = image.convert('L')
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            text = pytesseract.image_to_string(image, config='--psm 6')
            
            print("="*60)
            print("TEXTO EXTRAIDO:")
            print("="*60)
            print(text if text else "[VAZIO]")
            print("="*60)
            
            return text
            
        except Exception as e:
            print("Tesseract erro: " + str(e))
            return None
    
    def extract_values_from_text(self, text):
        try:
            if not text or len(text.strip()) < 5:
                print("Texto vazio")
                return None
            
            print("\nBuscando padroes...")
            
            # Padroes muito flexiveis
            all_numbers = re.findall(r'[0-9,.]+', text)
            print("Numeros encontrados: " + str(all_numbers[:10]))
            
            # Tenta padroes especificos
            patterns = [
                (r'size[\s:]*([0-9,.]+)', r'balance[\s:]*([0-9,.]+)'),
                (r'Size[\s:]*([0-9,.]+)', r'Balance[\s:]*([0-9,.]+)'),
                (r'SIZE[\s:]*([0-9,.]+)', r'BALANCE[\s:]*([0-9,.]+)'),
            ]
            
            for size_pat, balance_pat in patterns:
                size_m = re.search(size_pat, text, re.IGNORECASE)
                balance_m = re.search(balance_pat, text, re.IGNORECASE)
                
                if size_m and balance_m:
                    size = float(size_m.group(1).replace(',', ''))
                    balance = float(balance_m.group(1).replace(',', ''))
                    
                    print("ACHEI! Size: {}, Balance: {}".format(size, balance))
                    return {'size': size, 'balance': balance}
            
            print("Padroes nao encontrados")
                
        except Exception as e:
            print("Erro extract: " + str(e))
            
        return None
    
    def send_to_n8n(self, data):
        if not N8N_WEBHOOK_URL:
            return False
            
        try:
            payload = {
                'timestamp': data['timestamp'],
                'size': data['size'],
                'balance': data['balance']
            }
            
            response = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=10)
            response.raise_for_status()
            
            print("Enviado para n8n!")
            return True
        except Exception as e:
            print("Erro n8n: " + str(e))
            return False
    
    def check_carteira(self):
        print("\n" + "="*60)
        print("[CHECK] " + datetime.now().strftime("%H:%M:%S"))
        print("="*60)
        
        result = self.take_screenshot_puppeteer()
        
        if not result:
            print("Falha ao capturar")
            return
        
        image_bytes = result.get('screenshot_bytes')
        
        if not image_bytes or len(image_bytes) < 100:
            print("Screenshot vazio ou muito pequeno")
            return
        
        print("Screenshot OK ({} bytes)".format(len(image_bytes)))
        
        # Tenta OCR
        ocr_text = self.ocr_local(image_bytes)
        
        if not ocr_text:
            print("OCR falhou")
            return
        
        values = self.extract_values_from_text(ocr_text)
        
        if not values:
            print("\nSize/Balance NAO encontrados")
            return
        
        # Detecta mudancas
        size_changed = (self.last_size != values['size'])
        balance_changed = (self.last_balance != values['balance'])
        
        if size_changed or balance_changed:
            print("\n*** MUDANCA ***")
            print("Size: {} -> {}".format(self.last_size, values['size']))
            print("Balance: {} -> {}".format(self.last_balance, values['balance']))
            
            data = {
                'timestamp': result.get('timestamp'),
                'size': values['size'],
                'balance': values['balance']
            }
            
            if self.send_to_n8n(data):
                self.last_size = values['size']
                self.last_balance = values['balance']
        else:
            print("\nSem mudancas (Size: {}, Balance: {})".format(values['size'], values['balance']))
    
    def run(self):
        print("="*60)
        print("Discord Monitor - Puppeteer + Tesseract")
        print("Intervalo: {}s".format(CHECK_INTERVAL))
        print("="*60)
        
        while True:
            try:
                self.check_carteira()
                print("\nAguardando {}s...\n".format(CHECK_INTERVAL))
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                print("Encerrado")
                break
            except Exception as e:
                print("ERRO: " + str(e))
                time.sleep(60)

if __name__ == "__main__":
    monitor = DiscordStageMonitor()
    monitor.run()
