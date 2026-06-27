import customtkinter as ctk
from styles import *

class LoginFrame(ctk.CTkFrame):
    def __init__(self, master, al_loguear, db):
        super().__init__(
            master,
            fg_color=COLOR_TARJETAS,
            corner_radius=20,
            border_width=1,
            border_color=COLOR_BORDE
        )

        self.al_loguear = al_loguear
        self.db = db

        self.logo_image = cargar_logo_ctk(self.db, size=(110, 110))
        self.logo_label = None
        if self.logo_image:
            self.logo_label = ctk.CTkLabel(self, image=self.logo_image, text="")
            self.logo_label.pack(pady=(28, 6), padx=50)

        self.label = ctk.CTkLabel(
            self,
            text="PlanetBoxer",
            font=FUERTE_TITULO,
            text_color=COLOR_ACENTO
        )
        self.label.pack(pady=(16, 10) if self.logo_image else (40, 10), padx=50)

        self.sublabel = ctk.CTkLabel(
            self,
            text="Gestión de Inventario y Ventas",
            font=FUERTE_TEXTO,
            text_color=COLOR_TEXTO_SECUNDARIO
        )
        self.sublabel.pack(pady=(0, 30))

        self.user_entry = ctk.CTkEntry(
            self,
            placeholder_text="Usuario",
            width=280,
            height=50,
            border_color=COLOR_BORDE,
            fg_color=COLOR_FONDO_CONTENIDO,
            text_color=COLOR_TEXTO_PRINCIPAL,
            placeholder_text_color=COLOR_TEXTO_SECUNDARIO
        )
        self.user_entry.pack(pady=10, padx=40)

        self.pass_entry = ctk.CTkEntry(
            self,
            placeholder_text="Contraseña",
            show="*",
            width=280,
            height=50,
            border_color=COLOR_BORDE,
            fg_color=COLOR_FONDO_CONTENIDO,
            text_color=COLOR_TEXTO_PRINCIPAL,
            placeholder_text_color=COLOR_TEXTO_SECUNDARIO
        )
        self.pass_entry.pack(pady=10, padx=40)

        self.btn_entrar = ctk.CTkButton(
            self,
            text="Acceder al Sistema",
            command=self.verificar,
            fg_color=COLOR_PRIMARIO,
            hover_color="#2563eb",
            height=50,
            width=280,
            font=FUERTE_TEXTO_BOLD
        )
        self.btn_entrar.pack(pady=(30, 40))

        self.actualizar_textos()

    def actualizar_textos(self, negocio=None):
        if negocio is None and self.db:
            negocio = self.db.obtener_datos_negocio()
        if not negocio:
            return
        self.label.configure(text=negocio.get("nombre_sistema", "PlanetBoxer"))
        self.logo_image = cargar_logo_ctk(self.db, size=(110, 110))
        if self.logo_image and self.logo_label:
            self.logo_label.configure(image=self.logo_image)
        self.sublabel.configure(text=negocio.get("subtitulo_sistema", "Gestión de Inventario y Ventas"))

    def verificar(self):
        usuario = self.user_entry.get()
        contrasena = self.pass_entry.get()
        self.al_loguear(usuario, contrasena)
