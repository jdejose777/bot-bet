"""miner_agent.py

Agente autónomo de extracción de cuotas usando browser-use + Gemini Vision.

Flujo:
1. Recibe URL de competición/partido.
2. Usa IA (Gemini Vision) para navegar y entender la estructura.
3. Busca "Crear Apuesta" -> "Jugador" -> "Remates a puerta".
4. Extrae datos estructurados (jugador, línea, cuota) en JSON.

Requisitos:
- google_key.json en directorio padre del repositorio (fuera de git).
- pip install browser-use langchain-google-vertexai
"""
from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Optional

# ===================== Configuración de Credenciales =====================
# IMPORTANTE: google_key.json debe estar FUERA del repositorio por seguridad
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
GOOGLE_KEY_PATH = PROJECT_ROOT.parent / "google_key.json"  # Un nivel arriba del repo

# Fallback para desarrollo local
if not GOOGLE_KEY_PATH.exists():
    GOOGLE_KEY_PATH = PROJECT_ROOT / "google_key.json"

if GOOGLE_KEY_PATH.exists():
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(GOOGLE_KEY_PATH)
    print(f"[CONFIG] ✓ Credenciales Google Cloud: {GOOGLE_KEY_PATH.name}")
else:
    print(f"[ERROR] google_key.json no encontrado.")
    print(f"[INFO] Coloca el archivo en: {PROJECT_ROOT.parent}")
    raise FileNotFoundError("Credenciales de Google Cloud requeridas.")

# Imports después de configurar credenciales
from browser_use import Agent
from langchain_google_vertexai import ChatVertexAI

# ===================== Configuración =====================
MODEL_NAME = "gemini-1.5-pro-preview-0409"  # Modelo multimodal con visión
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
    
    # Configurar LLM (Gemini con capacidades de visión)
    llm = ChatVertexAI(
        model_name=MODEL_NAME,
        temperature=0.1,  # Respuestas deterministas
        max_tokens=2048,
    )
    
    # Definir tarea para el agente
    task = """
    Tu objetivo es extraer cuotas de jugadores (Player Props) para 'Tiros a Puerta' (Shots on Target).
    
    Pasos:
    1. Si estás en una lista de partidos, entra en el PRIMER partido visible.
    2. Busca y haz clic en la pestaña 'Crear Apuesta', 'Jugador' o 'Player'.
    3. Localiza la sección 'Tiros a Puerta', 'Shots on Target' o 'Remates'.
    4. Extrae la información de TODOS los jugadores visibles:
       - Nombre del jugador
       - Línea (ej: +0.5, +1.5)
       - Cuota ofrecida
    
    IMPORTANTE: Devuelve un JSON con este formato exacto:
    {
      "match": "Equipo A vs Equipo B",
      "market": "Shots on Target",
      "players": [
        {"name": "Nombre Jugador", "line": "+0.5", "odd": "2.50"},
        {"name": "Otro Jugador", "line": "+1.5", "odd": "3.20"}
      ]
    }
    
    Si no encuentras la sección de 'Tiros a Puerta', responde: {"error": "Market not found"}
    """
    
    try:
        # Inicializar agente de browser-use
        agent = Agent(
            task=task,
            llm=llm,
            headless=HEADLESS,
        )
        
        # Ejecutar la navegación y extracción
        print("[AGENT] Iniciando navegación autónoma...\n")
        result = await agent.run(url)
        
        print(f"\n[RESULT] Extracción completada.")
        print(f"[RAW OUTPUT]\n{result}\n")
        
        # Intentar parsear como JSON
        try:
            if isinstance(result, str):
                data = json.loads(result)
            else:
                data = result
            
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
