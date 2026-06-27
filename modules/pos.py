import customtkinter as ctk
from tkinter import messagebox, simpledialog, Listbox
from styles import *
import os
import subprocess
from datetime import datetime



class POSFrame(ctk.CTkFrame):
    def __init__(self, master, db, usuario_actual="admin"):
        super().__init__(master, fg_color=COLOR_FONDO_CONTENIDO)
        self.db = db
        self.usuario_actual = usuario_actual
        self.carrito = {}
        self.total = 0.0
        self.filas_visuales = {}

        if not os.path.exists("facturas"):
            os.makedirs("facturas")

        self.grid_columnconfigure(0, weight=3)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.disenar_area_venta()
        self.disenar_area_cobro()

        # Foco automático para lector de código de barras
        self.after(200, lambda: self.entry_busqueda.focus())

    def disenar_area_venta(self):
        self.left_container = ctk.CTkFrame(self, fg_color="transparent")
        self.left_container.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")

        self.search_container = ctk.CTkFrame(self.left_container, fg_color="transparent")
        self.search_container.pack(fill="x", pady=(0, 15))

        self.search_frame = ctk.CTkFrame(
            self.search_container,
            fg_color=COLOR_TARJETAS,
            height=60,
            corner_radius=15
        )
        self.search_frame.pack(fill="x")
        self.search_frame.pack_propagate(False)

        self.entry_busqueda = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="🔍 Escriba nombre o escanee código...",
            fg_color="transparent",
            border_width=0,
            font=FUERTE_TEXTO,
            height=40,
            text_color=COLOR_TEXTO_PRINCIPAL,
            placeholder_text_color=COLOR_TEXTO_SECUNDARIO
        )
        self.entry_busqueda.pack(fill="both", padx=20, pady=10)

        self.entry_busqueda.bind("<KeyRelease>", self.on_key_release)
        self.entry_busqueda.bind("<Return>", lambda e: self.agregar_al_carrito())

        self.lista_sugerencias = Listbox(
            self.left_container,
            font=("Inter", 12),
            fg=COLOR_TEXTO_PRINCIPAL,
            bg=COLOR_TARJETAS,
            borderwidth=0,
            highlightthickness=0,
            selectbackground=COLOR_ACENTO,
            selectforeground="black"
        )
        self.lista_sugerencias.bind("<<ListboxSelect>>", self.seleccionar_sugerencia)

        self.carrito_frame = ctk.CTkScrollableFrame(
            self.left_container,
            fg_color=COLOR_TARJETAS,
            corner_radius=15,
            label_text="DETALLE DE LA VENTA",
            label_font=FUERTE_TEXTO_BOLD,
            label_text_color=COLOR_TEXTO_SECUNDARIO
        )
        self.carrito_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.header_tabla = ctk.CTkFrame(self.carrito_frame, fg_color=COLOR_SELECCION, height=35)
        self.header_tabla.pack(fill="x", pady=5)

        self.header_tabla.grid_columnconfigure(0, weight=0, minsize=60)
        self.header_tabla.grid_columnconfigure(1, weight=1)
        self.header_tabla.grid_columnconfigure(2, weight=0, minsize=100)
        self.header_tabla.grid_columnconfigure(3, weight=0, minsize=90)

        ctk.CTkLabel(self.header_tabla, text="Cant.", font=("Inter", 11, "bold")).grid(row=0, column=0)
        ctk.CTkLabel(self.header_tabla, text="Descripción del Producto", font=("Inter", 11, "bold")).grid(row=0, column=1, padx=10, sticky="w")
        ctk.CTkLabel(self.header_tabla, text="Subtotal", font=("Inter", 11, "bold")).grid(row=0, column=2)
        ctk.CTkLabel(self.header_tabla, text="Acciones", font=("Inter", 11, "bold")).grid(row=0, column=3)

    def on_key_release(self, event):
        if event.keysym in ("Up", "Down", "Return", "Escape"):
            return

        query = self.entry_busqueda.get().strip()

        if len(query) >= 2:
            resultados = self.db.buscar_productos_coincidentes(query)

            if resultados:
                self.lista_sugerencias.delete(0, 'end')
                for res in resultados:
                    self.lista_sugerencias.insert(
                        'end',
                        f"{res[0]} | {res[1]} - {formato_moneda(res[2])}"
                    )
                self.lista_sugerencias.pack(fill="x", after=self.search_frame, padx=10)
            else:
                self.lista_sugerencias.pack_forget()
        else:
            self.lista_sugerencias.pack_forget()

    def seleccionar_sugerencia(self, event):
        if not self.lista_sugerencias.curselection():
            return

        seleccion = self.lista_sugerencias.get(self.lista_sugerencias.curselection())
        sku = seleccion.split(" | ")[0]

        self.entry_busqueda.delete(0, 'end')
        self.entry_busqueda.insert(0, sku)

        self.lista_sugerencias.pack_forget()
        self.agregar_al_carrito()

    def agregar_al_carrito(self):
        query = self.entry_busqueda.get().strip()
        if not query:
            return

        producto = self.db.buscar_producto_por_codigo(query)

        if producto:
            sku, nombre, precio, stock_max = producto

            if sku in self.carrito:
                if self.carrito[sku]['cantidad'] < stock_max:
                    self.carrito[sku]['cantidad'] += 1
                    self.actualizar_fila_visual(sku)
                else:
                    messagebox.showwarning("Stock Límite", f"No hay más stock de {nombre}.")
            else:
                if stock_max > 0:
                    self.carrito[sku] = {
                        'nombre': nombre,
                        'precio': precio,
                        'cantidad': 1,
                        'stock_max': stock_max
                    }
                    self.crear_fila_producto(sku)
                else:
                    messagebox.showwarning("Sin Stock", "Producto agotado.")

            self.recalcular_total()
            self.entry_busqueda.delete(0, 'end')
            self.lista_sugerencias.pack_forget()

        else:
            messagebox.showerror("No encontrado", "Producto no registrado.")

    def crear_fila_producto(self, sku):
        item = self.carrito[sku]

        fila = ctk.CTkFrame(self.carrito_frame, fg_color="transparent")
        fila.pack(fill="x", pady=2)

        fila.grid_columnconfigure(0, weight=0, minsize=60)
        fila.grid_columnconfigure(1, weight=1)
        fila.grid_columnconfigure(2, weight=0, minsize=100)
        fila.grid_columnconfigure(3, weight=0, minsize=90)

        lbl_cant = ctk.CTkLabel(fila, text=f"{item['cantidad']} x", font=FUERTE_TEXTO)
        lbl_cant.grid(row=0, column=0)

        ctk.CTkLabel(
            fila,
            text=item['nombre'],
            font=FUERTE_TEXTO,
            anchor="w"
        ).grid(row=0, column=1, padx=10, sticky="w")

        lbl_subtotal = ctk.CTkLabel(
            fila,
            text=formato_moneda(item['precio']),
            font=FUERTE_TEXTO_BOLD,
            text_color=COLOR_ACENTO
        )
        lbl_subtotal.grid(row=0, column=2, sticky="e")

        actions_frame = ctk.CTkFrame(fila, fg_color="transparent")
        actions_frame.grid(row=0, column=3, padx=5)

        ctk.CTkButton(actions_frame, text="📝", width=30, height=30,
                      fg_color="#2d3d3d",
                      command=lambda: self.editar_cantidad(sku)).pack(side="left", padx=2)

        ctk.CTkButton(actions_frame, text="✕", width=30, height=30,
                      fg_color="#3d2d2d",
                      command=lambda: self.eliminar_del_carrito(sku)).pack(side="left", padx=2)

        self.filas_visuales[sku] = {
            "frame": fila,
            "lbl_cant": lbl_cant,
            "lbl_subtotal": lbl_subtotal
        }

    def editar_cantidad(self, sku):
        item = self.carrito[sku]

        nueva_cant = simpledialog.askinteger(
            "Editar",
            f"¿Cantidad de {item['nombre']}?",
            initialvalue=item['cantidad'],
            minvalue=1,
            maxvalue=item['stock_max']
        )

        if nueva_cant:
            self.carrito[sku]['cantidad'] = nueva_cant
            self.actualizar_fila_visual(sku)
            self.recalcular_total()

    def actualizar_fila_visual(self, sku):
        item = self.carrito[sku]
        self.filas_visuales[sku]["lbl_cant"].configure(text=f"{item['cantidad']} x")
        self.filas_visuales[sku]["lbl_subtotal"].configure(
            text=formato_moneda(item['precio'] * item['cantidad'])
        )

    def eliminar_del_carrito(self, sku):
        self.filas_visuales[sku]["frame"].destroy()
        del self.filas_visuales[sku]
        del self.carrito[sku]
        self.recalcular_total()

    def recalcular_total(self):
        self.total = sum(item['precio'] * item['cantidad'] for item in self.carrito.values())
        self.lbl_total.configure(text=formato_moneda(self.total))

    def exportar_carrito(self):
        """Devuelve una copia segura del carrito actual para conservarlo al cambiar de vista."""
        try:
            return {
                sku: {
                    'nombre': datos.get('nombre', ''),
                    'precio': float(datos.get('precio', 0) or 0),
                    'cantidad': int(datos.get('cantidad', 0) or 0),
                    'stock_max': int(datos.get('stock_max', 0) or 0)
                }
                for sku, datos in self.carrito.items()
                if int(datos.get('cantidad', 0) or 0) > 0
            }
        except Exception as e:
            print(f"Error exportando carrito: {e}")
            return {}

    def restaurar_carrito(self, carrito_guardado):
        """Restaura el carrito guardado en memoria y reconstruye sus filas visuales."""
        try:
            self.carrito = {}

            if isinstance(carrito_guardado, dict):
                for sku, datos in carrito_guardado.items():
                    self.carrito[sku] = {
                        'nombre': datos.get('nombre', ''),
                        'precio': float(datos.get('precio', 0) or 0),
                        'cantidad': int(datos.get('cantidad', 0) or 0),
                        'stock_max': int(datos.get('stock_max', 0) or 0)
                    }

            self.actualizar_carrito()
        except Exception as e:
            print(f"Error restaurando carrito: {e}")

    def actualizar_carrito(self):
        """Reconstruye visualmente el carrito actual. Útil al volver desde Dashboard/Inventario."""
        try:
            for item in list(self.filas_visuales.values()):
                item["frame"].destroy()

            self.filas_visuales = {}

            for sku in list(self.carrito.keys()):
                datos = self.carrito.get(sku, {})
                cantidad = int(datos.get('cantidad', 0) or 0)

                if cantidad <= 0:
                    self.carrito.pop(sku, None)
                    continue

                self.crear_fila_producto(sku)

            self.recalcular_total()
            self.after(100, lambda: self.entry_busqueda.focus())
        except Exception as e:
            print(f"Error actualizando carrito visual: {e}")

    def disenar_area_cobro(self):
        self.cobro_frame = ctk.CTkFrame(
            self,
            fg_color=COLOR_TARJETAS,
            corner_radius=20,
            border_width=1,
            border_color=COLOR_BORDE
        )
        self.cobro_frame.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="nsew")

        ctk.CTkLabel(
            self.cobro_frame,
            text="RESUMEN",
            font=FUERTE_TEXTO_BOLD,
            text_color=COLOR_TEXTO_SECUNDARIO
        ).pack(pady=(30, 10))

        self.lbl_total = ctk.CTkLabel(
            self.cobro_frame,
            text=formato_moneda(0),
            font=MONEDA_TEXTO,
            text_color=COLOR_ACENTO
        )
        self.lbl_total.pack(pady=10)

        ctk.CTkButton(
            self.cobro_frame,
            text="Limpiar Todo",
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_PELIGRO,
            text_color=COLOR_PELIGRO,
            command=self.limpiar_venta
        ).pack(fill="x", padx=20, pady=10)

        self.btn_cierre_caja = ctk.CTkButton(
            self.cobro_frame,
            text="💰 Cierre de Caja",
            fg_color="#D35400",
            hover_color="#E67E22",
            text_color="#FFFFFF",
            font=("Inter", 13, "bold"),
            height=42,
            command=self.generar_cierre_caja_pos
        )
        self.btn_cierre_caja.pack(fill="x", padx=20, pady=(0, 10))

        self.btn_cobrar = ctk.CTkButton(
            self.cobro_frame,
            text="COBRAR (F5)",
            fg_color=COLOR_ACENTO,
            text_color="#000",
            font=("Inter", 18, "bold"),
            height=65,
            command=self.procesar_pago
        )
        self.btn_cobrar.pack(side="bottom", fill="x", padx=20, pady=20)

    def generar_cierre_caja_pos(self):
        """Genera el mismo cierre de caja usando los datos reales de la base de datos."""
        if not hasattr(self.db, "obtener_datos_cierre_caja"):
            messagebox.showerror(
                "Función no disponible",
                "Tu database.py aún no tiene la función obtener_datos_cierre_caja()."
            )
            return

        datos_cierre = self.db.obtener_datos_cierre_caja()

        if not datos_cierre:
            messagebox.showwarning("Sin datos", "No hay ventas registradas para el día de hoy.")
            return

        resumen = self.calcular_resumen_cierre(datos_cierre)

        try:
            ruta_pdf = self.generar_pdf_cierre(datos_cierre, resumen)
            self.abrir_archivo(ruta_pdf)
            messagebox.showinfo(
                "Cierre generado",
                f"Cierre de caja generado correctamente.\n\n"
                f"Total vendido: {formato_moneda(resumen['total'])}\n"
                f"Tickets: {resumen['tickets']}\n"
                f"Productos: {resumen['productos']}\n"
                f"Ganancia: {formato_moneda(resumen['ganancia'])}"
            )
        except ImportError:
            messagebox.showerror(
                "Falta librería",
                "Para generar el cierre en PDF debes instalar reportlab:\n\npip install reportlab"
            )
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el cierre de caja:\n{e}")

    def calcular_resumen_cierre(self, datos_cierre):
        """Calcula total, tickets, productos y ganancia usando los tickets del cierre."""
        resumen = {
            "total": 0.0,
            "tickets": len(datos_cierre),
            "productos": 0,
            "ganancia": 0.0
        }

        for venta in datos_cierre:
            info = venta.get("info_venta", ())
            productos = venta.get("productos", [])

            try:
                resumen["total"] += float(info[2] or 0)
            except Exception:
                pass

            for p in productos:
                try:
                    cantidad = int(p[1] or 0)
                    precio_unitario = float(p[2] or 0)
                    resumen["productos"] += cantidad

                    if len(p) >= 4:
                        precio_compra = float(p[3] or 0)
                        resumen["ganancia"] += (precio_unitario - precio_compra) * cantidad
                except Exception:
                    pass

        return resumen

    def agrupar_productos_cierre(self, datos_cierre):
        """Agrupa productos iguales para que el PDF salga compacto."""
        agrupados = {}

        for venta in datos_cierre:
            for p in venta.get("productos", []):
                try:
                    nombre = str(p[0])
                    cantidad = int(p[1] or 0)
                    precio_unitario = float(p[2] or 0)

                    if nombre not in agrupados:
                        agrupados[nombre] = {
                            "nombre": nombre,
                            "cantidad": 0,
                            "subtotal": 0.0
                        }

                    agrupados[nombre]["cantidad"] += cantidad
                    agrupados[nombre]["subtotal"] += cantidad * precio_unitario
                except Exception:
                    pass

        return list(agrupados.values())

    def generar_pdf_cierre(self, datos_cierre, resumen):
        """Genera PDF compacto del cierre de caja desde el POS."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        ahora = datetime.now()
        carpeta = "cierres_pdf"
        os.makedirs(carpeta, exist_ok=True)
        ruta_pdf = os.path.abspath(
            os.path.join(carpeta, f"Cierre_POS_{ahora.strftime('%d-%m-%Y_%H-%M-%S')}.pdf")
        )

        doc = SimpleDocTemplate(
            ruta_pdf,
            pagesize=letter,
            rightMargin=1.2 * cm,
            leftMargin=1.2 * cm,
            topMargin=1.0 * cm,
            bottomMargin=1.0 * cm
        )

        styles = getSampleStyleSheet()
        titulo_style = ParagraphStyle(
            "TituloCierrePOS",
            parent=styles["Title"],
            fontSize=16,
            leading=18,
            spaceAfter=8
        )
        subtitulo_style = ParagraphStyle(
            "SubtituloCierrePOS",
            parent=styles["Heading2"],
            fontSize=11,
            leading=13,
            spaceBefore=6,
            spaceAfter=4
        )
        normal_style = ParagraphStyle(
            "NormalCompactoPOS",
            parent=styles["Normal"],
            fontSize=8,
            leading=10
        )

        elementos = []
        negocio = self.db.obtener_datos_negocio()
        nombre_negocio = str(negocio.get("nombre_establecimiento", "PlanetBoxer")).upper()

        elementos.append(Paragraph(nombre_negocio, titulo_style))
        elementos.append(Paragraph("CIERRE DE CAJA", subtitulo_style))
        elementos.append(Paragraph(f"Fecha: {ahora.strftime('%d/%m/%Y %H:%M')}", normal_style))
        elementos.append(Spacer(1, 6))

        resumen_data = [[
            "Total vendido", "Tickets", "Productos", "Ganancia real"
        ], [
            formato_moneda(resumen["total"]),
            str(resumen["tickets"]),
            str(resumen["productos"]),
            formato_moneda(resumen["ganancia"])
        ]]

        tabla_resumen = Table(resumen_data, colWidths=[4.3 * cm, 3.3 * cm, 3.3 * cm, 4.3 * cm])
        tabla_resumen.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f222e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
        ]))
        elementos.append(tabla_resumen)
        elementos.append(Spacer(1, 8))

        productos_agrupados = self.agrupar_productos_cierre(datos_cierre)
        if productos_agrupados:
            elementos.append(Paragraph("Productos vendidos agrupados", subtitulo_style))
            data_productos = [["Producto", "Cantidad", "Subtotal"]]
            for item in productos_agrupados:
                data_productos.append([
                    item["nombre"][:45],
                    str(item["cantidad"]),
                    formato_moneda(item["subtotal"])
                ])

            tabla_productos = Table(data_productos, colWidths=[10.2 * cm, 2.5 * cm, 3.5 * cm], repeatRows=1)
            tabla_productos.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#10b981")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                ("ALIGN", (0, 1), (0, -1), "LEFT"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
            ]))
            elementos.append(tabla_productos)
            elementos.append(Spacer(1, 8))

        elementos.append(Paragraph("Detalle por ticket", subtitulo_style))
        data_tickets = [["Ticket", "Hora", "Cajero", "Productos", "Total"]]

        for venta in datos_cierre:
            info = venta.get("info_venta", ())
            prods = venta.get("productos", [])
            descripcion_productos = []

            for p in prods:
                try:
                    descripcion_productos.append(f"{p[1]}x {str(p[0])[:18]}")
                except Exception:
                    pass

            data_tickets.append([
                f"#{info[0]}",
                str(info[1]),
                str(info[4])[:8] if len(info) > 4 else "",
                ", ".join(descripcion_productos)[:55],
                formato_moneda(float(info[2] or 0))
            ])

        tabla_tickets = Table(data_tickets, colWidths=[1.6 * cm, 2.0 * cm, 2.3 * cm, 7.8 * cm, 2.7 * cm], repeatRows=1)
        tabla_tickets.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f222e")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 7),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ALIGN", (3, 1), (3, -1), "LEFT"),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f4f6")]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
        ]))
        elementos.append(tabla_tickets)

        doc.build(elementos)
        return ruta_pdf

    def abrir_archivo(self, ruta):
        """Abre un archivo con la aplicación predeterminada del sistema."""
        if os.name == "nt":
            os.startfile(ruta)
        elif os.name == "posix":
            subprocess.call(["open", ruta])
        else:
            subprocess.call(["xdg-open", ruta])

    def limpiar_venta(self):
        for item in list(self.filas_visuales.values()):
            item["frame"].destroy()

        self.carrito = {}
        self.filas_visuales = {}
        self.recalcular_total()
        self.entry_busqueda.delete(0, 'end')
        self.after(100, lambda: self.entry_busqueda.focus())

    def procesar_pago(self):
        if not self.carrito:
            return

        desea_factura = messagebox.askyesno("Facturación", "¿Desea imprimir el ticket de venta?")

        lista_final = []
        for sku, datos in self.carrito.items():
            lista_final.append({
                'sku': sku,
                'nombre': datos['nombre'],
                'precio': datos['precio'],
                'cantidad': datos['cantidad']
            })

        exito = self.db.registrar_venta(
            lista_final,
            self.total,
            "Venta POS",
            self.usuario_actual
        )

        if exito:
            if desea_factura:
                ruta = self.generar_factura_txt()
                try:
                    subprocess.run(['notepad.exe', '/p', ruta], check=True)
                except Exception:
                    subprocess.Popen(['notepad.exe', ruta])

            messagebox.showinfo("Éxito", f"Venta registrada.\nTotal: {formato_moneda(self.total)}")
            self.limpiar_venta()
        else:
            messagebox.showerror("Error", "No se pudo registrar la venta.")

    def generar_factura_txt(self):
        ahora = datetime.now()
        ruta_completa = os.path.abspath(
            os.path.join("facturas", f"ticket_{ahora.strftime('%Y%m%d_%H%M%S')}.txt")
        )

        negocio = self.db.obtener_datos_negocio()
        nombre = negocio.get("nombre_establecimiento", "PlanetBoxer")
        nit = negocio.get("nit", "")
        ciudad = negocio.get("ciudad", "")
        telefono = negocio.get("telefono", "")

        with open(ruta_completa, "w", encoding="utf-8") as f:
            f.write("================================\n")
            f.write(f"       {nombre}\n")
            if nit:
                f.write(f"   NIT: {nit}\n")
            if ciudad:
                f.write(f"   {ciudad}\n")
            if telefono:
                f.write(f"   Tel: {telefono}\n")
            f.write("================================\n")
            f.write(f"Fecha: {ahora.strftime('%d/%m/%Y %H:%M')}\n")
            f.write("--------------------------------\n")

            for sku, info in self.carrito.items():
                subtotal = info['precio'] * info['cantidad']
                f.write(
                    f"{info['cantidad']:<5} "
                    f"{info['nombre'][:14]:<15} "
                    f"{formato_moneda(subtotal):>10}\n"
                )

            f.write("--------------------------------\n")
            f.write(f"TOTAL: {'':<10}{formato_moneda(self.total)}\n")
            f.write("================================\n")
            f.write("   ¡GRACIAS POR SU COMPRA!\n")
            f.write("================================\n")

        return ruta_completa
