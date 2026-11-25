# Estándar de Imágenes de Productos y Fondo de Estudio

Distribuidora Tridente - Documentación Técnica y Guía de Ejecución

Este documento describe la arquitectura, algoritmos, reglas de segmentación y comandos para aplicar y mantener el fondo de estudio celeste degradado institucional en todas las imágenes de productos de la Distribuidora Tridente.

---

## 1. Objetivo y Estándar Visual

- **Referencia Canónica:** Código 762 (`Bolsas Kraft`).
- **Fondo:** Degradado vertical continuo de estudio:
  - Superior: `#4991AA` (Cyan oscuro de estudio).
  - Inferior: `#B2D6E6` (Cyan claro suave de piso).
- **Proporción y Dimensiones:**
  - Resolución: `900 x 900 px` (cuadrado 1:1).
  - Ocupación del producto: ~`80%` del canvas vertical/horizontal.
- **Restricciones de Calidad:**
  - **Cero blanco perimetral:** Ni esquinas, ni marcos, ni lienzos embebidos pueden tener blanco (`RGB > 240`).
  - **Preservación total de elementos internos:** Letras blancas (e.g. *Trencito*, *Costa*, *Alka*), envases blancos (e.g. *Kent 10*, *Marlboro 62*), poliestireno y vasos desechables deben conservar su blanco 100% opaco y sólido.
  - **Sin sombras falsas:** No se permiten rectángulos u óvalos oscuros artificiales pegados bajo los productos.
  - **Límite de Peso:** Binario JPEG $\le 72.000$ bytes ($< 100$ KB en Base64) para máxima velocidad de carga en la aplicación móvil y web.

---

## 2. Arquitectura del Algoritmo

El script principal se encuentra en:
```
scripts/aplicar_fondo_estudio_qa.py
```

### Componentes Clave:

1. **Extracción del Perfil de Fondo (`extract_bg_profile`):**
   Muestrea las columnas laterales libres de producto en la imagen de referencia (`scripts/referencia_fondo.jpg`) para construir la columna vertical de color exacta (`bg_profile`).

2. **Generación del Canvas (`create_studio_bg`):**
   Interpola linealmente el perfil extraído y lo proyecta horizontalmente mediante `np.tile`, garantizando un degradado suave sin artefactos de compresión.

3. **Segmentación y Envolvente Span-Hull (`process_product_image`):**
   - **Detección de Semilla de Fondo:**
     - Zonas neutras brillantes (`color_diff < 16 & brightness > 175` o `brightness > 248`) se marcan como fondo/sombra de mesa.
   - **Envolvente Convexa por Filas y Columnas (Span-Hull):**
     - Para cada fila horizontal $y \in [y_{min}, y_{max}]$, se llena todo el espacio entre el píxel con tinta más a la izquierda y el más a la derecha (`row_xs.min():row_xs.max()+1`).
     - Para cada columna vertical $x \in [x_{min}, x_{max}]$, se llena desde el primer píxel superior hasta el inferior.
     - Se toma la intersección lógica (`span_mask & col_mask`) y se aplica `ndimage.binary_fill_holes`.
     - **Efecto:** Cualquier elemento blanco interno (letras, marcas, tapas blancas) queda 100% blindado dentro del producto sin ser mordido por el fondo celeste.

4. **Tratamiento de Productos Especiales / Curados (`scripts/assets_estudio/`):**
   - **Bolsas Kraft (`760, 761, 762, 763`):** Reciben la imagen de referencia original directamente optimizada.
   - **Desechables (`764` a `778`):** Contenedores térmicos de plumavit, vasos de polipapel, pinchos de bambú y bolsas taco poseen renders fotográficos hiperrealistas en `scripts/assets_estudio/` para evitar que materiales translúcidos o poliestireno puro se confundan con fondos de mesa.
   - **Paquetes con Cabezal Blanco (`10, 60, 62, 76, 81, etc.`):** Paquetes de cigarrillos con cabezal 100% blanco cuentan con su asset ajustado y verificado.

5. **Compresión Adaptativa (`compress_to_limit`):**
   Itera reduciendo el factor de calidad JPEG (de 88 a 35) hasta alcanzar $\le 72.000$ bytes, optimizando los árboles de Huffman. Si el peso supera el límite, escala suavemente al 88% conservando la nitidez mediante filtro Lanczos.

---

## 3. Modo de Uso y Comandos

### Ejecución en Entorno QA (Catálogo Completo)
```bash
python scripts/aplicar_fondo_estudio_qa.py --pause 0.02
```

### Ejecución en Modo Simulación (Dry-Run, sin modificar base de datos)
```bash
python scripts/aplicar_fondo_estudio_qa.py --dry-run
```

### Actualizar Productos Específicos por Código
```bash
python scripts/aplicar_fondo_estudio_qa.py --codes 764,765,766,767,768,769 --pause 0.05
```

### Ejecución contra otro entorno (ej. Producción / Local)
```bash
python scripts/aplicar_fondo_estudio_qa.py --base-url https://pedidos.distribuidoratridente.cl
```

---

## 4. Estructura de Archivos

```
scripts/
├── aplicar_fondo_estudio_qa.py   # Script ejecutable principal
├── referencia_fondo.jpg           # Imagen canónica estándar (Código 762)
├── README_ESTANDAR_FONDOS.md     # Este manual de referencia
└── assets_estudio/               # 35 packshots curados de alta fidelidad
    ├── 10_final.jpg              # Kent 10
    ├── 62_final.jpg              # Marlboro 62
    ├── 764_final.jpg             # Bolsa Taco
    ├── 765_final.jpg             # Vaso Transparente 300 cc
    ├── 766_final.jpg             # Vaso Transparente 500 ml
    ├── 767_final.jpg             # Vaso Polipapel Blanco
    ├── 768_final.jpg             # Vaso Polipapel Diseño
    ├── 769_final.jpg             # Vaso Polipapel Kraft
    ├── 770_final.jpg             # Pincho Bambú 9 cm
    ├── 771_final.jpg             # Pincho Bambú 12 cm
    ├── 772_final.jpg             # Pincho Bambú 15 cm
    ├── 773_final.jpg             # Revolvedor Madera
    ├── 774_final.jpg             # Portacomidas sin división
    ├── 775_final.jpg             # Portacomidas con división
    ├── 776_final.jpg             # Marmita Plumavit
    ├── 777_final.jpg             # Marmita Bajo Plumavit
    ├── 778_final.jpg             # Portasándwich Plumavit
    └── ... (demás códigos sensibles verificados)
```
