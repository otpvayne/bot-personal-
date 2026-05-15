# Bot de Telegram — Productividad & Finanzas

Bot personal para gestión de tareas y control de finanzas personales. Corre 24/7 en Railway y persiste todos los datos en Firebase Realtime Database.

---

## Funcionalidades

| Módulo | Comandos |
|--------|----------|
| **Tareas** | `/tarea`, `/newtask`, `/tareas`, `/completar`, `/eliminar` |
| **Gastos** | `/gasto`, `/newgasto` |
| **Ingresos** | `/ingreso`, `/newingreso` |
| **Consultas** | `/balance`, `/historial`, `/mes`, `/categoria`, `/reporte` |

---

## Instalación local

### 1. Prerrequisitos

- Python 3.9+
- Cuenta de Firebase (plan Spark gratuito)
- Token de bot de Telegram ([@BotFather](https://t.me/BotFather))

### 2. Clonar y configurar

```bash
cd telegram_bot
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tus credenciales
```

### 3. Credenciales de Firebase

1. Ir a [Firebase Console](https://console.firebase.google.com)
2. Crear proyecto → Realtime Database → Crear base de datos (modo producción)
3. Project Settings → Service Accounts → **Generate new private key**
4. Guardar el JSON descargado como `serviceAccountKey.json` en esta carpeta
5. En `.env`, apuntar `FIREBASE_CREDENTIALS_PATH=./serviceAccountKey.json`

### 4. Ejecutar

```bash
python main.py
```

---

## Despliegue en Railway

### Opción A: desde GitHub

1. Subir el repositorio a GitHub
2. En [Railway](https://railway.app): **New Project → Deploy from GitHub repo**
3. Seleccionar el repositorio
4. En **Settings → Root Directory**: escribir `telegram_bot`
5. En **Variables**, agregar:
   - `TELEGRAM_BOT_TOKEN`
   - `FIREBASE_DB_URL`
   - `FIREBASE_CREDENTIALS_JSON` ← contenido del JSON en una sola línea
6. Railway detecta el `Procfile` y arranca el worker

### Opción B: Railway CLI

```bash
cd telegram_bot
railway login
railway init
railway up
```

### Variables de entorno en Railway

| Variable | Descripción |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Token del bot |
| `FIREBASE_DB_URL` | URL de la Realtime Database |
| `FIREBASE_CREDENTIALS_JSON` | Contenido del serviceAccountKey.json (una línea) |
| `ENVIRONMENT` | `production` |
| `LOG_LEVEL` | `INFO` |

**Cómo convertir el JSON a una línea:**

```bash
python -c "import json,sys; print(json.dumps(json.load(open('serviceAccountKey.json'))))"
```

---

## Estructura del proyecto

```
telegram_bot/
├── main.py                 # Punto de entrada
├── config.py               # Variables de entorno
├── Procfile                # Para Railway
├── requirements.txt
├── .env.example
│
├── handlers/
│   ├── start.py            # /start, /ayuda
│   ├── tareas.py           # Gestión de tareas
│   ├── finanzas.py         # Gastos e ingresos
│   └── consultas.py        # Balance, historial, reportes
│
├── database/
│   ├── firebase_manager.py # Acceso a Firebase
│   ├── models.py           # Modelos Tarea y Transaccion
│   └── utils.py            # Singleton y rate limiting
│
└── utils/
    ├── constants.py        # Categorías, prioridades, estados
    ├── validators.py       # Validación de entrada
    └── formatters.py       # Formateo de mensajes
```

---

## Seguridad

- El bot solo acepta mensajes de **chats privados**
- Rate limiting: máximo 10 comandos cada 10 segundos por usuario
- Token y credenciales siempre en variables de entorno, nunca en código
- `serviceAccountKey.json` y `.env` ignorados por git

---

## Pruebas rápidas

```
/start
/tarea Enviar propuesta
/newtask
/tareas
/tareas hoy
/gasto 15000 almuerzo
/newgasto
/ingreso 500000
/balance
/historial
/mes actual
/categoria
/reporte
/completar <ID>
/eliminar <ID>
```
