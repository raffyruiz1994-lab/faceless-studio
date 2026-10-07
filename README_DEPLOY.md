# Faceless Studio — despliegue en tu VM

## Qué es
App web auto-hospedada que produce documentales faceless cinematográficos:
tema → guion (Gemini) → imágenes cinematográficas (Nano Banana 2) →
narración (Fish Audio) → ensamblaje local (Ken Burns + subtítulos karaoke modernos
+ música ambiental) → MP4 listo + checklist de revisión humana.

## Requisitos de la VM
- Docker + Docker Compose (o Python 3.12 + ffmpeg como alternativa)
- ~2 GB RAM libres para renderizar (4+ recomendado), unos GB de disco para videos

## Instalación (Docker, recomendado)

```bash
# 1. Clona el repo en tu VM:
git clone https://github.com/TU-USUARIO/faceless-studio.git
cd faceless-studio

# 2. Levanta la app:
docker compose up -d --build

# 3. Abre en tu navegador (desde cualquier dispositivo de tu red local):
http://IP-DE-TU-VM:8000
```

Listo. La primera pantalla es la app: configura tus API keys en **Ajustes** y
genera tu primer video. Los trabajos, videos y ajustes persisten en `./jobs` y
`./settings.json` aunque reinicies el contenedor.

## Cómo hallar la IP local de tu VM
En la VM, ejecuta uno de estos comandos y usa la dirección que empiece por
`192.168.x.x`, `10.x.x.x` o `172.16.x.x`:

```bash
hostname -I
# o
ip -4 addr show | grep inet
```

Ejemplo: si ves `192.168.1.50`, la app queda en `http://192.168.1.50:8000`.
Tu teléfono o PC deben estar conectados a la misma red Wi-Fi.

## Si no carga: abre el puerto 8000 en el firewall de la VM
```bash
# Ubuntu/Debian con ufw:
sudo ufw allow 8000/tcp

# O con firewalld:
sudo firewall-cmd --permanent --add-port=8000/tcp && sudo firewall-cmd --reload
```
No necesitas abrir nada en el router: todo queda dentro de tu red local.

## Conseguir las API keys
- **Gemini** (guion + imágenes Nano Banana): Google AI Studio → crea una API key
  con facturación activada. Modelos usados: `gemini-2.5-flash` (texto),
  `gemini-3.1-flash-image-preview` (~$0.067/imagen) o `gemini-3-pro-image-preview`
  ($0.134/imagen, mejor calidad).
- **Fish Audio** (narración): fish.audio → API keys. El **Voice ID** está en la
  biblioteca de voces o en tus voces clonadas (campo `reference_id`). Si lo dejas
  vacío se usa la voz por defecto de Fish.

## Seguridad
- `settings.json` guarda tus keys con permisos 600 y nunca se exponen en la API.
- La app está pensada para tu red local solamente: no la expongas a internet
  (no abras el puerto 8000 en tu router).
## Alternativa sin Docker (systemd)
```bash
sudo apt install -y python3-venv ffmpeg fonts-dejavu
cd faceless-studio
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
sudo cp deploy/faceless-studio.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now faceless-studio
# disponible en http://IP-DE-TU-VM:8000 desde tu red local
```

## Costos estimados (a 2026)
- Video de 16 min ≈ 28 imágenes × $0.067 + ~14K caracteres de voz ≈ **$2.10**
- La demo local ("Probar sin APIs") cuesta $0.
