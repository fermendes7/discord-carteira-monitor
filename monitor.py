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

class DiscordMonitor:
    def __init__(self):
        print("Inicializando Discord Monitor v5 (COM AUTENTICACAO)")
        
    def take_screenshot_with_auth(self):
        """Captura screenshot COM autenticacao Discord via Puppeteer"""
        try:
            discord_url = f"https://discord.com/channels/{SERVER_ID}/{CHANNEL_ID}"
            
            print("Capturando com autenticacao Discord...")
            print(f"URL: {discord_url}")
            
            endpoint = f"{BROWSERLESS_URL}/function"
            
            # Script Puppeteer completo com autenticacao
            puppeteer_script = f"""
module.exports = async ({{ page }}) => {{
    try {{
        console.log('Iniciando captura autenticada...');
        
        // 1. Navegar para pagina de login do Discord
        console.log('Navegando para Discord login...');
        await page.goto('https://discord.com/login', {{
            waitUntil: 'networkidle2',
            timeout: 60000
        }});
        await page.waitForTimeout(3000);
        
        // 2. Injetar token no localStorage
        console.log('Injetando token no localStorage...');
        await page.evaluate((token) => {{
            localStorage.setItem('token', `"${{token}}"`);
        }}, '{DISCORD_TOKEN}');
        
        console.log('Token injetado!');
        
        // 3. Navegar para canal especifico
        console.log('Navegando para canal: {discord_url}');
        await page.goto('{discord_url}', {{
            waitUntil: 'networkidle2',
            timeout: 60000
        }});
        
        // 4. Aguardar carregamento do Discord (15 segundos)
        console.log('Aguardando carregamento completo...');
        await page.waitForTimeout(15000);
        
        // 5. Capturar screenshot
        console.log('Capturando screenshot...');
        const screenshot = await page.screenshot({{
            type: 'png',
            fullPage: false
        }});
        
        console.log('Screenshot capturado com sucesso!');
        
        return {{
            type: 'image/png',
            data: screenshot.toString('base64'),
            success: true
        }};
        
    }} catch (error) {{
        console.error('Erro no Puppeteer:', error);
        return {{
            error: error.message,
            success: false
        }};
    }}
}};
"""
            
            payload = {
                "code": puppeteer_script
            }
            
            print("Enviando para Browserless /function...")
            response = requests.post(endpoint, json=payload, timeout=150)
            
            print(f"Status Browserless: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                
                if result.get('success'):
                    screenshot_b64 = result['data']
                    screenshot_bytes = base64.b64decode(screenshot_b64)
                    
                    print(f"Screenshot autenticado capturado! ({len(screenshot_bytes)} bytes)")
                    
                    return {
                        'screenshot_base64': screenshot_b64,
                        'screenshot_bytes': screenshot_bytes,
                        'timestamp': datetime.now().isoformat(),
                        'url': discord_url,
                        'authenticated': True
                    }
                else:
                    print(f"Erro no Puppeteer: {result.get('error')}")
                    return None
            else:
                print(f"Erro HTTP: {response.text[:500]}")
                return None
            
        except Exception as e:
            print(f"Excecao ao capturar: {str(e)}")
            import traceback
            traceback.print_exc()
            return None
    
    def take_screenshot_fallback(self):
        """Metodo fallback sem autenticacao (caso o v5 falhe)"""
        try:
            discord_url = f"https://discord.com/channels/{SERVER_ID}/{CHANNEL_ID}"
            
            print("Tentando metodo fallback...")
            
            endpoint = f"{BROWSERLESS_URL}/screenshot"
            
            payload = {
                "url": discord_url,
                "options": {
                    "type": "png",
                    "fullPage": False
                },
                "gotoOptions": {
                    "waitUntil": "networkidle2",
                    "timeout": 60000
                }
            }
            
            response = requests.post(endpoint, json=payload, timeout=90)
            
            if response.status_code == 200:
                screenshot_bytes = response.content
                screenshot_b64 = base64.b64encode(screenshot_bytes).decode('utf-8')
                
                print(f"Screenshot fallback capturado ({len(screenshot_bytes)} bytes)")
                
                return {
                    'screenshot_base64': screenshot_b64,
                    'screenshot_bytes': screenshot_bytes,
                    'timestamp': datetime.now().isoformat(),
                    'url': discord_url,
                    'authenticated': False
                }
            else:
                print(f"Erro fallback: {response.text[:200]}")
                return None
                
        except Exception as e:
            print(f"Erro no fallback: {str(e)}")
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
                'channel_id': CHANNEL_ID,
                'authenticated': data.get('authenticated', False)
            }
            
            response = requests.post(
                N8N_WEBHOOK_URL, 
                json=payload, 
                timeout=30
            )
            
            print(f"Status n8n: {response.status_code}")
            
            if response.status_code == 200:
                print("Enviado com sucesso para n8n!")
                return True
            else:
                print(f"Erro n8n: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"Erro ao enviar para n8n: {str(e)}")
            return False
    
    def check(self):
        """Captura e envia para n8n"""
        print("\n" + "="*70)
        print(f"[CHECK v5] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # Tentar metodo autenticado primeiro
        result = self.take_screenshot_with_auth()
        
        # Se falhar, tentar fallback
        if not result:
            print("\nMetodo autenticado falhou, tentando fallback...")
            result = self.take_screenshot_fallback()
        
        if not result:
            print("Falha em todos os metodos de captura")
            return
        
        # Informar qual metodo funcionou
        if result.get('authenticated'):
            print("Captura autenticada com sucesso!")
        else:
            print("Captura sem autenticacao (pode mostrar tela de login)")
        
        success = self.send_to_n8n(result)
        
        if success:
            print("Ciclo completo com sucesso!")
        else:
            print("Falha ao enviar para n8n")
    
    def run(self):
        """Loop principal"""
        print("="*70)
        print("Discord Monitor v5 - COM AUTENTICACAO")
        print("="*70)
        print(f"Canal: {CHANNEL_ID}")
        print(f"Intervalo: {CHECK_INTERVAL}s")
        print(f"n8n: {N8N_WEBHOOK_URL[:50]}..." if N8N_WEBHOOK_URL else "NAO CONFIGURADO")
        print(f"Token Discord: {'Configurado' if DISCORD_TOKEN else 'FALTANDO'}")
        print("="*70)
        
        if not DISCORD_TOKEN:
            print("\nATENCAO: DISCORD_TOKEN nao configurado!")
            print("O sistema vai funcionar mas pode mostrar tela de login.\n")
        
        if not N8N_WEBHOOK_URL:
            print("\nATENCAO: N8N_WEBHOOK_URL nao configurado!")
            print("Configure a variavel de ambiente.\n")
        
        while True:
            try:
                self.check()
                
                print(f"\nProxima verificacao em {CHECK_INTERVAL}s...")
                print("="*70 + "\n")
                time.sleep(CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                print("\nMonitor encerrado pelo usuario")
                break
            except Exception as e:
                print(f"\nERRO CRITICO: {str(e)}")
                import traceback
                traceback.print_exc()
                print("\nAguardando 60s antes de tentar novamente...")
                time.sleep(60)

if __name__ == "__main__":
    monitor = DiscordMonitor()
    monitor.run()
