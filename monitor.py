import requests
import time
import json
import re
import os
from datetime import datetime
import base64

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
                # Screenshot retorna imagem binaria
                screenshot_b64 = base64.b64encode(response.content).decode('utf-8')
                
                print("Screenshot capturado com sucesso!")
                
                return {
                    'screenshot': screenshot_b64,
                    'pageText': '',
                    'timestamp': datetime.now().isoformat()
                }
            else:
                print("Erro ao capturar: " + str(response.status_code))
                print("Resposta: " + response.text[:200])
                return None
            
        except requests.exceptions.ConnectionError as e:
            print("ERRO DE CONEXAO: Browserless nao acessivel")
            print("  Detalhes: " + str(e))
            return None
        except requests.exceptions.Timeout:
            print("ERRO: Timeout ao conectar no Browserless")
            return None
        except Exception as e:
            print("Erro ao tirar screenshot: " + str(e))
            print("  Tipo: " + type(e).__name__)
            return None
    
    def ocr_screenshot(self, screenshot_base64):
        try:
            print("Usando OCR para ler imagem...")
            
            response = requests.post(
                'https://api.ocr.space/parse/image',
                data={
                    'base64Image': 'data:image/png;base64,' + screenshot_base64,
                    'language': 'eng',
                    'isOverlayRequired': 'false',
                    'OCREngine': '2'
                },
                timeout=30
            )
            
            print("Status OCR: " + str(response.status_code))
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('ParsedResults') and len(result['ParsedResults']) > 0:
                    text = result['ParsedResults'][0].get('ParsedText', '')
                    print("Texto OCR extraido com sucesso!")
                    print("Primeiros 300 caracteres do OCR:")
                    print(text[:300])
                    return text
                else:
                    print("OCR nao retornou resultados")
                    print("Resposta completa: " + str(result))
            else:
                print("OCR falhou com status: " + str(response.status_code))
                
        except Exception as e:
            print("OCR falhou: " + str(e))
            print("  Tipo: " + type(e).__name__)
        
        return None
    
    def extract_values_from_text(self, text):
        try:
            if not text:
                return None
                
            size_match = re.search(r'size[:\s]*([0-9,.]+)', text, re.IGNORECASE)
            balance_match = re.search(r'balance[:\s]*([0-9,.]+)', text, re.IGNORECASE)
            
            if size_match and balance_match:
                size = float(size_match.group(1).replace(',', ''))
                balance = float(balance_match.group(1).replace(',', ''))
                print("Valores encontrados! Size: {}, Balance: {}".format(size, balance))
                return {'size': size, 'balance': balance}
            else:
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
        
        screenshot_b64 = result.get('screenshot', '')
        
        if not screenshot_b64:
            print("Screenshot vazio")
            return
        
        # Tenta OCR
        ocr_text = self.ocr_screenshot(screenshot_b64)
        
        if not ocr_text:
            print("Nao foi possivel extrair texto da imagem")
            return
        
        values = self.extract_values_from_text(ocr_text)
        
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
