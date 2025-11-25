# 🤖 Bot de Apuestas de Valor

Sistema automatizado de extracción y análisis de cuotas deportivas usando IA (Gemini Vision) y web automation.

## 📋 Estructura del Proyecto

```
bot-bet/
├── src/bot_bet/
│   ├── automation/        # Scripts de navegación web
│   │   ├── visual_navigator.py   # Navegación determinística con Playwright
│   │   └── miner_agent.py         # Navegación autónoma con IA
│   ├── analysis/          # Lógica de cálculos de apuestas
│   │   └── logic.py               # Arbitraje, EV, Kelly
│   ├── database/          # Persistencia de datos
│   │   └── setup_db.py            # Schema SQLite
│   └── scrapers/          # (Futuro) Scrapers específicos por casa
├── data/                  # Datos extraídos (JSON, CSV)
├── logs/                  # Logs de ejecución
├── .venv/                 # Entorno virtual Python
└── requirements.txt       # Dependencias
```

## 🔧 Instalación

### 1. Clonar el repositorio

```powershell
git clone https://github.com/jdejose777/bot-bet.git
cd bot-bet
```

### 2. Configurar entorno virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 3. Instalar dependencias

```powershell
pip install -r requirements.txt
playwright install chromium
```

### 4. **IMPORTANTE: Configurar credenciales de Google Cloud**

#### Opción A: Ubicación segura (recomendado para producción)
```powershell
# Mover google_key.json UN NIVEL ARRIBA del repositorio
Move-Item google_key.json ..\google_key.json
```

Estructura resultante:
```
carpeta-padre/
├── google_key.json    ← FUERA del repositorio (no se versiona)
└── bot-bet/           ← Repositorio git
    ├── src/
    └── ...
```

#### Opción B: Desarrollo local
```powershell
# Dejar google_key.json en la raíz del proyecto
# ⚠️ NUNCA hacer commit de este archivo
```

El script `miner_agent.py` buscará automáticamente en ambas ubicaciones.

## 🚀 Uso

### Navegación Visual (Determinística)

```powershell
python .\src\bot_bet\automation\visual_navigator.py
```

### Minería con IA (Gemini Vision)

```powershell
python .\src\bot_bet\automation\miner_agent.py
```

**Ejemplo de uso:**
1. Ejecutar el script
2. Pegar URL de competición (ej: Champions League en Bet365)
3. El agente navegará automáticamente y extraerá cuotas de "Tiros a Puerta"
4. Resultados guardados en `data/extracted_odds.json`

## 📊 Capacidades Actuales

### ✅ Implementado
- ✓ Base de datos SQLite con schema de partidos y cuotas
- ✓ Navegación web stealth con Playwright (evasión de detección)
- ✓ Navegación autónoma con IA usando Gemini Vision
- ✓ Cálculos de arbitraje, Expected Value y Kelly Criterion
- ✓ Extracción de cuotas de jugadores (Player Props)

### 🚧 En Desarrollo
- ⏳ Integración entre extracción y base de datos
- ⏳ Sistema de logging estructurado
- ⏳ Análisis estadístico de cuotas históricas
- ⏳ Dashboard de visualización

## 🔐 Seguridad

### Archivos protegidos por `.gitignore`:
- `google_key.json` - Credenciales de Google Cloud
- `.env` - Variables de entorno
- `.venv/` - Entorno virtual
- `data/` - Datos extraídos (opcional)
- `*.log` - Logs de ejecución

### ⚠️ NUNCA commitear:
- Credenciales de APIs
- Contraseñas de casas de apuestas
- Datos personales o financieros

## 📚 Documentación Técnica

### Modelos de IA Utilizados
- **Gemini 1.5 Pro Preview 0409**: Modelo multimodal con capacidades de visión para navegación autónoma

### Técnicas de Stealth
- Mascara de `navigator.webdriver`
- Falsificación de WebGL vendor/renderer
- Mocking de `navigator.permissions`
- Headers de navegador reales

### Cálculos Matemáticos
- **Margen de Arbitraje**: `1 - (1/odd1 + 1/odd2 + ... + 1/oddN)`
- **Expected Value (EV)**: `(odd * true_prob) - 1`
- **Kelly Criterion**: `(bp - q) / b` donde b=odd-1, p=prob, q=1-p

## 🤝 Contribuir

1. Fork del repositorio
2. Crear branch: `git checkout -b feature/nueva-funcionalidad`
3. Commit: `git commit -am 'Añadir nueva funcionalidad'`
4. Push: `git push origin feature/nueva-funcionalidad`
5. Pull Request

## ⚖️ Disclaimer Legal

Este software es **solo para fines educativos**. 

- NO promueve el juego compulsivo
- El usuario es responsable del cumplimiento de leyes locales
- Las casas de apuestas pueden prohibir el uso de bots
- Úsalo bajo tu propio riesgo

## 📧 Contacto

GitHub: [@jdejose777](https://github.com/jdejose777)

---

**Hecho con 🧠 y Python**
