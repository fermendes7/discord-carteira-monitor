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
        
    def take_screenshot(self):
        try:
            if not DISCORD_TOKEN:
                print("ERRO: DISCORD_TOKEN nao configurado!")
                return None
            
            discord_url = "https://discord.com/channels/{}/{}".format(SERVER_ID, CHANNEL_ID)
            
            print("Capturando screenshot direto...")
            screenshot_endpoint = BROWSERLESS_URL + "/screenshot"
            screenshot_payload = {
                "url": discord_url,
                "options": {
                    "fullPage": False,
                    "type": "png"
                }
            }
            
            response = requests.post(
                screenshot_endpoint,
                json=screenshot_payload,
                timeout=60
            )
            
            print("Status: " + str(response.status_code))
            
            if response.status_code == 200:
                print("Screenshot OK!")
                
                # Salva screenshot para debug
                try:
                    with open('/tmp/screenshot_debug.png', 'wb') as f:
                        f.write(response.content)
                    print("Screenshot salvo em: /tmp/screenshot_debug.png")
                except:
                    pass
                
                return {
                    'screenshot_bytes': response.content,
                    'screenshot_b64': base64.b64encode(response.content).decode('utf-8'),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                print("Erro: " + str(response.status_code))
                return None
            
        except Exception as e:
            print("Erro: " + str(e))
            return None
    
    def ocr_local(self, image_bytes):
        try:
            if not TESSERACT_AVAILABLE:
                return None
                
            print("Tesseract OCR local...")
            image = Image.open(BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            
            print("\n" + "="*60)
            print("TEXTO TESSERACT COMPLETO:")
            print("="*60)
            print(text)
            print("="*60 + "\n")
            
            return text
            
        except Exception as e:
            print("Tesseract falhou: " + str(e))
            return None
    
    def ocr_external(self, screenshot_base64):
        try:
            print("OCR externo...")
            
            response = requests.post(
                'https://api.ocr.space/parse/image',
                data={
                    'base64Image': 'data:image/png;base64,' + screenshot_base64,
                    'language': 'eng',
                    'isOverlayRequired': 'false',
                    'OCREngine': '2',
                    'apikey': 'helloworld'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('ParsedResults') and len(result['ParsedResults']) > 0:
                    text = result['ParsedResults'][0].get('ParsedText', '')
                    
                    print("\n" + "="*60)
                    print("TEXTO OCR EXTERNO COMPLETO:")
                    print("="*60)
                    print(text)
                    print("="*60 + "\n")
                    
                    return text
                    
        except Exception as e:
            print("OCR externo falhou: " + str(e))
        
        return None
    
    def extract_values_from_text(self, text):
        try:
            if not text or len(text.strip()) == 0:
                print("Texto vazio!")
                return None
            
            print("Procurando padroes no texto...")
            
            # Padroes mais flexiveis
            patterns = [
                (r'(?:size|tamanho|SIZE)[\s:]*([0-9,.]+)', r'(?:balance|saldo|BALANCE)[\s:]*([0-9,.]+)'),
                (r'([0-9,.]+)[\s]*(?:size|SIZE)', r'([0-9,.]+)[\s]*(?:balance|BALANCE)'),
            ]
            
            for size_pattern, balance_pattern in patterns:
                size_match = re.search(size_pattern, text, re.IGNORECASE)
                balance_match = re.search(balance_pattern, text, re.IGNORECASE)
                
                if size_match and balance_match:
                    size_str = size_match.group(1)
                    balance_str = balance_match.group(1)
                    
                    size = float(size_str.replace(',', ''))
                    balance = float(balance_str.replace(',', ''))
                    
                    print("VALORES ENCONTRADOS! Size: {}, Balance: {}".format(size, balance))
                    return {'size': size, 'balance': balance}
            
            print("Padroes nao encontrados")
                
        except Exception as e:
            print("Erro ao extrair: " + str(e))
            
        return None
    
    def check_carteira(self):
        print("\n[VERIFICACAO] Capturando tela...")
        
        result = self.take_screenshot()
        if not result:
            return
        
        image_bytes = result.get('screenshot_bytes')
        image_b64 = result.get('screenshot_b64')
        
        # Tenta Tesseract local
        ocr_text = self.ocr_local(image_bytes)
        
        # Fallback para API externa
        if not ocr_text or len(ocr_text.strip()) < 10:
            print("Texto Tesseract vazio - tentando API externa...")
            ocr_text = self.ocr_external(image_b64)
        
        if not ocr_text or len(ocr_text.strip()) < 10:
            print("ERRO: Nenhum texto extraido!")
            return
        
        values = self.extract_values_from_text(ocr_text)
        
        if not values:
            print("Size/Balance nao encontrados")
            return
        
        # Logica de mudanca
        size_changed = (self.last_size != values['size'])
        balance_changed = (self.last_balance != values['balance'])
        
        if size_changed or balance_changed:
            print("\n*** MUDANCA DETECTADA! ***")
            print("  Size: {} -> {}".format(self.last_size, values['size']))
            print("  Balance: {} -> {}".format(self.last_balance, values['balance']))
            
            self.last_size = values['size']
            self.last_balance = values['balance']
        else:
            print("Sem mudancas (Size: {}, Balance: {})".format(values['size'], values['balance']))
    
    def run(self):
        print("="*60)
        print("Discord Stage Monitor - MODO DEBUG COMPLETO")
        print("OCR: " + ("Tesseract Local" if TESSERACT_AVAILABLE else "API Externa"))
        print("Intervalo: {} segundos".format(CHECK_INTERVAL))
        print("="*60)
        
        while True:
            try:
                self.check_carteira()
                print("\nAguardando {} segundos...\n".format(CHECK_INTERVAL))
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
