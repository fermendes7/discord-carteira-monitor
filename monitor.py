from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import time
import os
from datetime import datetime
import base64

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
SERVER_ID = os.getenv("SERVER_ID", "971218268574584852")
CHANNEL_ID = os.getenv("CHANNEL_ID", "1435710395909410878")
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "300"))

class DiscordStageMonitor:
    """Monitor v14 - Selenium com Chrome REAL"""
    
    def __init__(self):
        if not DISCORD_TOKEN:
            print("❌ ERRO: DISCORD_TOKEN não configurado!")
            exit(1)
        
        print("\n" + "="*70)
        print("🎭 DISCORD STAGE VOICE MONITOR v14 - SELENIUM")
        print("="*70)
        print(f"📍 Server: {SERVER_ID}")
        print(f"🎤 Stage Channel: {CHANNEL_ID}")
        print(f"⏱️  Intervalo: {CHECK_INTERVAL}s ({CHECK_INTERVAL/60:.1f} min)")
        print(f"🔑 Token: {'✅ Configurado' if DISCORD_TOKEN else '❌ NÃO CONFIGURADO'}")
        print(f"🌐 n8n: {'✅ Configurado' if N8N_WEBHOOK_URL else '❌ NÃO CONFIGURADO'}")
        print("="*70)
        
        self.driver = None
        self.authenticated = False
    
    def setup_driver(self):
        """Configura Chrome com Selenium"""
        try:
            print("\n🔧 Configurando Chrome...")
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # Inicializar driver
            self.driver = webdriver.Chrome(options=chrome_options)
            
            print("✅ Chrome configurado com sucesso!")
            return True
            
        except Exception as e:
            print(f"❌ Erro ao configurar Chrome: {e}")
            return False
    
    def authenticate(self):
        """Faz login no Discord usando token"""
        try:
            print("\n🔐 Autenticando no Discord...")
            
            # Ir para Discord
            self.driver.get("https://discord.com/app")
            time.sleep(3)
            
            # Injetar token via JavaScript
            script = f'''
            function login(token) {{
                setInterval(() => {{
                    document.body.appendChild(document.createElement('iframe')).contentWindow.localStorage.token = `"${{token}}"`;
                }}, 50);
                setTimeout(() => {{
                    location.reload();
                }}, 2500);
            }}
            login("{DISCORD_TOKEN}");
            '''
            
            self.driver.execute_script(script)
            
            print("⏳ Aguardando autenticação...")
            time.sleep(10)
            
            # Verificar se autenticou
            current_url = self.driver.current_url
            if "login" not in current_url.lower():
                print("✅ Autenticação bem-sucedida!")
                self.authenticated = True
                return True
            else:
                print("⚠️ Ainda na tela de login - token pode estar inválido")
                self.authenticated = False
                return False
                
        except Exception as e:
            print(f"❌ Erro na autenticação: {e}")
            self.authenticated = False
            return False
    
    def take_screenshot(self):
        """Captura screenshot do Stage Channel"""
        try:
            stage_url = f"https://discord.com/channels/{SERVER_ID}/{CHANNEL_ID}"
            
            print(f"\n🎭 Navegando para Stage Voice Channel...")
            print(f"🔗 URL: {stage_url}")
            
            self.driver.get(stage_url)
            
            print("⏳ Aguardando página carregar...")
            time.sleep(15)
            
            # Tirar screenshot
            print("📸 Capturando screenshot...")
            screenshot_png = self.driver.get_screenshot_as_png()
            
            print(f"✅ Screenshot capturado! ({len(screenshot_png)} bytes = {len(screenshot_png)/1024:.1f} KB)")
            
            return screenshot_png
            
        except Exception as e:
            print(f"❌ Erro ao capturar screenshot: {e}")
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
                "version": "v14_selenium",
                "authenticated": self.authenticated
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
        print(f"\n🚀 Iniciando monitoramento v14 com Selenium...\n")
        
        # Setup inicial
        if not self.setup_driver():
            print("❌ Falha ao configurar Chrome!")
            return
        
        # Autenticar uma vez
        if not self.authenticate():
            print("⚠️ Autenticação falhou, mas vou continuar tentando capturar...")
        
        cycle = 0
        
        try:
            while True:
                try:
                    cycle += 1
                    print(f"\n{'='*70}")
                    print(f"🔄 Ciclo #{cycle}")
                    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"🔐 Autenticado: {'✅ SIM' if self.authenticated else '❌ NÃO'}")
                    print(f"{'='*70}")
                    
                    # Capturar screenshot
                    screenshot = self.take_screenshot()
                    
                    if screenshot:
                        # Enviar para n8n
                        success = self.send_to_n8n(screenshot)
                        
                        if success:
                            if self.authenticated:
                                print(f"\n🎉 Ciclo completo com sucesso! (AUTENTICADO ✅)")
                            else:
                                print(f"\n⚠️ Ciclo completo mas NÃO AUTENTICADO!")
                        else:
                            print(f"\n⚠️ Ciclo completo mas com problemas no envio")
                    else:
                        print(f"\n❌ Falha na captura do screenshot")
                    
                    # Aguardar próximo ciclo
                    print(f"\n{'='*70}")
                    print(f"⏳ Aguardando {CHECK_INTERVAL}s até próxima verificação...")
                    print(f"{'='*70}\n")
                    
                    time.sleep(CHECK_INTERVAL)
                    
                except Exception as e:
                    print(f"\n❌ Erro no ciclo: {e}")
                    print(f"🔄 Tentando novamente em {CHECK_INTERVAL}s...")
                    time.sleep(CHECK_INTERVAL)
                    
        except KeyboardInterrupt:
            print(f"\n\n⚠️ Monitor interrompido pelo usuário")
        finally:
            if self.driver:
                print("🔒 Fechando Chrome...")
                self.driver.quit()

if __name__ == "__main__":
    monitor = DiscordStageMonitor()
    monitor.run()
