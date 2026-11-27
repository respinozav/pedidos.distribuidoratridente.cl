import urllib.request
import json
import base64
import io
from PIL import Image

url = 'https://pedidos.distribuidoratridente.cl/api/productos?page=1&page_size=1000'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode('utf-8'))

items = data.get('items', [])
print(f'Total productos en Produccion: {len(items)}')
with_img = [p for p in items if p.get('imagen_url') and len(p.get('imagen_url', '')) > 100]
print(f'Total productos con imagen: {len(with_img)}')

sample_codes = ['3', '50', '711', '760', '764', '770', '778']
for code in sample_codes:
    p = next((x for x in items if str(x.get('codigo')) == code), None)
    if p:
        img_b64 = p.get('imagen_url')
        nombre = p.get('nombre', '')[:25]
        if img_b64 and len(img_b64) > 100:
            if 'base64,' in img_b64:
                raw_b64 = img_b64.split('base64,')[1]
            else:
                raw_b64 = img_b64
            raw = base64.b64decode(raw_b64)
            im = Image.open(io.BytesIO(raw))
            tl = im.getpixel((5, 5))[:3]
            print(f'Cod {code:5} | {nombre:25} | Dim: {im.size} | Tam: {len(raw):5}B | Pixel(5,5): {tl}')
        else:
            print(f'Cod {code:5} | {nombre:25} | Sin imagen')
