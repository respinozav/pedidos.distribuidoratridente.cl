import asyncio
import base64
import io
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageDraw

app = FastAPI(title="Mock Evolution API (Local Simulator)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Estado de la instancia simulada
instances_state: dict[str, str] = {}


def generate_qr_image_base64() -> str:
    """Genera una imagen PNG simulada de código QR en base64 usando Pillow."""
    img = Image.new("RGB", (260, 260), color="white")
    draw = ImageDraw.Draw(img)

    # Marco exterior
    draw.rectangle([10, 10, 250, 250], outline="black", width=4)

    # Patrón de esquinas (Finders)
    def draw_finder(x, y):
        draw.rectangle([x, y, x + 50, y + 50], fill="black")
        draw.rectangle([x + 10, y + 10, x + 40, y + 40], fill="white")
        draw.rectangle([x + 20, y + 20, x + 30, y + 30], fill="black")

    draw_finder(25, 25)
    draw_finder(185, 25)
    draw_finder(25, 185)

    # Patrones internos decorativos
    import random
    random.seed(42)
    for row in range(5, 21):
        for col in range(5, 21):
            if (row < 9 and col < 9) or (row < 9 and col > 16) or (row > 16 and col < 9):
                continue
            if random.random() > 0.45:
                x = 25 + col * 10
                y = 25 + row * 10
                draw.rectangle([x, y, x + 8, y + 8], fill="black")

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    raw_b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{raw_b64}"


@app.get("/instance/connectionState/{instance_name}")
async def get_connection_state(instance_name: str):
    state = instances_state.get(instance_name, "DISCONNECTED")
    return {"instance": {"instanceName": instance_name, "state": state}}


@app.post("/instance/create")
async def create_instance(payload: dict):
    name = payload.get("instanceName", "tridente_ws")
    if name not in instances_state:
        instances_state[name] = "DISCONNECTED"
    return {"instance": {"instanceName": name, "state": instances_state[name]}}


@app.get("/instance/connect/{instance_name}")
async def connect_instance(instance_name: str):
    current = instances_state.get(instance_name, "DISCONNECTED")
    if current == "open":
        return {"instance": {"instanceName": instance_name, "state": "open"}}

    qr_b64 = generate_qr_image_base64()
    instances_state[instance_name] = "connecting"

    # Simular que el usuario escanea el QR después de 6 segundos
    async def simulate_scan():
        await asyncio.sleep(6)
        instances_state[instance_name] = "open"
        print(f"[MOCK EVOLUTION API] ¡Instancia '{instance_name}' conectada exitosamente (QR escaneado)!")

    asyncio.create_task(simulate_scan())

    return {
        "base64": qr_b64,
        "instance": {"instanceName": instance_name, "state": "connecting"},
    }


@app.post("/message/sendText/{instance_name}")
async def send_text(instance_name: str, payload: dict):
    number = payload.get("number")
    text = payload.get("text")
    print(f"[MOCK EVOLUTION API] Mensaje enviado a {number}: {text}")
    return {"status": "SUCCESS", "message": "Mensaje simulado enviado"}


if __name__ == "__main__":
    import uvicorn
    print("\n--- MOCK EVOLUTION API corriendo en http://localhost:8080 ---\n")
    uvicorn.run(app, host="127.0.0.1", port=8080)
