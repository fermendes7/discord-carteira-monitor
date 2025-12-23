import requests
import time
import os
from datetime import datetime
import base64

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_ID = os.getenv("SERVER_ID", "971218268574584852")
CHANNEL_ID = os.getenv("CHANNEL_ID", "1435710395909410878")  # Palco "Clássica"
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")
BROWSERLESS_URL = os.getenv("BROWSERLESS_URL", "http://browserless:3000")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))

class DiscordStageMonitor:
    """Monitor para capturar tela compartilhada em Stage Voice Channel"""
    
    def __init__(self):
        if not DISCORD_TOKEN:
            print("⚠️ AVISO: DISCORD_TOKEN não configurado!")
        print(f"🎤 Palco de Voz: Canal {CHANNEL_ID}")
        
    def take_screenshot_stage(self):
        """Captura screenshot da tela compartilhada no palco de voz"""
        try:
            stage_url = f"https://discord.com/channels/{SERVER_ID}/{CHANNEL_ID}"
            
            print("\n🎭 Capturando Stage Voice Channel...")
            print(f"📍 URL: {stage_url}")
            print(f"🔑 Token: {'✅ OK' if DISCORD_TOKEN else '❌ NÃO CONFIGURADO'}")
            
            endpoint = f"{BROWSERLESS_URL}/screenshot"
            
            # Payload otimizado para Stage Channel com stream
            payload = {
                "url": stage_url,
                "options": {
                    "type": "png",
                    "fullPage": False,
                    "encoding": "binary"
                },
                "gotoOptions": {
                    "waitUntil": "networkidle0",  # Aguarda tudo carregar incluindo stream
                    "timeout": 90000  # 90 segundos para carregar stream
                }
            }
            
            # Adicionar autenticação via cookies
            if DISCORD_TOKEN:
                payload["cookies"] = [
                    {
                        "name": "token",
                        "value": DISCORD_TOKEN,
                        "domain": ".discord.com",
                        "path": "/",
                        "httpOnly": True,
                        "secure": True
                    }
                ]
                print("🍪 Cookies de autenticação: Adicionados")
            else:
                print("⚠️ Sem autenticação - pode falhar!")
            
            # Aguardar elementos do stage carregarem (tempo extra para stream)
            payload["waitForTimeout"] = 10000  # 10 segundos extras após load
            
            print("⏳ Enviando requisição para Browserless...")
            print("   (Aguardando stream carregar - pode demorar 10-20s)")
            
            response = requests.post(endpoint, json=payload, timeout=120)
            
            print(f"📊 Status Browserless: {response.status_code}")
            
            if response.status_code == 200:
                screenshot_bytes = response.content
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                
                size_kb = len(screenshot_bytes) / 1024
                print(f"✅ Screenshot capturado! ({size_kb:.1f} KB)")
                
                return {
                    'screenshot_base64': screenshot_b64,
                    'screenshot_bytes': screenshot_bytes,
                    'timestamp': datetime.now().isoformat(),
                    'url': stage_url,
                    'channel_type': 'stage_voice',
                    'authenticated': bool(DISCORD_TOKEN),
                    'size_kb': size_kb
                }
            else:
                error_text = response.text[:500] if response.text else "Sem detalhes"
                print(f"❌ Erro Browserless: {error_text}")
                return None
            
        except requests.exceptions.Timeout:
            print("⏱️ Timeout! Stream demorou muito para carregar.")
            print("   Possíveis causas:")
            print("   - Stream offline")
            print("   - Autenticação inválida")
            print("   - Browserless sobrecarregado")
            return None
        except Exception as e:
            print(f"❌ Erro ao capturar: {str(e)}")
            return None
    
    def take_screenshot_with_script(self):
        """Método alternativo usando JavaScript para capturar área específica"""
        try:
            stage_url = f"https://discord.com/channels/{SERVER_ID}/{CHANNEL_ID}"
            
            print("\n🎭 Método Alternativo: Captura com JavaScript")
            print(f"📍 URL: {stage_url}")
            
            endpoint = f"{BROWSERLESS_URL}/screenshot"
            
            # Script para aguardar e capturar área do vídeo
            wait_script = """
            new Promise((resolve) => {
                // Aguardar 8 segundos para stream carregar
                setTimeout(() => {
                    console.log('Stream carregado, capturando...');
                    resolve();
                }, 8000);
            });
            """
            
            payload = {
                "url": stage_url,
                "options": {
                    "type": "png",
                    "fullPage": False
                },
                "gotoOptions": {
                    "waitUntil": "networkidle2",
                    "timeout": 90000
                },
                "waitForFunction": wait_script
            }
            
            if DISCORD_TOKEN:
                payload["cookies"] = [
                    {
                        "name": "token",
                        "value": DISCORD_TOKEN,
                        "domain": ".discord.com",
                        "path": "/",
                        "httpOnly": True,
                        "secure": True
                    }
                ]
            
            response = requests.post(endpoint, json=payload, timeout=120)
            
            if response.status_code == 200:
                screenshot_bytes = response.content
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                
                print(f"✅ Screenshot alternativo capturado! ({len(screenshot_bytes)/1024:.1f} KB)")
                
                return {
                    'screenshot_base64': screenshot_b64,
                    'screenshot_bytes': screenshot_bytes,
                    'timestamp': datetime.now().isoformat(),
                    'url': stage_url,
                    'channel_type': 'stage_voice',
                    'authenticated': bool(DISCORD_TOKEN),
                    'method': 'javascript'
                }
            else:
                print(f"❌ Método alternativo falhou: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ Erro método alternativo: {str(e)}")
            return None
    
    def take_screenshot(self):
        """Tenta capturar screenshot do stage (com fallback)"""
        # Método principal
        result = self.take_screenshot_stage()
        
        if result:
            return result
        
        # Fallback com JavaScript
        print("\n🔄 Tentando método alternativo...")
        result = self.take_screenshot_with_script()
        
        if result:
            return result
        
        print("❌ Todos os métodos falharam")
        return None
    
    def send_to_n8n(self, data):
        """Envia screenshot para n8n processar"""
        if not N8N_WEBHOOK_URL:
            print("⚠️ N8N_WEBHOOK_URL não configurado")
            return False
            
        try:
            print("\n📤 Enviando para n8n...")
            
            payload = {
                'timestamp': data['timestamp'],
                'screenshot_base64': data['screenshot_base64'],
                'discord_url': data['url'],
                'server_id': SERVER_ID,
                'channel_id': CHANNEL_ID,
                'channel_type': data.get('channel_type', 'stage_voice'),
                'authenticated': data.get('authenticated', False),
                'size_kb': data.get('size_kb', 0)
            }
            
            response = requests.post(
                N8N_WEBHOOK_URL, 
                json=payload, 
                timeout=30
            )
            
            print(f"📊 Status n8n: {response.status_code}")
            
            if response.status_code == 200:
                print("✅ Enviado com sucesso para n8n!")
                return True
            else:
                print(f"❌ Erro n8n: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao enviar: {str(e)}")
            return False
    
    def check(self):
        """Ciclo de captura e envio"""
        print("\n" + "="*70)
        print(f"🎬 [STAGE CHECK] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        result = self.take_screenshot()
        
        if not result:
            print("💥 Falha ao capturar screenshot do stage")
            return False
        
        success = self.send_to_n8n(result)
        
        if success:
            print("\n🎉 Ciclo completo com sucesso!")
            print("="*70)
            return True
        else:
            print("\n💥 Falha ao enviar para n8n")
            print("="*70)
            return False
    
    def run(self):
        """Loop principal de monitoramento"""
        print("\n" + "="*70)
        print("🎭 DISCORD STAGE VOICE MONITOR v8")
        print("="*70)
        print(f"📍 Server: {SERVER_ID}")
        print(f"🎤 Stage Channel: {CHANNEL_ID} (Palco 'Clássica')")
        print(f"⏱️  Intervalo: {CHECK_INTERVAL}s ({CHECK_INTERVAL/60:.1f} min)")
        print(f"🔑 Token: {'✅ Configurado' if DISCORD_TOKEN else '❌ NÃO CONFIGURADO'}")
        print(f"🌐 n8n: {'✅ Configurado' if N8N_WEBHOOK_URL else '❌ NÃO CONFIGURADO'}")
        print(f"🖥️  Browserless: {BROWSERLESS_URL}")
        print("="*70)
        
        if not DISCORD_TOKEN:
            print("\n⚠️⚠️⚠️ ATENÇÃO ⚠️⚠️⚠️")
            print("DISCORD_TOKEN não configurado!")
            print("Sem token, só vai capturar tela de login.")
            print("Configure DISCORD_TOKEN no EasyPanel.")
            print("="*70 + "\n")
        
        if not N8N_WEBHOOK_URL:
            print("\n⚠️ N8N_WEBHOOK_URL não configurado!")
            print("Screenshots não serão enviados.")
            print("="*70 + "\n")
        
        print("🚀 Iniciando monitoramento...\n")
        
        cycle = 0
        
        while True:
            try:
                cycle += 1
                print(f"\n🔄 Ciclo #{cycle}")
                
                self.check()
                
                print(f"\n💤 Aguardando {CHECK_INTERVAL}s até próxima verificação...")
                print(f"⏰ Próxima captura: {datetime.now().strftime('%H:%M:%S')} + {CHECK_INTERVAL}s\n")
                
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                print("\n\n🛑 Monitor encerrado pelo usuário")
                print("="*70)
                break
            except Exception as e:
                print(f"\n💥 ERRO CRÍTICO: {str(e)}")
                print("⏳ Aguardando 60s antes de tentar novamente...\n")
                time.sleep(60)

if __name__ == "__main__":
    monitor = DiscordStageMonitor()
    monitor.run()
