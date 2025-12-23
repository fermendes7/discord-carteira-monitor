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
    """Monitor v11 - Usando /content do Browserless (aceita HTML customizado)"""
    
    def __init__(self):
        if not DISCORD_TOKEN:
            print("❌ ERRO: DISCORD_TOKEN não configurado!")
            exit(1)
        
        print("\n" + "="*70)
        print("🎭 DISCORD STAGE VOICE MONITOR v11 - MÉTODO CONTENT")
        print("="*70)
        print(f"📍 Server: {SERVER_ID}")
        print(f"🎤 Stage Channel: {CHANNEL_ID} (Palco 'Clássica')")
        print(f"⏱️  Intervalo: {CHECK_INTERVAL}s ({CHECK_INTERVAL/60:.1f} min)")
        print(f"🔑 Token: {'✅ Configurado' if DISCORD_TOKEN else '❌ NÃO CONFIGURADO'}")
        print(f"🌐 n8n: {'✅ Configurado' if N8N_WEBHOOK_URL else '❌ NÃO CONFIGURADO'}")
        print("="*70)
    
    def take_screenshot_with_puppeteer_script(self):
        """Usa endpoint /function com script Puppeteer completo"""
        try:
            stage_url = f"https://discord.com/channels/{SERVER_ID}/{CHANNEL_ID}"
            
            print(f"\n🎭 Capturando via Puppeteer Script...")
            print(f"🔗 URL: {stage_url}")
            
            endpoint = f"{BROWSERLESS_URL}/function"
            
            # Script Puppeteer que vai FORÇAR autenticação
            puppeteer_script = f"""
module.exports = async ({{ page, context }}) => {{
    try {{
        console.log('🚀 Iniciando captura autenticada...');
        
        // 1. Definir User-Agent realista
        await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36');
        
        // 2. Definir viewport
        await page.setViewport({{ width: 1920, height: 1080 }});
        
        // 3. Ir para Discord (qualquer página)
        console.log('📍 Navegando para Discord...');
        await page.goto('https://discord.com/app', {{
            waitUntil: 'domcontentloaded',
            timeout: 60000
        }});
        
        // 4. FORÇAR token via evaluate (executa no contexto do browser)
        console.log('🔑 Injetando token...');
        await page.evaluate((token) => {{
            // Limpar storage
            localStorage.clear();
            sessionStorage.clear();
            
            // Definir token (formato exato do Discord)
            localStorage.setItem('token', `"${{token}}"`);
            
            // Também no sessionStorage
            sessionStorage.setItem('token', `"${{token}}"`);
            
            console.log('Token definido:', localStorage.getItem('token'));
        }}, '{DISCORD_TOKEN}');
        
        // 5. Aguardar um pouco
        await page.waitForTimeout(2000);
        
        // 6. Navegar para o Stage Channel
        console.log('🎯 Navegando para Stage Channel...');
        await page.goto('{stage_url}', {{
            waitUntil: 'networkidle0',
            timeout: 90000
        }});
        
        // 7. Aguardar elementos carregarem
        console.log('⏳ Aguardando elementos...');
        await page.waitForTimeout(15000);
        
        // 8. Verificar se está logado (procurar elementos da interface)
        const isLoggedIn = await page.evaluate(() => {{
            // Se tiver botão "Log In", NÃO está logado
            const loginButton = document.querySelector('button:contains("Log In")');
            if (loginButton) return false;
            
            // Se tiver elementos da interface do Discord, está logado
            const chatArea = document.querySelector('[class*="chat"]');
            const sidebar = document.querySelector('[class*="sidebar"]');
            
            return !!(chatArea || sidebar);
        }});
        
        console.log('🔍 Status login:', isLoggedIn ? 'LOGADO ✅' : 'NÃO LOGADO ❌');
        
        // 9. Tirar screenshot
        console.log('📸 Capturando screenshot...');
        const screenshot = await page.screenshot({{
            type: 'png',
            fullPage: false
        }});
        
        console.log('✅ Screenshot capturado!');
        
        return {{
            data: {{
                screenshot: screenshot.toString('base64'),
                logged_in: isLoggedIn,
                url: page.url(),
                timestamp: new Date().toISOString()
            }},
            type: 'application/json'
        }};
        
    }} catch (error) {{
        console.error('❌ Erro:', error.message);
        return {{
            data: {{
                error: error.message,
                screenshot: null
            }},
            type: 'application/json'
        }};
    }}
}};
"""
            
            payload = {
                "code": puppeteer_script,
                "context": {}
            }
            
            headers = {
                "Content-Type": "application/json"
            }
            
            print(f"📤 Executando script Puppeteer...")
            
            response = requests.post(
                endpoint,
                json=payload,
                headers=headers,
                timeout=180
            )
            
            print(f"📊 Status Browserless: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    result = response.json()
                    
                    if 'data' in result and 'screenshot' in result['data']:
                        screenshot_b64 = result['data']['screenshot']
                        logged_in = result['data'].get('logged_in', False)
                        
                        print(f"📊 Status Login: {'✅ LOGADO' if logged_in else '❌ NÃO LOGADO'}")
                        
                        if screenshot_b64:
                            screenshot_data = base64.b64decode(screenshot_b64)
                            print(f"✅ Screenshot capturado! ({len(screenshot_data)} bytes = {len(screenshot_data)/1024:.1f} KB)")
                            
                            return screenshot_data, logged_in
                        else:
                            print(f"❌ Screenshot vazio na resposta")
                            return None, False
                    else:
                        print(f"❌ Formato de resposta inesperado")
                        print(f"Resposta: {str(result)[:200]}")
                        return None, False
                        
                except Exception as e:
                    print(f"❌ Erro ao processar resposta JSON: {e}")
                    return None, False
            else:
                print(f"❌ Browserless retornou status {response.status_code}")
                print(f"Resposta: {response.text[:200]}")
                return None, False
                
        except Exception as e:
            print(f"❌ Erro geral: {e}")
            return None, False
    
    def send_to_n8n(self, screenshot_data, logged_in=False):
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
                "version": "v11_puppeteer",
                "logged_in": logged_in,
                "warning": "NOT_LOGGED_IN" if not logged_in else None
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
                
                if not logged_in:
                    print(f"⚠️ AVISO: Screenshot enviado MAS não está logado!")
                    print(f"⚠️ Você precisa obter um TOKEN válido e atualizar!")
                
                return True
            else:
                print(f"⚠️ n8n retornou status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Erro ao enviar para n8n: {e}")
            return False
    
    def run(self):
        """Loop principal do monitor"""
        print(f"\n🚀 Iniciando monitoramento v11...\n")
        
        cycle = 0
        
        while True:
            try:
                cycle += 1
                print(f"\n{'='*70}")
                print(f"🔄 Ciclo #{cycle}")
                print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"{'='*70}")
                
                # Capturar screenshot
                result = self.take_screenshot_with_puppeteer_script()
                
                if result and result[0]:
                    screenshot_data, logged_in = result
                    
                    # Enviar para n8n
                    success = self.send_to_n8n(screenshot_data, logged_in)
                    
                    if success:
                        if logged_in:
                            print(f"\n🎉 Ciclo completo com sucesso! (LOGADO ✅)")
                        else:
                            print(f"\n⚠️ Ciclo completo mas NÃO LOGADO! (Token inválido)")
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
