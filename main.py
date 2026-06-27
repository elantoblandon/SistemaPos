import customtkinter as ctk
from tkinter import messagebox
import styles
from styles import *
from database import Database
import modules.login as login_module
import modules.pos as pos_module
import modules.dashboard as dashboard_module
import modules.inventario_modal as inventario_modal_module
from modules.login import LoginFrame
from modules.pos import POSFrame
from modules.dashboard import DashboardFrame
import os
import shutil
import datetime

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.db = Database()
        self.aplicar_apariencia()
        self.crear_backup()
        self.dashboard_desbloqueado = False

        # 🔥 NUEVO: guardar carrito en memoria
        self.carrito_temporal = {}

        self.actualizar_branding()
        self.geometry("1280x800")
        self.configure(fg_color=styles.COLOR_FONDO_CONTENIDO)

        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True)

        self.mostrar_login()

    def crear_backup(self):
        try:
            origen = "licorera_pro.db"

            if not os.path.exists(origen):
                return

            carpeta = "backups"
            os.makedirs(carpeta, exist_ok=True)

            fecha = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            destino = os.path.join(carpeta, f"backup_{fecha}.db")

            shutil.copy2(origen, destino)

        except Exception as e:
            print(f"Error creando backup: {e}")

    def aplicar_apariencia(self):
        """Carga colores desde SQLite y actualiza los módulos ya importados."""
        styles.aplicar_tema(self.db)
        constantes = styles.exportar_constantes_tema()
        for modulo in (login_module, pos_module, dashboard_module, inventario_modal_module):
            for nombre, valor in constantes.items():
                setattr(modulo, nombre, valor)
        globals().update(constantes)

    def refrescar_interfaz_por_configuracion(self):
        """Aplica branding/apariencia y reconstruye la pantalla activa."""
        self.aplicar_apariencia()
        self.configure(fg_color=styles.COLOR_FONDO_CONTENIDO)
        self.actualizar_branding()

        if not hasattr(self, "usuario_actual"):
            self.mostrar_login()
            return

        vista_actual = "dash"
        if hasattr(self, "pos_frame"):
            try:
                if self.pos_frame.winfo_exists():
                    vista_actual = "pos"
                    self.carrito_temporal = self.pos_frame.carrito.copy()
            except Exception:
                pass

        self.construir_interfaz_principal()
        if vista_actual == "dash" and self.usuario_actual.get("rol") == "admin":
            self.dashboard_desbloqueado = True
            self.cambiar_vista("dash")

    def mostrar_login(self):
        self.dashboard_desbloqueado = False
        for w in self.main_container.winfo_children():
            w.destroy()
        self.login = LoginFrame(self.main_container, self.procesar_login, self.db)
        self.login.place(relx=0.5, rely=0.5, anchor="center")

    def procesar_login(self, user, password):
        rol = self.db.validar_usuario(user, password)
        
        if rol:
            self.usuario_actual = {"username": user, "rol": rol}
            self.construir_interfaz_principal()
        else:
            messagebox.showerror("Error de Acceso", "Usuario o contraseña incorrectos.")

    def construir_interfaz_principal(self):
        for w in self.main_container.winfo_children():
            w.destroy()
        
        self.sidebar = ctk.CTkFrame(
            self.main_container,
            width=220,
            fg_color=COLOR_FONDO_SIDERBAR,
            corner_radius=0
        )
        self.sidebar.pack(side="left", fill="y")
        
        self.content_area = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_area.pack(side="right", fill="both", expand=True, padx=20, pady=20)

        negocio = self.db.obtener_datos_negocio()
        self.logo_sidebar_image = cargar_logo_ctk(self.db, size=(88, 88))
        if self.logo_sidebar_image:
            self.lbl_sidebar_logo = ctk.CTkLabel(
                self.sidebar,
                image=self.logo_sidebar_image,
                text=""
            )
            self.lbl_sidebar_logo.pack(pady=(24, 6))

        self.lbl_sidebar_brand = ctk.CTkLabel(
            self.sidebar,
            text=str(negocio.get("nombre_sistema", "PlanetBoxer")).upper(),
            font=FUERTE_SUBTITULO,
            text_color=COLOR_ACENTO
        )
        self.lbl_sidebar_brand.pack(pady=(10, 30) if self.logo_sidebar_image else 30)

        self.btn_pos = self.crear_boton_menu(
            "🛒 Punto de Venta",
            lambda: self.cambiar_vista("pos")
        )
        
        if self.usuario_actual["rol"] == "admin":
            self.btn_dash = self.crear_boton_menu(
                "📊 Dashboard",
                lambda: self.cambiar_vista("dash")
            )
        
        self.btn_salir = self.crear_boton_menu("🚪 Cerrar Sesión", self.mostrar_login)
        self.btn_salir.configure(hover_color=COLOR_PELIGRO)
        self.btn_salir.pack(side="bottom", pady=20)

        self.cambiar_vista("pos")

    def crear_boton_menu(self, texto, comando):
        btn = ctk.CTkButton(
            self.sidebar,
            text=texto,
            command=comando,
            fg_color="transparent",
            hover_color=COLOR_TARJETAS,
            anchor="w",
            font=FUERTE_TEXTO,
            height=45
        )
        btn.pack(fill="x", padx=10, pady=5)
        return btn

    def actualizar_branding(self):
        """Actualiza título de ventana y textos visibles según configuración del negocio."""
        try:
            negocio = self.db.obtener_datos_negocio()
            nombre = negocio.get("nombre_sistema", "PlanetBoxer")
            self.title(nombre)
            if hasattr(self, "lbl_sidebar_brand"):
                self.lbl_sidebar_brand.configure(text=str(nombre).upper())
            if hasattr(self, "login") and hasattr(self.login, "actualizar_textos"):
                self.login.actualizar_textos(negocio)
        except Exception as e:
            print(f"Error actualizando branding: {e}")

    def mostrar_modal_clave_dashboard(self):
        resultado = {"ok": False}

        modal = ctk.CTkToplevel(self)
        modal.title("Acceso Dashboard")
        modal.geometry("380x300")
        modal.resizable(False, False)
        modal.configure(fg_color=COLOR_FONDO_CONTENIDO)
        modal.transient(self)
        modal.grab_set()
        modal.lift()

        self.update_idletasks()
        x = self.winfo_x() + int((self.winfo_width() - 380) / 2)
        y = self.winfo_y() + int((self.winfo_height() - 300) / 2)
        modal.geometry(f"380x300+{max(x, 0)}+{max(y, 0)}")

        contenedor = ctk.CTkFrame(
            modal,
            fg_color=COLOR_TARJETAS,
            corner_radius=18,
            border_width=1,
            border_color=COLOR_BORDE
        )
        contenedor.pack(fill="both", expand=True, padx=18, pady=18)

        logo_img = cargar_logo_ctk(self.db, size=(56, 56))
        if logo_img:
            modal.logo_img = logo_img
            ctk.CTkLabel(contenedor, image=modal.logo_img, text="").pack(pady=(22, 6))

        ctk.CTkLabel(
            contenedor,
            text="Acceso administrativo",
            font=FUERTE_SUBTITULO,
            text_color=COLOR_ACENTO
        ).pack(pady=(18 if not logo_img else 4, 4))

        ctk.CTkLabel(
            contenedor,
            text="Ingresa la clave para abrir el Dashboard.",
            font=FUERTE_TEXTO,
            text_color=COLOR_TEXTO_SECUNDARIO
        ).pack(pady=(0, 16))

        entry_clave = ctk.CTkEntry(
            contenedor,
            width=260,
            height=44,
            show="*",
            justify="center",
            font=("Inter", 18, "bold"),
            fg_color=COLOR_FONDO_CONTENIDO,
            border_color=COLOR_BORDE,
            text_color=COLOR_TEXTO_PRINCIPAL,
            placeholder_text="Clave",
            placeholder_text_color=COLOR_TEXTO_SECUNDARIO
        )
        entry_clave.pack(pady=(0, 14))

        lbl_error = ctk.CTkLabel(
            contenedor,
            text="",
            font=("Inter", 11, "bold"),
            text_color=COLOR_PELIGRO
        )
        lbl_error.pack(pady=(0, 8))

        botones = ctk.CTkFrame(contenedor, fg_color="transparent")
        botones.pack(fill="x", padx=28, pady=(0, 18))
        botones.grid_columnconfigure((0, 1), weight=1)

        def cerrar():
            resultado["ok"] = False
            modal.destroy()

        def validar():
            clave = entry_clave.get().strip()
            if clave == self.db.obtener_clave_dashboard():
                resultado["ok"] = True
                self.dashboard_desbloqueado = True
                modal.destroy()
            else:
                lbl_error.configure(text="Clave incorrecta.")
                entry_clave.delete(0, "end")
                entry_clave.focus()

        ctk.CTkButton(
            botones,
            text="Cancelar",
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDE,
            text_color=COLOR_TEXTO_PRINCIPAL,
            hover_color=COLOR_HOVER,
            command=cerrar
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkButton(
            botones,
            text="Entrar",
            fg_color=COLOR_ACENTO,
            hover_color=COLOR_PRIMARIO,
            text_color="#000000",
            font=FUERTE_TEXTO_BOLD,
            command=validar
        ).grid(row=0, column=1, sticky="ew", padx=(6, 0))

        modal.protocol("WM_DELETE_WINDOW", cerrar)
        modal.bind("<Escape>", lambda _e: cerrar())
        modal.bind("<Return>", lambda _e: validar())
        entry_clave.focus()
        self.wait_window(modal)
        return resultado["ok"]

    def pedir_clave_dashboard(self):
        return self.mostrar_modal_clave_dashboard()

        clave = simpledialog.askstring(
            "Acceso restringido",
            "Ingrese la contraseña para acceder al Dashboard:",
            show="*"
        )

        if clave is None:
            return False

        if clave == self.db.obtener_clave_dashboard():
            self.dashboard_desbloqueado = True
            return True

        messagebox.showerror("Acceso denegado", "Contraseña incorrecta.")
        return False

    def cambiar_vista(self, vista):
        if vista in ("dash", "inv") and not self.dashboard_desbloqueado:
            if not self.pedir_clave_dashboard():
                return

        # 🔥 GUARDAR carrito antes de cambiar
        if hasattr(self, "pos_frame"):
            try:
                self.carrito_temporal = self.pos_frame.carrito.copy()
            except:
                pass

        for w in self.content_area.winfo_children():
            w.destroy()
        
        if vista == "pos":
            # 🔥 CREAR POS y restaurar carrito
            self.pos_frame = POSFrame(
                self.content_area,
                self.db,
                self.usuario_actual.get("username", "admin")
            )
            self.pos_frame.pack(fill="both", expand=True)

            if self.carrito_temporal:
                try:
                    self.pos_frame.carrito = self.carrito_temporal.copy()
                    self.pos_frame.actualizar_carrito()
                except:
                    pass
        
        elif vista == "dash" or vista == "inv":
            panel = DashboardFrame(
                self.content_area,
                self.db,
                on_config_guardada=self.refrescar_interfaz_por_configuracion
            )
            panel.pack(fill="both", expand=True)
            
            if vista == "inv":
                try:
                    panel.pestanas.set("📦 Inventario Detallado")
                except:
                    pass

if __name__ == "__main__":
    app = App()
    app.mainloop()
