"""miner_agent.py

Agente autónomo de extracción de cuotas usando browser-use + Gemini Vision.

Flujo:
1. Recibe URL de competición/partido.
2. Usa IA (Gemini Vision) para navegar y entender la estructura.
3. Busca "Crear Apuesta" -> "Jugador" -> "Remates a puerta".
4. Extrae datos estructurados (jugador, línea, cuota) en JSON.

Requisitos:
- google_key.json en la raíz del proyecto.
- pip install browser-use langchain-google-vertexai
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Optional, Any

# ===================== Configuración de Credenciales =====================
# IMPORTANTE: google_key.json debe estar en la raíz del proyecto
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
GOOGLE_KEY_PATH = PROJECT_ROOT / "google_key.json"

if GOOGLE_KEY_PATH.exists():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(GOOGLE_KEY_PATH)
    print(f"[CONFIG] ✓ Credenciales Google Cloud: {GOOGLE_KEY_PATH.name}")
else:
    print(f"[ERROR] google_key.json no encontrado en: {GOOGLE_KEY_PATH}")
    raise FileNotFoundError("Credenciales de Google Cloud requeridas.")

# Imports después de configurar credenciales
import random
import time
from browser_use import Agent, Controller, Browser
from langchain_google_vertexai import ChatVertexAI
from langchain_core.language_models.chat_models import BaseChatModel
from playwright.async_api import async_playwright

# ===================== WRAPPER DE COMPATIBILIDAD =====================
class CompatibleChatVertexAI:
    """
    Wrapper para ChatVertexAI que añade el campo 'provider' requerido por browser-use.
    Delega todas las llamadas al objeto ChatVertexAI original.
    Acepta cualquier atributo que browser-use quiera inyectar.
    """
    def __init__(self, base_llm: ChatVertexAI):
        object.__setattr__(self, '_llm', base_llm)
        object.__setattr__(self, 'provider', 'google')
        
    def __getattr__(self, name):
        """Delegar todos los atributos/métodos al LLM base."""
        if name == 'model_name':
            return self._llm.model_name
        if name == 'model':
            return self._llm.model_name
        return getattr(self._llm, name)
    
    def __setattr__(self, name, value):
        """Permitir que browser-use inyecte métodos tracked sin restricciones."""
        object.__setattr__(self, name, value)


# ===================== Controller (Anti-Bot) =====================
controller = Controller()

@controller.action('Human Delay: Espera 1-3 segundos aleatorios')
async def human_delay():
    """Espera un tiempo aleatorio entre 1 y 3 segundos para simular comportamiento humano."""
    delay = random.uniform(1, 3)
    await asyncio.sleep(delay)
    return f"Esperado {delay:.2f} segundos."

async def get_stealth_scripts() -> str:
    """
    Genera el payload de JavaScript para evasión.
    Técnicas extraídas de repositorios de evasión (puppeteer-extra/selenium-driverless).
    """
    return """
        // 1. Enmascarar WebDriver
        Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        
        // 2. Falsificar WebGL para que no parezca Google SwiftShader (común en headless)
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            if (parameter === 37445) return 'Intel Open Source Technology Center'; // UNMASKED_VENDOR_WEBGL
            if (parameter === 37446) return 'Mesa DRI Intel(R) HD Graphics 630 (Kaby Lake GT2)'; // UNMASKED_RENDERER_WEBGL
            return getParameter(parameter);
        };

        // 3. Mockear Chrome Runtime
        window.chrome = { runtime: {} };

        // 4. Falsificar Permisos (Notification check es común para detectar bots)
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
        );

        // 5. Plugins y Lenguajes
        Object.defineProperty(navigator, 'languages', { get: () => ['es-ES', 'es', 'en-US', 'en'] });
        Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
    """

async def safe_go_to(page, url):
    """Navegación robusta con Playwright puro."""
    try:
        print(f"[NAV] Navegando a {url} con timeout extendido...")
        await page.goto(url, timeout=90000, wait_until='domcontentloaded')
    except Exception as e:
        print(f"[WARN] Timeout o error en carga inicial (posiblemente ignorado): {e}")


# ===================== Configuración =====================
MODEL_NAME = "gemini-1.5-pro-002"  # Modelo estable con visión
HEADLESS = False  # Modo visual para debugging
# =========================================================


async def run_miner(url: str) -> Optional[dict]:
    """
    Ejecuta el agente autónomo de extracción de cuotas.
    
    Args:
        url: URL de la página de competición o partido específico.
        
    Returns:
        Diccionario con datos extraídos o None si falla.
    """
    print(f"\n{'='*70}")
    print(f"  MINER AGENT - Extracción con Gemini Vision")
    print(f"{'='*70}")
    print(f"[TARGET] {url}")
    print(f"[MODEL] {MODEL_NAME}\n")
    
    # Configurar LLM base (Gemini con capacidades de visión vía Vertex AI)
    base_llm = ChatVertexAI(
        model_name=MODEL_NAME,
        temperature=0,
        max_output_tokens=2048,
    )
    
    # Envolver con compatibilidad para browser-use
    llm = CompatibleChatVertexAI(base_llm)
    print(f"[PATCH] ✓ LLM envuelto con compatibilidad browser-use")
    
    # Definir tarea para el agente (MODIFICADA PARA ASUMIR NAVEGACIÓN PREVIA)
    task = f"""
    Estás en la página de apuestas de Bet365. YA HAS NAVEGADO A LA URL.
    Tu objetivo es extraer cuotas de JUGADORES.
    
    IMPORTANTE: Usa la acción 'Human Delay' antes de cada clic o navegación para simular comportamiento humano y evitar detección.
    
    PASOS:
    1. Si aparece un banner de Cookies, acéptalo haciendo clic.
    2. Si estás en una lista de partidos, haz clic en el PRIMER partido disponible.
    3. Una vez dentro del partido, busca la pestaña o menú que diga "Crear apuesta" o "Jugador" (Player). Haz clic.
    4. Busca la sección de "Remates a puerta" (Shots on Target) o "Remates" (Shots).
    5. Extrae toda la información visible en formato JSON:
       - Nombre del jugador
       - Línea (ej: +0.5, +1.5)
       - Cuota ofrecida
    
    FORMATO DE SALIDA JSON:
    {{
      "match": "Equipo A vs Equipo B",
      "market": "Shots on Target",
      "players": [
        {{"name": "Nombre Jugador", "line": "+0.5", "odd": "2.50"}},
        {{"name": "Otro Jugador", "line": "+1.5", "odd": "3.20"}}
      ]
    }}
    
    Si no encuentras la sección de 'Tiros a Puerta', responde: {{"error": "Market not found"}}
    NO inventes datos. Solo extrae lo que veas.
    """
    
    # INICIO DEL FLUJO HÍBRIDO (Playwright Puro + Browser-use)
    async with async_playwright() as p:
        # 1. Lanzar navegador con puerto de depuración remoto para que browser-use se pueda conectar
        print("[INIT] Lanzando navegador Playwright (Chrome Real) con Stealth...")
        try:
            browser_pw = await p.chromium.launch(
                channel="chrome",  # Usar Chrome oficial para mayor sigilo
                headless=HEADLESS,
                args=[
                    "--remote-debugging-port=9222", 
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                    "--no-default-browser-check",
                    "--disable-infobars",
                    "--disable-popup-blocking",
                    "--disable-extensions",
                ]
            )
        except Exception as e:
            print(f"[WARN] No se encontró Chrome, intentando con Edge... ({e})")
            browser_pw = await p.chromium.launch(
                channel="msedge",  # Fallback a Edge
                headless=HEADLESS,
                args=[
                    "--remote-debugging-port=9222", 
                    "--disable-blink-features=AutomationControlled",
                    "--start-maximized",
                    "--no-default-browser-check"
                ]
            )
        
        try:
            # 2. Crear contexto y página con scripts de evasión
            context_pw = await browser_pw.new_context(
                viewport=None,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                locale="es-ES"
            )
            page_pw = await context_pw.new_page()
            
            # Inyectar scripts de evasión
            stealth_js = await get_stealth_scripts()
            await page_pw.add_init_script(stealth_js)
            
            # 3. Navegación Pura (Rescue Navigation)
            await safe_go_to(page_pw, url)
            
            # 4. Espera Humana Forzosa
            print("[WAIT] Espera humana de 15s para carga completa...")
            await asyncio.sleep(15)
            
            # 5. Conectar browser-use al navegador existente vía CDP
            print("[HANDOVER] Conectando Agente AI al navegador...")
            # Browser en browser-use es BrowserSession. Se conecta vía cdp_url.
            browser_use_session = Browser(cdp_url="http://localhost:9222")
            
            # Inicializar agente de browser-use con el navegador conectado
            agent = Agent(
                task=task,
                llm=llm,  # type: ignore
                browser=browser_use_session,
                controller=controller,
            )
            
            # Ejecutar la navegación y extracción (El agente continuará desde donde lo dejó Playwright)
            print("[AGENT] Iniciando control por IA...\n")
            history = await agent.run()
            
            # Extraer resultado del historial
            result = history.final_result() if hasattr(history, 'final_result') else str(history)
            
            print(f"\n[RESULT] Extracción completada.")
            print(f"[RAW OUTPUT]\n{result}\n")
            
            # Intentar parsear como JSON
            try:
                if isinstance(result, str):
                    data = json.loads(result)
                else:
                    # Convertir cualquier tipo a dict serializable
                    data = {"result": str(result), "type": type(result).__name__}
                
                # Guardar resultado
                output_path = PROJECT_ROOT / "data" / "extracted_odds.json"
                output_path.parent.mkdir(exist_ok=True)
                
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                print(f"[SAVED] Datos guardados en: {output_path}")
                return data
                
            except json.JSONDecodeError:
                print("[WARN] La respuesta no es JSON válido. Guardando como texto.")
                output_path = PROJECT_ROOT / "data" / "extracted_odds.txt"
                output_path.parent.mkdir(exist_ok=True)
                
                with open(output_path, "w", encoding="utf-8") as f:
                    f.write(str(result))
                
                return {"raw_output": str(result)}
        
        except Exception as e:
            print(f"\n[ERROR] Fallo en ejecución del agente: {e}")
            import traceback
            traceback.print_exc()
            return None
        finally:
            # Cerrar navegador al finalizar
            if browser_pw:
                await browser_pw.close()


async def main():
    """Punto de entrada CLI del script."""
    # Solicitar URL al usuario
    url = input("\n📍 Introduce la URL del partido o competición:\n> ").strip()
    
    if not url:
        print("[ERROR] URL vacía. Abortando.")
        return
    
    # Ejecutar extracción
    result = await run_miner(url)
    
    # Mostrar resumen
    if result:
        print("\n" + "="*70)
        print("  RESUMEN DE EXTRACCIÓN")
        print("="*70)
        
        if "error" in result:
            print(f"⚠️  {result['error']}")
        elif "players" in result:
            print(f"🏟️  Partido: {result.get('match', 'N/A')}")
            print(f"📊 Mercado: {result.get('market', 'N/A')}")
            print(f"👥 Jugadores extraídos: {len(result['players'])}\n")
            
            for player in result['players'][:5]:  # Mostrar primeros 5
                print(f"  • {player['name']}: {player['line']} @ {player['odd']}")
            
            if len(result['players']) > 5:
                print(f"  ... y {len(result['players']) - 5} más.")
        else:
            print(f"📄 Datos extraídos (ver archivo JSON para detalles)")
    else:
        print("\n❌ No se pudo extraer información.")


if __name__ == "__main__":
    asyncio.run(main())
