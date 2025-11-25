"""visual_navigator

Sistema de navegación visual robusto con técnicas avanzadas de evasión (Stealth)
y recuperación de errores (Self-Healing).

Mejoras implementadas (Refactorización):
- Inyección de scripts de evasión profunda (WebGL, Permissions, Chrome Runtime).
- Lógica de 'Smart Click': Reintento con scroll automático si falla la interacción.
- Estructura modular para facilitar el mantenimiento.
"""
from __future__ import annotations

import asyncio
import random
from typing import Iterable, Optional, Any

from playwright.async_api import (
    Browser, 
    BrowserContext, 
    Page, 
    async_playwright, 
    TimeoutError as PWTimeoutError,
    Locator
)

# ===================== Configurables =====================
URL: str = "https://m.apuestas.codere.es/deportesEs/#/HomePage"
USER_AGENT: str = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
# Tiempos para simulación humana
ACTION_MIN_WAIT: float = 1.5
ACTION_MAX_WAIT: float = 3.5
TYPE_MIN_DELAY: float = 0.05
TYPE_MAX_DELAY: float = 0.15

SEARCH_QUERY: str = "Levante"

# Diccionarios de selectores flexibles
SELECTORS = {
    "cookies": ["Aceptar", "Accept", "Allow all", "OK", "Acepto", "Allow", "Aceptar cookies"],
    "search_trigger": ["Buscar", "Search", "Búsqueda", "Buscar eventos"],
    "bet_builder": ["Bet Builder", "Crear Apuesta", "Tiros"],
    "player_section": ["Player", "Jugador"],
    "shots_target": ["Tiros a puerta", "Shots on Target", "Tiros a portería"]
}
# =========================================================

def _rand_wait() -> float:
    return random.uniform(ACTION_MIN_WAIT, ACTION_MAX_WAIT)

async def human_pause(label: str | None = None) -> None:
    """Espera aleatoria simulando proceso cognitivo humano."""
    delay = _rand_wait()
    if label:
        print(f"[HUMAN] Pausa '{label}' ~{delay:.2f}s")
    await asyncio.sleep(delay)

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

async def launch_browser(pw: Any) -> tuple[Browser, BrowserContext, Page]:
    """Lanza navegador con configuración de evasión robusta."""
    browser = await pw.chromium.launch(
        headless=False, # Cambiar a True en producción si se desea, pero aumenta riesgo de detección
        args=[
            "--start-maximized",
            "--disable-blink-features=AutomationControlled",
            "--no-default-browser-check",
            "--disable-infobars",
            "--disable-extensions",
            "--disable-popup-blocking",
        ],
    )
    
    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport=None,
        locale="es-ES",
        timezone_id="Europe/Madrid",
        has_touch=True, # Importante para emulación móvil/tablet si aplica
    )
    
    page = await context.new_page()
    
    # Inyectar scripts de evasión antes de que cargue cualquier página
    stealth_js = await get_stealth_scripts()
    await page.add_init_script(stealth_js)
    
    return browser, context, page

async def smart_click(page: Page, locator: Locator, label: str) -> bool:
    """
    Intenta hacer clic de forma robusta (Inspirado en browser-use).
    Si falla, hace un pequeño scroll y reintenta.
    """
    try:
        # Movimiento humano previo
        box = await locator.bounding_box()
        if box:
            # Mover al centro con variabilidad
            x = box["x"] + box["width"] / 2 + random.uniform(-5, 5)
            y = box["y"] + box["height"] / 2 + random.uniform(-5, 5)
            await page.mouse.move(x, y, steps=random.randint(10, 20))
        
        await asyncio.sleep(random.uniform(0.2, 0.5))
        await locator.click()
        return True
        
    except Exception as e:
        print(f"[RETRY] Falló clic en '{label}'. Intentando recuperación (Scroll + Retry). Error: {str(e)[:50]}...")
        
        # Estrategia de recuperación: Scroll aleatorio
        scroll_amount = random.choice([-200, 200])
        await page.mouse.wheel(0, scroll_amount)
        await asyncio.sleep(1.0)
        
        try:
            # Reintento forzado
            await locator.click(force=True, timeout=2000)
            print(f"[RETRY] Recuperación exitosa para '{label}'.")
            return True
        except Exception:
            print(f"[FAIL] No se pudo recuperar el clic en '{label}'.")
            return False

async def safe_find_text(page: Page, texts: Iterable[str], timeout: int = 3000) -> Optional[Locator]:
    """Busca elementos por texto flexible."""
    for t in texts:
        try:
            # Usamos 'get_by_text' o 'get_by_role' según convenga, aquí genérico
            el = page.get_by_text(t, exact=False)
            if await el.count() > 0 and await el.first.is_visible():
                return el.first
        except:
            continue
    return None

# ===================== Flujo de Negocio =====================

async def accept_cookies(page: Page) -> None:
    await human_pause("check cookies")
    # Intentar buscar botón por rol primero (más accesible/robusto)
    for text in SELECTORS["cookies"]:
        try:
            btn = page.get_by_role("button", name=text, exact=True)
            if await btn.count() > 0 and await btn.first.is_visible():
                print(f"[STEP] Cookies encontradas: {text}")
                await smart_click(page, btn.first, "cookies")
                return
        except: pass
    print("[INFO] No se detectó banner de cookies.")

async def perform_search(page: Page) -> None:
    await human_pause("pre search")
    
    # 1. Encontrar trigger
    trigger = await safe_find_text(page, SELECTORS["search_trigger"])
    if not trigger:
        # Fallback a selectores CSS comunes
        css_triggers = ["button[aria-label*='Buscar']", ".search-button", "ion-icon[name='search']"]
        for sel in css_triggers:
            l = page.locator(sel).first
            if await l.is_visible():
                trigger = l
                break
    
    if trigger:
        await smart_click(page, trigger, "search_trigger")
        await human_pause("wait input")
        
        # 2. Interactuar con Input
        try:
            inp = page.locator("input[type='search'], input.searchbar-input").first
            await inp.wait_for(state="visible", timeout=4000)
            await inp.click()
            
            # Tecleo humano simulado
            for char in SEARCH_QUERY:
                await page.keyboard.type(char)
                await asyncio.sleep(random.uniform(TYPE_MIN_DELAY, TYPE_MAX_DELAY))
            
            await page.keyboard.press("Enter")
            print(f"[STEP] Búsqueda lanzada: {SEARCH_QUERY}")
            
            # 3. Seleccionar resultado
            res = await safe_find_text(page, [SEARCH_QUERY], timeout=5000)
            if res:
                await human_pause("found result")
                await smart_click(page, res, "search_result")
            else:
                print("[WARN] No se encontraron resultados en la lista.")
                
        except Exception as e:
            print(f"[ERROR] Fallo en flujo de input búsqueda: {e}")
            await page.screenshot(path="error_search_input.png")
    else:
        print("[WARN] No se encontró botón de búsqueda.")

async def navigate_match_tabs(page: Page) -> None:
    """Navega por las pestañas internas del partido (Bet Builder -> Player)."""
    # Bet Builder
    bb = await safe_find_text(page, SELECTORS["bet_builder"], timeout=5000)
    if bb:
        await smart_click(page, bb, "bet_builder_tab")
        await human_pause("tab switch")
    
    # Player Section
    ps = await safe_find_text(page, SELECTORS["player_section"], timeout=5000)
    if ps:
        await smart_click(page, ps, "player_section_tab")
        await human_pause("section load")

async def verify_market(page: Page) -> None:
    """Verifica visualmente si existe el mercado objetivo."""
    target = await safe_find_text(page, SELECTORS["shots_target"], timeout=4000)
    if target:
        print(f"[SUCCESS] Mercado '{SELECTORS['shots_target'][0]}' LOCALIZADO.")
        # Aquí se llamaría a la lógica de extracción (OCR o texto)
    else:
        print("[INFO] Mercado objetivo no disponible en este evento.")

async def run_flow() -> None:
    async with async_playwright() as pw:
        browser = None
        try:
            browser, context, page = await launch_browser(pw)
            print(f"[BOT] Iniciando navegación Stealth a {URL}")
            
            try:
                await page.goto(URL, wait_until="domcontentloaded", timeout=60000)
            except PWTimeoutError:
                print("[WARN] Timeout en carga inicial, intentando continuar...")

            await accept_cookies(page)
            await perform_search(page)
            await navigate_match_tabs(page)
            await verify_market(page)
            
            print("[BOT] Sesión finalizada correctamente.")
            
        except Exception as e:
            print(f"[CRITICAL] Error no controlado: {e}")
        finally:
            if browser:
                await browser.close()

if __name__ == "__main__":
    asyncio.run(run_flow())