import requests
import time
import os
from datetime import datetime
import base64
import json

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_ID = os.getenv("SERVER_ID", "971218268574584852")
CHANNEL_ID = os.getenv("CHANNEL_ID", "1435710395909410878")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")
BROWSERLESS_URL = os.getenv("BROWSERLESS_URL", "http://browserless:3000")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))

class DiscordStageMonitor:
    """Monitor v12 - Corrigindo erro 400 do Browserless"""
    
    def __init__(self):
        if not DISCORD_TOKEN:
            print("❌ ERRO: DISCORD_TOKEN não configurado!")
            exit(1)
        
        print("\n" + "="*70)
        print("🎭 DISCORD STAGE VOICE MONITOR v12 - BROWSERLESS FIX")
        print("="*70)
        print(f"📍 Server: {SERVER_ID}")
        print(f"🎤 Stage Channel: {CHANNEL_ID}")
        print(f"⏱️  Intervalo: {CHECK_INTERVAL}s ({CHECK_INTERVAL/60:.1f} min)")
        print(f"🔑 Token: {'✅ Configurado' if DISCORD_TOKEN else '❌ NÃO CONFIGURADO'}")
        print(f"🌐 n8n: {'✅ Configurado' if N8N_WEBHOOK_URL else '❌ NÃO CONFIGURADO'}")
        print("="*70)
    
    def take_screenshot_method_simple(self):
        """Método simplificado usando apenas screenshot endpoint"""
        try:
            stage_url = f"https://discord.com/channels/{SERVER_ID}/{CHANNEL_ID}"
            
            print(f"\n🎭 Capturando Stage Voice Channel...")
            print(f"🔗 URL: {stage_url}")
            print(f"🔑 Token: {DISCORD_TOKEN[:20]}..." if DISCORD_TOKEN else "❌ Sem token")
            
            endpoint = f"{BROWSERLESS_URL}/screenshot"
            
            # Payload simplificado
            payload = {
                "url": stage_url,
                "options": {
                    "type": "png",
                    "fullPage": False
                },
                "gotoOptions": {
                    "waitUntil": "networkidle2",
                    "timeout": 60000
                },
                "waitFor": 10000
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            print(f"📤 Enviando requisição para Browserless...")
            
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=90
            )
            
            print(f"📊 Status Browserless: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ Screenshot capturado! ({len(response.content)} bytes = {len(response.content)/1024:.1f} KB)")
                return response.content
            else:
                print(f"❌ Browserless retornou status {response.status_code}")
                print(f"📄 Resposta: {response.text[:500]}")
                return None
                
        except Exception as e:
            print(f"❌ Erro: {e}")
            return None
    
    def send_to_n8n(self, screenshot_data):
        """Envia screenshot para n8n webhook"""
        try:
            if not N8N_WEBHOOK_URL:
                print("⚠️ N8N_WEBHOOK_URL não configurado, pulando envio...")
                return True
            
            print(f"\n📤 Enviando para n8n...")
            
            # Converter para base64
            screenshot_b64 = base64.b64encode(screenshot_data).decode('utf-8')
            
            # Payload para n8n
            payload = {
                "timestamp": datetime.now().isoformat(),
                "server_id": SERVER_ID,
                "channel_id": CHANNEL_ID,
                "screenshot": screenshot_b64,
                "screenshot_size": len(screenshot_data),
                "format": "png",
                "version": "v12_simple",
                "note": "Using simple screenshot method - no login verification"
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                N8N_WEBHOOK_URL,
                json=payload,
                headers=headers,
                timeout=30
            )
            
            print(f"📊 Status n8n: {response.status_code}")
            
            if response.status_code == 200:
                print(f"✅ Enviado com sucesso para n8n!")
                return True
            else:
                print(f"⚠️ n8n retornou status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao enviar para n8n: {e}")
            return False
    
    def run(self):
        """Loop principal do monitor"""
        print(f"\n🚀 Iniciando monitoramento v12...\n")
        
        cycle = 0
        
        while True:
            try:
                cycle += 1
                print(f"\n{'='*70}")
                print(f"🔄 Ciclo #{cycle}")
                print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*70}")
                
                # Capturar screenshot
                screenshot = self.take_screenshot_method_simple()
                
                if screenshot:
                    # Enviar para n8n
                    success = self.send_to_n8n(screenshot)
                    
                    if success:
                        print(f"\n🎉 Ciclo completo com sucesso!")
                    else:
                        print(f"\n⚠️ Ciclo completo mas com problemas no envio")
                else:
                    print(f"\n❌ Falha na captura do screenshot")
                
                # Aguardar próximo ciclo
                print(f"\n{'='*70}")
                print(f"⏳ Aguardando {CHECK_INTERVAL}s até próxima verificação...")
                print(f"{'='*70}\n")
                
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                print(f"\n\n⚠️ Monitor interrompido pelo usuário")
                break
            except Exception as e:
                print(f"\n❌ Erro no ciclo: {e}")
                print(f"🔄 Tentando novamente em {CHECK_INTERVAL}s...")
                time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    monitor = DiscordStageMonitor()
    monitor.run()
