import requests
import time
import os
from datetime import datetime
import base64

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_ID = os.getenv("SERVER_ID", "971218268574584852")
CHANNEL_ID = os.getenv("CHANNEL_ID", "1435710395909410878")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")
BROWSERLESS_URL = os.getenv("BROWSERLESS_URL", "http://browserless:3000")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))

class DiscordMonitor:
    def __init__(self):
        pass
        
    def take_screenshot(self):
        """Captura screenshot do canal Discord"""
        try:
            discord_url = "https://discord.com/channels/{}/{}".format(SERVER_ID, CHANNEL_ID)
            
            print("Capturando screenshot...")
            print("URL: " + discord_url)
            
            endpoint = BROWSERLESS_URL + "/screenshot"
            
            # Payload simplificado - apenas campos basicos
            payload = {
                "url": discord_url,
                "options": {
                    "type": "png",
                    "fullPage": False
                }
            }
            
            response = requests.post(endpoint, json=payload, timeout=60)
            
            print("Status: " + str(response.status_code))
            
            if response.status_code == 200:
                screenshot_bytes = response.content
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                
                print("Screenshot capturado! ({} bytes)".format(len(screenshot_bytes)))
                
                return {
                    'screenshot_base64': screenshot_b64,
                    'screenshot_bytes': screenshot_bytes,
                    'timestamp': datetime.now().isoformat(),
                    'url': discord_url
                }
            else:
                print("Erro: " + response.text[:200])
                return None
            
        except Exception as e:
            print("Erro ao capturar: " + str(e))
            return None
    
    def send_to_n8n(self, data):
        """Envia screenshot para n8n processar"""
        if not N8N_WEBHOOK_URL:
            print("N8N_WEBHOOK_URL nao configurado")
            return False
            
        try:
            print("Enviando para n8n...")
            
            payload = {
                'timestamp': data['timestamp'],
                'screenshot_base64': data['screenshot_base64'],
                'discord_url': data['url'],
                'server_id': SERVER_ID,
                'channel_id': CHANNEL_ID
            }
            
            response = requests.post(
                N8N_WEBHOOK_URL, 
                json=payload, 
                timeout=30
            )
            
            print("Status n8n: " + str(response.status_code))
            
            if response.status_code == 200:
                print("Enviado com sucesso!")
                return True
            else:
                print("Erro n8n: " + response.text[:200])
                return False
                
        except Exception as e:
            print("Erro ao enviar: " + str(e))
            return False
    
    def check(self):
        """Captura e envia para n8n"""
        print("\n" + "="*60)
        print("[CHECK] " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("="*60)
        
        result = self.take_screenshot()
        
        if not result:
            print("Falha ao capturar screenshot")
            return
        
        success = self.send_to_n8n(result)
        
        if success:
            print("Ciclo completo com sucesso!")
        else:
            print("Falha ao enviar para n8n")
    
    def run(self):
        """Loop principal"""
        print("="*60)
        print("Discord Monitor - Screenshot para n8n")
        print("Canal: " + CHANNEL_ID)
        print("Intervalo: {}s".format(CHECK_INTERVAL))
        print("n8n: " + (N8N_WEBHOOK_URL[:50] + "..." if N8N_WEBHOOK_URL else "NAO CONFIGURADO"))
        print("="*60)
        
        if not N8N_WEBHOOK_URL:
            print("\nAVISO: N8N_WEBHOOK_URL nao configurado!")
            print("Configure a variavel de ambiente.\n")
        
        while True:
            try:
                self.check()
                
                print("\nProxima verificacao em {}s...\n".format(CHECK_INTERVAL))
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                print("\nMonitor encerrado")
                break
            except Exception as e:
                print("\nERRO: " + str(e))
                print("Aguardando 60s...\n")
                time.sleep(60)

if __name__ == "__main__":
    monitor = DiscordMonitor()
    monitor.run()
