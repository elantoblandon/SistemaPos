import os
import re
import pdfplumber

try:
    import pytesseract
    from PIL import Image

    TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

    if os.path.exists(TESSERACT_PATH):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

    OCR_DISPONIBLE = True
except Exception:
    OCR_DISPONIBLE = False

try:
    import cv2
    import numpy as np
    OPENCV_DISPONIBLE = True
except Exception:
    OPENCV_DISPONIBLE = False


PALABRAS_PROHIBIDAS = [
    "AUTORIZACION", "AUTORIZACIÓN", "NUMERACION", "NUMERACIÓN", "FACTURACION", "FACTURACIÓN",
    "CUFE", "FIRMA", "GENERADO", "SOFTWARE", "REPRESENTACION", "REPRESENTACIÓN",
    "ELECTRONICA", "ELECTRÓNICA", "IVA", "TOTAL", "SUBTOTAL", "RETENCION", "RETENCIONES",
    "CLIENTE", "DIRECCION", "DIRECCIÓN", "NIT", "FECHA", "PAGO", "VALOR", "BASE",
    "TARIFA", "IMPUESTO", "DESCUENTO", "TELEFONO", "TELÉFONO", "EMAIL", "CORREO",
    "CIUDAD", "VENDEDOR", "VEND", "MEDIO", "EFECTIVO", "HABIL", "HÁBIL", "HASTA",
    "DESDE", "VIGENCIA", "REGIMEN", "RÉGIMEN", "RESPONSABLE", "PARCIAL",
]

PALABRAS_BASURA_NOMBRE = [
    "CANT", "CANT.", "PRECIO", "TOTAL", "IVA", "NIT", "FACTURA", "CLIENTE",
    "DIRECCION", "DIRECCIÓN", "FECHA", "VALOR", "REFERENCIA", "NOMBRE"
]


def process_invoice(file_path):
    """Extrae productos desde PDF o imagen y devuelve lista de diccionarios."""
    file_path_lower = file_path.lower()
    products = []

    if file_path_lower.endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    products.extend(extract_products_from_text(text))

    elif file_path_lower.endswith((".png", ".jpg", ".jpeg")):
        if not OCR_DISPONIBLE:
            raise Exception("Para leer imágenes debe instalar Tesseract OCR.")

        text = extraer_texto_imagen(file_path)
        products.extend(extract_products_from_text(text))

    else:
        raise Exception("Formato no soportado. Use PDF, PNG, JPG o JPEG.")

    return products


def extraer_texto_imagen(file_path):
    """Lee texto de imagen con OCR mejorado."""
    try:
        textos = []

        if OPENCV_DISPONIBLE:
            imagenes = preparar_imagenes_para_ocr(file_path)
            configs = [
                "--oem 3 --psm 6",
                "--oem 3 --psm 4",
                "--oem 3 --psm 11",
            ]

            for img in imagenes:
                for config in configs:
                    texto = ejecutar_ocr_con_fallback(img, config=config)
                    if texto:
                        textos.append(texto)

        img_pil = Image.open(file_path)
        texto_original = ejecutar_ocr_con_fallback(img_pil)
        if texto_original:
            textos.append(texto_original)

        if textos:
            # Se escoge el texto con más posibles líneas de producto.
            return max(textos, key=puntuar_texto_ocr)

        return ""

    except Exception as e:
        raise Exception(
            "No se pudo leer la imagen con OCR.\n"
            "Verifique que Tesseract esté instalado correctamente.\n\n"
            f"Detalle: {e}"
        )


def ejecutar_ocr_con_fallback(imagen, config=""):
    """Intenta OCR en español y si falla usa el idioma por defecto."""
    try:
        return pytesseract.image_to_string(imagen, lang="spa", config=config)
    except Exception:
        return pytesseract.image_to_string(imagen, config=config)


def puntuar_texto_ocr(texto):
    """Prefiere el OCR que detecte más productos y más texto útil."""
    if not texto:
        return 0

    texto_upper = texto.upper()
    puntos = len(texto)
    puntos += texto_upper.count("U/M") * 800
    puntos += texto_upper.count(" UM") * 400
    puntos += texto_upper.count("ML") * 100
    puntos += texto_upper.count("UND") * 100
    puntos -= texto_upper.count("CUFE") * 200
    puntos -= texto_upper.count("AUTORIZ") * 200
    return puntos


def preparar_imagenes_para_ocr(file_path):
    """Genera varias versiones limpias de la imagen para mejorar el OCR."""
    img = cv2.imread(file_path)

    if img is None:
        raise Exception("No se pudo abrir la imagen.")

    gris = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gris = cv2.resize(gris, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    blur = cv2.GaussianBlur(gris, (3, 3), 0)

    _, otsu = cv2.threshold(
        blur,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    adaptiva = cv2.adaptiveThreshold(
        gris,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        11
    )

    invertida = cv2.bitwise_not(otsu)

    return [gris, otsu, adaptiva, invertida]


def extract_products_from_text(text):
    """Extrae productos detectados desde texto de PDF/OCR."""
    products = []
    lines = [limpiar_linea_ocr(l) for l in text.split("\n")]
    lines = [l for l in lines if l]

    for i, line in enumerate(lines):
        line_upper = line.upper()

        if not es_linea_producto(line_upper):
            continue

        if es_linea_basura(line_upper):
            continue

        nombre = limpiar_nombre_producto(line)

        if not validar_nombre_producto(nombre):
            continue

        cantidad = extraer_cantidad_desde_siguiente_linea(lines, i)

        if cantidad > 0:
            products.append({
                "nombre": nombre,
                "cantidad": cantidad
            })

    return limpiar_productos_duplicados(products)


def es_linea_producto(line_upper):
    """Detecta si una línea parece encabezado de producto."""
    return (
        "U/M" in line_upper
        or "U M" in line_upper
        or re.search(r"\bUM\b", line_upper) is not None
    )


def es_linea_basura(line_upper):
    """Evita líneas legales, totales o datos de factura que el OCR confunde."""
    return any(p in line_upper for p in PALABRAS_PROHIBIDAS)


def limpiar_linea_ocr(linea):
    texto = str(linea or "").strip()

    reemplazos = {
        "|": " ",
        "—": "-",
        "“": "",
        "”": "",
        "‘": "",
        "’": "",
        "O/M": "U/M",
        "0/M": "U/M",
        "UIM": "U/M",
        "U M": "U/M",
        "UM:": "U/M:",
        "U/M;": "U/M:",
        "~": " ",
    }

    for viejo, nuevo in reemplazos.items():
        texto = texto.replace(viejo, nuevo)

    texto = re.sub(r"\s+", " ", texto).strip()
    return texto


def limpiar_nombre_producto(linea):
    """Limpia la línea del producto y deja solo el nombre."""
    texto = str(linea or "").strip()

    texto = re.sub(r"^\d+\s*", "", texto)
    texto = re.sub(r"U\s*/?\s*M\s*:?\s*\d*", "", texto, flags=re.IGNORECASE)
    texto = re.sub(r"\b\d{7,}\b", "", texto)
    texto = re.sub(r"\b\d+[.,]\d{2,}\b", "", texto)
    texto = texto.replace("~", " ").replace(":", " ").replace(";", " ")
    texto = re.sub(r"\s+", " ", texto).strip()

    partes = []
    for palabra in texto.split():
        if palabra.upper() not in PALABRAS_BASURA_NOMBRE:
            partes.append(palabra)

    texto = " ".join(partes).strip()
    texto = corregir_errores_comunes_nombre(texto)
    return texto


def corregir_errores_comunes_nombre(nombre):
    texto = str(nombre or "").strip()

    correcciones = {
        "X750": "750",
        "X 750": "750",
        "LYMROJO": "LYM ROJO",
        "L Y M": "LYM",
        "BUCHANANS": "BUCHANAN'S",
        "BUCHANAN S": "BUCHANAN'S",
        "375MLDELUXE": "375ML DELUXE",
        "750MLUND": "750ML UND",
    }

    upper = texto.upper()
    for malo, bueno in correcciones.items():
        upper = upper.replace(malo, bueno)

    upper = re.sub(r"\s+", " ", upper).strip()
    return upper


def validar_nombre_producto(nombre):
    nombre_upper = str(nombre or "").upper().strip()

    if not nombre_upper:
        return False

    if len(nombre_upper) < 5:
        return False

    if not any(c.isalpha() for c in nombre_upper):
        return False

    if any(p in nombre_upper for p in PALABRAS_PROHIBIDAS):
        return False

    # Exige que parezca producto de inventario: medida, presentación o marca reconocible.
    pistas_producto = [
        "ML", "UND", "750", "375", "X10", "X 10", "RON", "AGUARDIENTE",
        "BUCHANAN", "DERBY", "DOMEC", "LYM", "CERVEZA", "WHISKY", "VINO",
        "TEQUILA", "VODKA", "BRANDY", "GINEBRA", "CALDAS", "AMARILLO"
    ]

    return any(p in nombre_upper for p in pistas_producto)


def extraer_cantidad_desde_siguiente_linea(lines, index):
    posibles_lineas = []

    for offset in range(1, 4):
        if index + offset < len(lines):
            posibles_lineas.append(lines[index + offset])

    for siguiente in posibles_lineas:
        if es_linea_basura(siguiente.upper()):
            continue

        numeros = re.findall(r"\d+(?:[.,]\d+)?", siguiente)

        if not numeros:
            continue

        valores = []
        for n in numeros:
            try:
                valores.append(float(n.replace(",", ".")))
            except Exception:
                pass

        if not valores:
            continue

        # Quitar códigos de barras y precios grandes.
        candidatos = [v for v in valores if 0 < v <= 1000]

        if not candidatos:
            continue

        # En la factura suele venir: código, referencia, cantidad, precio.
        # Tras filtrar código y precio, queda algo tipo [5, 1.00], [6, 2.00], [19, 10.00].
        if len(candidatos) >= 2:
            cantidad = candidatos[-1]
        else:
            cantidad = candidatos[0]

        if cantidad > 0:
            return int(cantidad)

    return 0


def limpiar_productos_duplicados(products):
    resultado = []
    vistos = set()

    for p in products:
        nombre = str(p.get("nombre", "")).strip()
        cantidad = int(p.get("cantidad", 0) or 0)

        if not validar_nombre_producto(nombre) or cantidad <= 0:
            continue

        clave = normalizar_clave_producto(nombre)

        if clave in vistos:
            continue

        vistos.add(clave)
        resultado.append({
            "nombre": nombre,
            "cantidad": cantidad
        })

    return resultado


def normalizar_clave_producto(nombre):
    clave = str(nombre or "").upper()
    clave = re.sub(r"[^A-Z0-9]+", " ", clave)
    clave = re.sub(r"\s+", " ", clave).strip()
    return clave
