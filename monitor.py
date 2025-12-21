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
        
    def take_screenshot_with_auth(self):
        """Tira screenshot COM autenticacao Discord"""
        try:
            if not DISCORD_TOKEN:
                print("ERRO: DISCORD_TOKEN nao configurado!")
                return None
            
            discord_url = "https://discord.com/channels/{}/{}".format(SERVER_ID, CHANNEL_ID)
            
            print("Autenticando no Discord e capturando screenshot...")
            
            # Usa /content com script de autenticacao
            endpoint = BROWSERLESS_URL + "/content"
            
            # Script para autenticar e navegar
            auth_script = """
            (async () => {{
                // Vai para pagina de login
                await page.goto('https://discord.com/login');
                
                // Injeta token no localStorage
                await page.evaluate((token) => {{
                    function setToken() {{
                        const iframe = document.createElement('iframe');
                        iframe.style.display = 'none';
                        document.body.appendChild(iframe);
                        iframe.contentWindow.localStorage.setItem('token', JSON.stringify(token));
                    }}
                    setToken();
                }}, '{}');
                
                // Aguarda um pouco
                await page.waitForTimeout(2000);
                
                // Recarrega para aplicar token
                await page.reload();
                await page.waitForTimeout(3000);
                
                // Navega para o canal
                await page.goto('{}');
                await page.waitForTimeout(8000);
                
                // Tira screenshot
                const screenshot = await page.screenshot({{ type: 'png', fullPage: false }});
                
                // Pega texto da pagina
                const text = await page.evaluate(() => document.body.innerText);
                
                return {{
                    screenshot: screenshot.toString('base64'),
                    text: text
                }};
            }})();
            """.format(DISCORD_TOKEN, discord_url)
            
            payload = {
                "code": auth_script
            }
            
            print("Enviando para: " + endpoint)
            
            response = requests.post(
                endpoint,
                json=payload,
                timeout=90
            )
            
            print("Status: " + str(response.status_code))
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    
                    screenshot_b64 = result.get('screenshot', '')
                    page_text = result.get('text', '')
                    
                    if screenshot_b64:
                        screenshot_bytes = base64.b64decode(screenshot_b64)
                        
                        # Salva para debug
                        try:
                            with open('/tmp/screenshot_auth.png', 'wb') as f:
                                f.write(screenshot_bytes)
                            print("Screenshot salvo em: /tmp/screenshot_auth.png")
                        except:
                            pass
                        
                        print("Screenshot COM autenticacao capturado!")
                        
                        if page_text:
                            print("Texto da pagina (primeiros 500 chars):")
                            print(page_text[:500])
                        
                        return {
                            'screenshot_bytes': screenshot_bytes,
                            'screenshot_b64': screenshot_b64,
                            'page_text': page_text,
                            'timestamp': datetime.now().isoformat()
                        }
                except Exception as e:
                    print("Erro ao processar resposta: " + str(e))
            else:
                print("Erro HTTP: " + response.text[:300])
            
            return None
            
        except Exception as e:
            print("Erro ao capturar: " + str(e))
            return None
    
    def ocr_local(self, image_bytes):
        try:
            if not TESSERACT_AVAILABLE:
                return None
                
            print("\nTesseract OCR...")
            image = Image.open(BytesIO(image_bytes))
            text = pytesseract.image_to_string(image)
            
            print("="*60)
            print("TEXTO TESSERACT:")
            print("="*60)
            print(text if text else "[VAZIO]")
            print("="*60)
            
            return text
            
        except Exception as e:
            print("Tesseract falhou: " + str(e))
            return None
    
    def extract_values_from_text(self, text):
        try:
            if not text or len(text.strip()) < 5:
                print("Texto vazio ou muito curto")
                return None
            
            print("\nProcurando padroes...")
            
            # Padroes flexiveis
            patterns = [
                (r'(?:size|SIZE|Size)[\s:]*([0-9,.]+)', r'(?:balance|BALANCE|Balance)[\s:]*([0-9,.]+)'),
                (r'([0-9,.]+)[\s]*(?:size|SIZE)', r'([0-9,.]+)[\s]*(?:balance|BALANCE)'),
            ]
            
            for size_pattern, balance_pattern in patterns:
                size_match = re.search(size_pattern, text, re.IGNORECASE)
                balance_match = re.search(balance_pattern, text, re.IGNORECASE)
                
                if size_match and balance_match:
                    size = float(size_match.group(1).replace(',', ''))
                    balance = float(balance_match.group(1).replace(',', ''))
                    
                    print("ENCONTRADO! Size: {}, Balance: {}".format(size, balance))
                    return {'size': size, 'balance': balance}
            
            print("Padroes nao encontrados")
                
        except Exception as e:
            print("Erro: " + str(e))
            
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
            print("Erro ao enviar: " + str(e))
            return False
    
    def check_carteira(self):
        print("\n" + "="*60)
        print("[VERIFICACAO] " + datetime.now().strftime("%H:%M:%S"))
        print("="*60)
        
        result = self.take_screenshot_with_auth()
        if not result:
            print("Falha ao capturar")
            return
        
        # Primeiro tenta usar o texto da pagina (se veio do /content)
        page_text = result.get('page_text', '')
        values = None
        
        if page_text and len(page_text) > 10:
            print("\nUsando texto direto da pagina...")
            values = self.extract_values_from_text(page_text)
        
        # Se nao achou, tenta OCR na imagem
        if not values:
            image_bytes = result.get('screenshot_bytes')
            if image_bytes:
                ocr_text = self.ocr_local(image_bytes)
                if ocr_text:
                    values = self.extract_values_from_text(ocr_text)
        
        if not values:
            print("\nSize/Balance NAO ENCONTRADOS")
            return
        
        # Detecta mudancas
        size_changed = (self.last_size != values['size'])
        balance_changed = (self.last_balance != values['balance'])
        
        if size_changed or balance_changed:
            print("\n*** MUDANCA! ***")
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
        print("Discord Stage Monitor - COM AUTENTICACAO")
        print("OCR: " + ("Tesseract" if TESSERACT_AVAILABLE else "Externo"))
        print("Intervalo: {} seg".format(CHECK_INTERVAL))
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
