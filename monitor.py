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
    print("AVISO: pytesseract nao disponivel - usando OCR externo")

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
            
            print("Status da resposta: " + str(response.status_code))
            
            if response.status_code == 200:
                print("Screenshot capturado com sucesso!")
                
                return {
                    'screenshot_bytes': response.content,
                    'screenshot_b64': base64.b64encode(response.content).decode('utf-8'),
                    'timestamp': datetime.now().isoformat()
                }
            else:
                print("Erro ao capturar: " + str(response.status_code))
                print("Resposta: " + response.text[:200])
                return None
            
        except Exception as e:
            print("Erro ao tirar screenshot: " + str(e))
            print("  Tipo: " + type(e).__name__)
            return None
    
    def ocr_local(self, image_bytes):
        """OCR usando Tesseract local"""
        try:
            if not TESSERACT_AVAILABLE:
                return None
                
            print("Usando Tesseract OCR local...")
            
            image = Image.open(BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            
            print("Texto extraido com Tesseract!")
            print("Primeiros 300 caracteres:")
            print(text[:300])
            
            return text
            
        except Exception as e:
            print("Tesseract falhou: " + str(e))
            return None
    
    def ocr_external(self, screenshot_base64):
        """OCR usando API externa (fallback)"""
        try:
            print("Tentando OCR externo (API)...")
            
            # Tenta OCR.space com API key gratuita
            response = requests.post(
                'https://api.ocr.space/parse/image',
                data={
                    'base64Image': 'data:image/png;base64,' + screenshot_base64,
                    'language': 'eng',
                    'isOverlayRequired': 'false',
                    'OCREngine': '2',
                    'apikey': 'helloworld'  # API key publica de teste
                },
                timeout=30
            )
            
            print("Status OCR externo: " + str(response.status_code))
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('ParsedResults') and len(result['ParsedResults']) > 0:
                    text = result['ParsedResults'][0].get('ParsedText', '')
                    print("Texto OCR extraido com API externa!")
                    print("Primeiros 300 caracteres:")
                    print(text[:300])
                    return text
                    
        except Exception as e:
            print("OCR externo falhou: " + str(e))
        
        return None
    
    def extract_values_from_text(self, text):
        try:
            if not text:
                return None
            
            # Tenta varios padroes
            patterns = [
                (r'size[:\s]*([0-9,.]+)', r'balance[:\s]*([0-9,.]+)'),
                (r'Size[:\s]*([0-9,.]+)', r'Balance[:\s]*([0-9,.]+)'),
                (r'SIZE[:\s]*([0-9,.]+)', r'BALANCE[:\s]*([0-9,.]+)'),
                (r'tamanho[:\s]*([0-9,.]+)', r'saldo[:\s]*([0-9,.]+)'),
            ]
            
            for size_pattern, balance_pattern in patterns:
                size_match = re.search(size_pattern, text, re.IGNORECASE)
                balance_match = re.search(balance_pattern, text, re.IGNORECASE)
                
                if size_match and balance_match:
                    size = float(size_match.group(1).replace(',', ''))
                    balance = float(balance_match.group(1).replace(',', ''))
                    print("Valores encontrados! Size: {}, Balance: {}".format(size, balance))
                    return {'size': size, 'balance': balance}
            
            print("Padroes Size/Balance nao encontrados no texto")
                
        except Exception as e:
            print("Erro ao extrair valores: " + str(e))
            
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
        
        image_bytes = result.get('screenshot_bytes')
        image_b64 = result.get('screenshot_b64')
        
        if not image_bytes:
            print("Screenshot vazio")
            return
        
        # Tenta OCR local primeiro (mais rapido e confiavel)
        ocr_text = self.ocr_local(image_bytes)
        
        # Se falhar, tenta OCR externo
        if not ocr_text:
            ocr_text = self.ocr_external(image_b64)
        
        if not ocr_text:
            print("Nao foi possivel extrair texto da imagem")
            return
        
        values = self.extract_values_from_text(ocr_text)
        
        if not values:
            print("Size e Balance nao encontrados no texto")
            print("\n=== TEXTO COMPLETO EXTRAIDO ===")
            print(ocr_text)
            print("=== FIM DO TEXTO ===\n")
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
        
        if TESSERACT_AVAILABLE:
            print("OCR: Tesseract Local (RAPIDO)")
        else:
            print("OCR: API Externa (LENTO)")
        
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
