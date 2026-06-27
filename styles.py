import re
import os
import customtkinter as ctk

try:
    from PIL import Image
except Exception:
    Image = None


THEME_DEFAULTS = {
    "tema_modo": "Oscuro",
    "color_acento": "#10b981",
    "color_primario": "#3b82f6",
}


THEMES = {
    "Oscuro": {
        "COLOR_FONDO_CONTENIDO": "#0f111a",
        "COLOR_FONDO_SIDERBAR": "#1a1c23",
        "COLOR_TARJETAS": "#1f222e",
        "COLOR_TEXTO_PRINCIPAL": "#f9fafb",
        "COLOR_TEXTO_SECUNDARIO": "#9ca3af",
        "COLOR_BORDE": "#2d303d",
        "COLOR_ACENTO_BAJO": "#1e3a34",
        "COLOR_SELECCION": "#2d303d",
        "COLOR_HOVER": "#252936",
    },
    "Claro": {
        "COLOR_FONDO_CONTENIDO": "#eef3f8",
        "COLOR_FONDO_SIDERBAR": "#ffffff",
        "COLOR_TARJETAS": "#ffffff",
        "COLOR_TEXTO_PRINCIPAL": "#0f172a",
        "COLOR_TEXTO_SECUNDARIO": "#334155",
        "COLOR_BORDE": "#cbd5e1",
        "COLOR_ACENTO_BAJO": "#ccfbf1",
        "COLOR_SELECCION": "#dbeafe",
        "COLOR_HOVER": "#e2e8f0",
    },
}


COLOR_FONDO_CONTENIDO = THEMES["Oscuro"]["COLOR_FONDO_CONTENIDO"]
COLOR_FONDO_SIDERBAR = THEMES["Oscuro"]["COLOR_FONDO_SIDERBAR"]
COLOR_TARJETAS = THEMES["Oscuro"]["COLOR_TARJETAS"]
COLOR_ACENTO = THEME_DEFAULTS["color_acento"]
COLOR_PRIMARIO = THEME_DEFAULTS["color_primario"]
COLOR_PELIGRO = "#ef4444"
COLOR_ACENTO_BAJO = THEMES["Oscuro"]["COLOR_ACENTO_BAJO"]
COLOR_SELECCION = THEMES["Oscuro"]["COLOR_SELECCION"]
COLOR_HOVER = THEMES["Oscuro"]["COLOR_HOVER"]
COLOR_TEXTO_PRINCIPAL = THEMES["Oscuro"]["COLOR_TEXTO_PRINCIPAL"]
COLOR_TEXTO_SECUNDARIO = THEMES["Oscuro"]["COLOR_TEXTO_SECUNDARIO"]
COLOR_BORDE = THEMES["Oscuro"]["COLOR_BORDE"]


FUERTE_TITULO = ("Inter", 28, "bold")
FUERTE_SUBTITULO = ("Inter", 18, "bold")
FUERTE_TEXTO = ("Inter", 13)
FUERTE_TEXTO_BOLD = ("Inter", 13, "bold")
MONEDA_TEXTO = ("Inter", 32, "bold")


def normalizar_hex_color(valor, fallback):
    valor = str(valor or "").strip()
    if re.fullmatch(r"#[0-9a-fA-F]{6}", valor):
        return valor.lower()
    return fallback


def cargar_tema_desde_db(db=None):
    datos = THEME_DEFAULTS.copy()
    if db is None:
        return datos

    try:
        for clave, valor_default in THEME_DEFAULTS.items():
            datos[clave] = db.obtener_configuracion(clave, valor_default) or valor_default
    except Exception:
        return datos

    datos["tema_modo"] = "Claro" if str(datos.get("tema_modo")).lower() == "claro" else "Oscuro"
    datos["color_acento"] = normalizar_hex_color(datos.get("color_acento"), THEME_DEFAULTS["color_acento"])
    datos["color_primario"] = normalizar_hex_color(datos.get("color_primario"), THEME_DEFAULTS["color_primario"])
    return datos


def aplicar_tema(db=None):
    global COLOR_FONDO_CONTENIDO, COLOR_FONDO_SIDERBAR, COLOR_TARJETAS
    global COLOR_ACENTO, COLOR_PRIMARIO, COLOR_ACENTO_BAJO, COLOR_SELECCION
    global COLOR_HOVER, COLOR_TEXTO_PRINCIPAL, COLOR_TEXTO_SECUNDARIO, COLOR_BORDE

    datos = cargar_tema_desde_db(db)
    modo = datos["tema_modo"]
    paleta = THEMES[modo]

    COLOR_FONDO_CONTENIDO = paleta["COLOR_FONDO_CONTENIDO"]
    COLOR_FONDO_SIDERBAR = paleta["COLOR_FONDO_SIDERBAR"]
    COLOR_TARJETAS = paleta["COLOR_TARJETAS"]
    COLOR_TEXTO_PRINCIPAL = paleta["COLOR_TEXTO_PRINCIPAL"]
    COLOR_TEXTO_SECUNDARIO = paleta["COLOR_TEXTO_SECUNDARIO"]
    COLOR_BORDE = paleta["COLOR_BORDE"]
    COLOR_ACENTO_BAJO = paleta["COLOR_ACENTO_BAJO"]
    COLOR_SELECCION = paleta["COLOR_SELECCION"]
    COLOR_HOVER = paleta["COLOR_HOVER"]
    COLOR_ACENTO = datos["color_acento"]
    COLOR_PRIMARIO = datos["color_primario"]

    ctk.set_appearance_mode("Light" if modo == "Claro" else "Dark")
    ctk.set_default_color_theme("blue")
    return datos


def exportar_constantes_tema():
    return {
        "COLOR_FONDO_CONTENIDO": COLOR_FONDO_CONTENIDO,
        "COLOR_FONDO_SIDERBAR": COLOR_FONDO_SIDERBAR,
        "COLOR_TARJETAS": COLOR_TARJETAS,
        "COLOR_ACENTO": COLOR_ACENTO,
        "COLOR_PRIMARIO": COLOR_PRIMARIO,
        "COLOR_PELIGRO": COLOR_PELIGRO,
        "COLOR_ACENTO_BAJO": COLOR_ACENTO_BAJO,
        "COLOR_SELECCION": COLOR_SELECCION,
        "COLOR_HOVER": COLOR_HOVER,
        "COLOR_TEXTO_PRINCIPAL": COLOR_TEXTO_PRINCIPAL,
        "COLOR_TEXTO_SECUNDARIO": COLOR_TEXTO_SECUNDARIO,
        "COLOR_BORDE": COLOR_BORDE,
    }


def obtener_ruta_logo(db=None):
    if db is None:
        return ""
    try:
        ruta = db.obtener_configuracion("logo_path", "") or ""
        ruta = str(ruta).strip()
        if ruta and os.path.exists(ruta):
            return ruta
    except Exception:
        pass
    return ""


def cargar_logo_ctk(db=None, size=(96, 96)):
    ruta = obtener_ruta_logo(db)
    if not ruta or Image is None:
        return None

    try:
        imagen = Image.open(ruta)
        imagen.thumbnail(size)
        lienzo = Image.new("RGBA", size, (0, 0, 0, 0))
        x = int((size[0] - imagen.width) / 2)
        y = int((size[1] - imagen.height) / 2)
        lienzo.paste(imagen.convert("RGBA"), (x, y), imagen.convert("RGBA"))
        return ctk.CTkImage(light_image=lienzo, dark_image=lienzo, size=size)
    except Exception as e:
        print(f"Error cargando logo: {e}")
        return None


def formato_moneda(valor):
    try:
        return f"$ {float(valor):,.0f}"
    except Exception:
        return "$ 0"
