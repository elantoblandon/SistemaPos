import customtkinter as ctk
from styles import *
from tkinter import messagebox


class NuevoProductoModal(ctk.CTkToplevel):
    def __init__(self, master, db, callback_actualizar, producto_data=None):
        super().__init__(master)
        self.db = db
        self.callback_actualizar = callback_actualizar
        self.producto_data = producto_data

        titulo_ventana = "EDITAR PRODUCTO" if producto_data else "REGISTRAR PRODUCTO"

        self.title("Gestión de Producto")
        self.geometry("400x560")
        self.configure(fg_color=COLOR_TARJETAS)
        self.resizable(False, False)

        self.grab_set()
        self.lift()
        self.focus_force()

        ctk.CTkLabel(
            self,
            text=titulo_ventana,
            font=FUERTE_SUBTITULO,
            text_color=COLOR_ACENTO
        ).pack(pady=20)

        # Campos de entrada
        self.ent_codigo = self.crear_campo("Código de Barras / SKU")
        self.ent_nombre = self.crear_campo("Nombre del Producto (ej. Producto)")
        self.ent_precio_c = self.crear_campo("Precio Compra ($)")
        self.ent_precio_v = self.crear_campo("Precio Venta ($)")
        self.ent_stock = self.crear_campo("Cantidad Inicial")
        self.ent_cat = self.crear_campo("Categoría (categoria1, categoria2, categoria3)")

        # Formato automático de moneda
        self.ent_precio_c.bind(
            "<KeyRelease>",
            lambda e: self.formatear_moneda_entry(self.ent_precio_c)
        )
        self.ent_precio_v.bind(
            "<KeyRelease>",
            lambda e: self.formatear_moneda_entry(self.ent_precio_v)
        )

        # Navegación por teclado
        self.ent_codigo.bind("<Return>", lambda e: self.ent_nombre.focus())
        self.ent_nombre.bind("<Return>", lambda e: self.ent_precio_c.focus())
        self.ent_precio_c.bind("<Return>", lambda e: self.ent_precio_v.focus())
        self.ent_precio_v.bind("<Return>", lambda e: self.ent_stock.focus())
        self.ent_stock.bind("<Return>", lambda e: self.ent_cat.focus())
        self.ent_cat.bind("<Return>", lambda e: self.guardar())

        # Cargar datos si es edición
        if self.producto_data:
            self.cargar_datos_producto()

        self.after(
            200,
            lambda: self.ent_nombre.focus() if self.producto_data else self.ent_codigo.focus()
        )

        texto_btn = "ACTUALIZAR DATOS" if producto_data else "GUARDAR EN INVENTARIO"

        self.btn_guardar = ctk.CTkButton(
            self,
            text=texto_btn,
            fg_color=COLOR_ACENTO,
            text_color="#000",
            font=FUERTE_TEXTO_BOLD,
            height=45,
            command=self.guardar
        )
        self.btn_guardar.pack(pady=(30, 10), padx=40, fill="x")

        self.btn_cancelar = ctk.CTkButton(
            self,
            text="CANCELAR",
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_BORDE,
            text_color=COLOR_TEXTO_PRINCIPAL,
            font=FUERTE_TEXTO_BOLD,
            height=40,
            command=self.destroy
        )
        self.btn_cancelar.pack(pady=(0, 20), padx=40, fill="x")

    def crear_campo(self, placeholder):
        entry = ctk.CTkEntry(
            self,
            placeholder_text=placeholder,
            height=40,
            fg_color=COLOR_FONDO_CONTENIDO,
            border_color=COLOR_BORDE
        )
        entry.pack(pady=5, padx=40, fill="x")
        return entry

    def cargar_datos_producto(self):
        self.ent_codigo.insert(0, str(self.producto_data[0]))
        self.ent_codigo.configure(state="disabled")

        self.ent_nombre.insert(0, str(self.producto_data[1]))
        self.ent_precio_c.insert(0, self.formatear_moneda(self.producto_data[2]))
        self.ent_precio_v.insert(0, self.formatear_moneda(self.producto_data[3]))
        self.ent_stock.insert(0, str(self.producto_data[4]))

        if len(self.producto_data) > 5 and self.producto_data[5] is not None:
            self.ent_cat.insert(0, str(self.producto_data[5]))

    def formatear_moneda(self, valor):
        try:
            return f"{float(valor):,.0f}"
        except Exception:
            return "0"

    def limpiar_numero(self, valor):
        return str(valor).replace(",", "").replace(".", "").strip()

    def formatear_moneda_entry(self, entry):
        texto = self.limpiar_numero(entry.get())

        if not texto:
            return

        if not texto.isdigit():
            return

        valor = int(texto)
        nuevo = f"{valor:,}"

        entry.delete(0, "end")
        entry.insert(0, nuevo)
        entry.icursor("end")

    def guardar(self):
        try:
            codigo = self.ent_codigo.get().strip()
            nombre = self.ent_nombre.get().strip()
            categoria = self.ent_cat.get().strip()

            precio_c_texto = self.ent_precio_c.get().replace(",", "").strip()
            precio_v_texto = self.ent_precio_v.get().replace(",", "").strip()
            stock_texto = self.ent_stock.get().strip()

            precio_c = float(precio_c_texto or 0)
            precio_v = float(precio_v_texto or 0)
            stock = int(float(stock_texto or 0))

            if not codigo or not nombre:
                messagebox.showwarning("Atención", "Código y Nombre son obligatorios.")
                return

            if precio_v < 0 or precio_c < 0 or stock < 0:
                messagebox.showwarning("Atención", "Precios y stock no pueden ser negativos.")
                return

            if self.producto_data:
                res = self.db.actualizar_producto(
                    codigo,
                    nombre,
                    precio_c,
                    precio_v,
                    stock,
                    categoria
                )
                mensaje_exito = "Producto actualizado correctamente."
            else:
                res = self.db.guardar_producto(
                    codigo,
                    nombre,
                    precio_c,
                    precio_v,
                    stock,
                    categoria
                )
                mensaje_exito = "Producto guardado con éxito."

            if res:
                messagebox.showinfo("Éxito", mensaje_exito)
                self.callback_actualizar()
                self.destroy()
            else:
                messagebox.showerror(
                    "Error",
                    "No se pudo procesar la operación. Verifique que el código no esté repetido."
                )

        except ValueError:
            messagebox.showerror(
                "Error",
                "Los precios y el stock deben ser números válidos."
            )
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"Ocurrió un error inesperado: {e}"
            )
