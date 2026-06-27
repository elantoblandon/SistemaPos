import customtkinter as ctk
from tkinter import messagebox, filedialog
from styles import *
from modules.inventario_modal import NuevoProductoModal
import datetime
import os
import shutil
import subprocess
from modules.your_image_pdf_processor import process_invoice

class DashboardFrame(ctk.CTkFrame):
    def __init__(self, master, db, on_config_guardada=None):
        super().__init__(master, fg_color=COLOR_FONDO_CONTENIDO)
        self.db = db
        self.on_config_guardada = on_config_guardada
        self.producto_seleccionado = None
        self.frames_productos = {} 
        
        # --- HEADER ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=30, pady=(20, 10))
        
        self.lbl_titulo = ctk.CTkLabel(
            self.header_frame, text="Panel de Control Administrativo", 
            font=FUERTE_TITULO, text_color=COLOR_TEXTO_PRINCIPAL
        )
        self.lbl_titulo.pack(side="left")

        # --- PESTAÑAS ---
        self.pestanas = ctk.CTkTabview(
            self, segmented_button_selected_color=COLOR_ACENTO,
            segmented_button_unselected_hover_color=COLOR_TARJETAS,
            fg_color="transparent", command=self.al_cambiar_pestana
        )
        self.pestanas.pack(fill="both", expand=True, padx=30, pady=10)
        
        self.tab_stats = self.pestanas.add("📊 Estadísticas")
        self.tab_inventario = self.pestanas.add("📦 Inventario Detallado")
        self.tab_facturas = self.pestanas.add("🧾 Facturas Compras")
        self.tab_usuarios = self.pestanas.add("👥 Usuarios")
        self.tab_config = self.pestanas.add("⚙️ Configuración")

        self.disenar_pestana_estadisticas()
        self.disenar_pestana_inventario()
        self.disenar_pestana_facturas_compra()
        self.disenar_pestana_usuarios()
        self.disenar_pestana_configuracion()

    def al_cambiar_pestana(self):
        tab = self.pestanas.get()
        if tab == "📊 Estadísticas":
            self.actualizar_estadisticas()
        elif tab == "📦 Inventario Detallado":
            self.producto_seleccionado = None
            self.actualizar_tabla_inventario()
        elif tab == "🧾 Facturas Compras":
            self.actualizar_facturas_compra()
        elif tab == "⚙️ Configuración":
            self.cargar_formulario_configuracion()

    # ==========================================================
    # --- PESTAÑA ESTADÍSTICAS ---
    # ==========================================================

    def crear_tarjeta_metrica(self, parent, titulo, valor, color_valor, texto_inicial):
        card = ctk.CTkFrame(parent, fg_color=COLOR_TARJETAS, corner_radius=15, border_width=1, border_color=COLOR_BORDE)
        card.pack(side="left", padx=10, expand=True, fill="both")
        
        ctk.CTkLabel(card, text=titulo, font=FUERTE_TEXTO, text_color=COLOR_TEXTO_SECUNDARIO).pack(pady=(15, 0))
        lbl_valor = ctk.CTkLabel(card, text=valor, font=("Inter", 24, "bold"), text_color=color_valor)
        lbl_valor.pack(pady=(5, 0))
        
        btn_subtexto = ctk.CTkButton(card, text=texto_inicial, font=("Inter", 11, "underline"), 
            text_color=COLOR_ACENTO, fg_color="transparent", hover=False, height=20,
            command=lambda t=titulo: self.mostrar_informe_en_pantalla(t))
        btn_subtexto.pack(pady=(0, 15))
        return {"valor": lbl_valor, "subtexto": btn_subtexto}

    def disenar_pestana_estadisticas(self):
        self.filtros_frame = ctk.CTkFrame(self.tab_stats, fg_color=COLOR_TARJETAS, corner_radius=10)
        self.filtros_frame.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(self.filtros_frame, text="Filtrar por:", font=FUERTE_TEXTO).pack(side="left", padx=20, pady=10)

        self.combo_periodo = ctk.CTkComboBox(self.filtros_frame, values=["Hoy", "Ayer", "fecha", "Mes", "Año"], width=120, command=self.gestionar_visibilidad_filtros)
        self.combo_periodo.set("Hoy")
        self.combo_periodo.pack(side="left", padx=5)

        self.meses_nombres = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        self.combo_mes = ctk.CTkComboBox(self.filtros_frame, values=self.meses_nombres, width=130, command=lambda e: self.actualizar_estadisticas())
        self.combo_anio = ctk.CTkComboBox(self.filtros_frame, values=[str(a) for a in range(2024, 2031)], width=100, command=lambda e: self.actualizar_estadisticas())

        self.btn_cierre = ctk.CTkButton(
            self.filtros_frame,
            text="🔒 Realizar Cierre",
            fg_color="#D35400",
            hover_color="#E67E22",
            width=140,
            font=("Inter", 12, "bold"),
            command=self.generar_cierre_caja_completo
        )
        self.btn_cierre.pack(side="right", padx=20, pady=10)

        self.btn_cierre_semana = ctk.CTkButton(
            self.filtros_frame,
            text="📆 Cierre Últimos 7 días",
            fg_color=COLOR_PRIMARIO,
            hover_color="#2563eb",
            width=190,
            font=("Inter", 12, "bold"),
            command=self.generar_cierre_caja_semanal
        )
        self.btn_cierre_semana.pack(side="right", padx=10, pady=10)

        self.cierre_fecha_frame = ctk.CTkFrame(self.tab_stats, fg_color=COLOR_TARJETAS, corner_radius=10)
        self.cierre_fecha_frame.pack(fill="x", padx=10, pady=(0, 10))

        ctk.CTkLabel(
            self.cierre_fecha_frame,
            text="Cierre de fecha:",
            font=FUERTE_TEXTO
        ).pack(side="left", padx=(20, 8), pady=10)

        self.ent_fecha_cierre = ctk.CTkEntry(
            self.cierre_fecha_frame,
            placeholder_text="DD/MM/AAAA",
            width=120,
            height=35,
            fg_color=COLOR_FONDO_CONTENIDO,
            border_color=COLOR_BORDE
        )
        self.ent_fecha_cierre.pack(side="left", padx=5, pady=10)
        self.ent_fecha_cierre.insert(0, datetime.datetime.now().strftime("%d/%m/%Y"))

        ctk.CTkButton(
            self.cierre_fecha_frame,
            text="📅 Generar cierre del día",
            fg_color=COLOR_ACENTO,
            text_color="#000",
            font=FUERTE_TEXTO_BOLD,
            width=200,
            command=self.generar_cierre_caja_por_fecha
        ).pack(side="left", padx=10, pady=10)

        ctk.CTkLabel(
            self.cierre_fecha_frame,
            text="Seleccione cualquier día anterior o el día de hoy.",
            font=("Inter", 11),
            text_color=COLOR_TEXTO_SECUNDARIO
        ).pack(side="left", padx=5, pady=10)

        cards_container = ctk.CTkFrame(self.tab_stats, fg_color="transparent")
        cards_container.pack(fill="x", pady=10)

        self.metrica_ventas = self.crear_tarjeta_metrica(cards_container, "Ventas Netas", "$ 0", COLOR_ACENTO, "Ver Informe")
        self.metrica_utilidad = self.crear_tarjeta_metrica(cards_container, "Ganancia Real", "$ 0", "#50C878", "Cálculo Neto")
        self.metrica_pedidos = self.crear_tarjeta_metrica(cards_container, "Pedidos", "0", COLOR_PRIMARIO, "Ver Lista")
        self.metrica_stock = self.crear_tarjeta_metrica(cards_container, "Stock Crítico", "0 items", COLOR_PELIGRO, "Ver Agotados")

        self.cuerpo_stats = ctk.CTkFrame(self.tab_stats, fg_color="transparent")
        self.cuerpo_stats.pack(fill="both", expand=True, pady=10)

        self.area_reporte = ctk.CTkFrame(self.cuerpo_stats, fg_color=COLOR_TARJETAS, corner_radius=15)
        self.area_reporte.pack(side="left", fill="both", expand=True, padx=(10, 5))

        self.scroll_reporte = ctk.CTkScrollableFrame(self.area_reporte, fg_color="transparent")
        self.scroll_reporte.pack(fill="both", expand=True, padx=10, pady=10)

        self.area_ranking = ctk.CTkFrame(self.cuerpo_stats, fg_color=COLOR_TARJETAS, corner_radius=15, width=280)
        self.area_ranking.pack(side="right", fill="both", padx=(5, 10))
        self.area_ranking.pack_propagate(False)

        ctk.CTkLabel(self.area_ranking, text="🏆 Top 5 Productos", font=FUERTE_TEXTO_BOLD, text_color=COLOR_ACENTO).pack(pady=15)
        self.contenedor_top = ctk.CTkFrame(self.area_ranking, fg_color="transparent")
        self.contenedor_top.pack(fill="both", expand=True, padx=15)

        self.actualizar_estadisticas()

    def gestionar_visibilidad_filtros(self, eleccion):
        self.combo_mes.pack_forget()
        self.combo_anio.pack_forget()
        if eleccion == "Mes":
            mes_actual = self.meses_nombres[datetime.datetime.now().month - 1]
            self.combo_mes.set(mes_actual)
            self.combo_mes.pack(side="left", padx=5)
        elif eleccion == "Año":
            self.combo_anio.set(str(datetime.datetime.now().year))
            self.combo_anio.pack(side="left", padx=5)
        self.actualizar_estadisticas()

    def parsear_fecha_cierre(self, texto):
        """Convierte DD/MM/AAAA o DD-MM-AAAA a datetime.date. None si es inválida."""
        texto = str(texto or "").strip()
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.datetime.strptime(texto, fmt).date()
            except ValueError:
                continue
        return None

    def _ejecutar_cierre(self, datos_cierre, titulo_resumen, mensaje_sin_datos, fecha_cierre=None):
        """Genera PDF de cierre y muestra resumen en pantalla."""
        for widget in self.scroll_reporte.winfo_children():
            widget.destroy()

        if not datos_cierre:
            messagebox.showwarning("Sin Datos", mensaje_sin_datos)
            return

        resumen = self.calcular_resumen_cierre_desde_datos(datos_cierre)

        try:
            ruta_pdf = self.generar_pdf_cierre(datos_cierre, resumen, fecha_cierre=fecha_cierre)
            self.abrir_archivo(ruta_pdf)
        except ImportError:
            messagebox.showerror(
                "Falta librería",
                "Para generar el cierre en PDF debes instalar reportlab:\n\npip install reportlab"
            )
            return
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo generar el PDF de cierre:\n{e}")
            return

        ctk.CTkLabel(
            self.scroll_reporte,
            text=titulo_resumen,
            font=FUERTE_TEXTO_BOLD,
            text_color=COLOR_PELIGRO
        ).pack(pady=(10, 5))

        resumen_frame = ctk.CTkFrame(self.scroll_reporte, fg_color=COLOR_FONDO_CONTENIDO, corner_radius=10)
        resumen_frame.pack(fill="x", padx=5, pady=(0, 10))

        ctk.CTkLabel(
            resumen_frame,
            text=f"💰 Total: ${resumen['total']:,.0f}",
            font=("Inter", 12, "bold"),
            text_color=COLOR_ACENTO
        ).pack(side="left", padx=10, pady=8)

        ctk.CTkLabel(
            resumen_frame,
            text=f"🧾 Tickets: {resumen['tickets']}",
            font=("Inter", 12, "bold"),
            text_color=COLOR_TEXTO_SECUNDARIO
        ).pack(side="left", padx=10, pady=8)

        ctk.CTkLabel(
            resumen_frame,
            text=f"📦 Productos: {resumen['productos']}",
            font=("Inter", 12, "bold"),
            text_color=COLOR_TEXTO_SECUNDARIO
        ).pack(side="left", padx=10, pady=8)

        ctk.CTkLabel(
            resumen_frame,
            text=f"📈 Ganancia: ${resumen['ganancia']:,.0f}",
            font=("Inter", 12, "bold"),
            text_color="#50C878"
        ).pack(side="left", padx=10, pady=8)

        ctk.CTkLabel(
            self.scroll_reporte,
            text=f"PDF generado: {os.path.basename(ruta_pdf)}",
            font=("Inter", 11),
            text_color=COLOR_TEXTO_SECUNDARIO
        ).pack(pady=(0, 8))

        for venta in datos_cierre:
            info = venta["info_venta"]
            v_frame = ctk.CTkFrame(self.scroll_reporte, fg_color=COLOR_FONDO_CONTENIDO, corner_radius=10)
            v_frame.pack(fill="x", pady=4, padx=5)
            header_v = ctk.CTkFrame(v_frame, fg_color="transparent")
            header_v.pack(fill="x", padx=10, pady=5)
            ctk.CTkLabel(
                header_v,
                text=f"Ticket #{info[0]} | {info[1]} | Caj: {str(info[4])[:8]}",
                font=("Inter", 11, "bold")
            ).pack(side="left")
            ctk.CTkLabel(
                header_v,
                text=f"$ {float(info[2] or 0):,.0f}",
                font=("Inter", 12, "bold"),
                text_color=COLOR_ACENTO
            ).pack(side="right")

    def generar_cierre_caja_completo(self):
        """Genera un cierre de caja compacto en PDF y muestra el resumen en pantalla."""
        ahora = datetime.datetime.now()
        fecha_str = ahora.strftime("%d/%m/%Y")
        datos_cierre = self.db.obtener_datos_cierre_caja()
        self._ejecutar_cierre(
            datos_cierre,
            f"RESUMEN CIERRE {fecha_str}",
            "No hay ventas registradas para el día de hoy.",
            fecha_cierre=ahora.date()
        )

    def generar_cierre_caja_por_fecha(self):
        """Genera cierre de caja para un día específico elegido por el usuario."""
        if not hasattr(self.db, "obtener_datos_cierre_fecha"):
            messagebox.showerror(
                "Función no disponible",
                "Tu database.py aún no tiene la función obtener_datos_cierre_fecha()."
            )
            return

        texto_fecha = self.ent_fecha_cierre.get().strip() if hasattr(self, "ent_fecha_cierre") else ""
        fecha = self.parsear_fecha_cierre(texto_fecha)

        if not fecha:
            messagebox.showwarning(
                "Fecha inválida",
                "Escribe la fecha en formato DD/MM/AAAA.\nEjemplo: 15/04/2026"
            )
            return

        if fecha > datetime.datetime.now().date():
            messagebox.showwarning(
                "Fecha no válida",
                "No puedes generar un cierre de una fecha futura."
            )
            return

        fecha_iso = fecha.strftime("%Y-%m-%d")
        fecha_str = fecha.strftime("%d/%m/%Y")
        datos_cierre = self.db.obtener_datos_cierre_fecha(fecha_iso)

        self._ejecutar_cierre(
            datos_cierre,
            f"RESUMEN CIERRE {fecha_str}",
            f"No hay ventas registradas para el día {fecha_str}.",
            fecha_cierre=fecha
        )

    def generar_cierre_caja_semanal(self):
        """Genera un cierre compacto en PDF para los últimos 7 días (incluyendo hoy)."""
        if not hasattr(self.db, "obtener_datos_cierre_rango"):
            messagebox.showerror(
                "Función no disponible",
                "Tu database.py aún no tiene la función obtener_datos_cierre_rango()."
            )
            return

        datos_cierre = self.db.obtener_datos_cierre_rango(7)
        ahora = datetime.datetime.now()
        inicio = (ahora - datetime.timedelta(days=6)).strftime("%d/%m/%Y")
        fin = ahora.strftime("%d/%m/%Y")

        self._ejecutar_cierre(
            datos_cierre,
            f"RESUMEN CIERRE SEMANAL {inicio} - {fin}",
            "No hay ventas registradas en los últimos 7 días."
        )

    def calcular_resumen_cierre_desde_datos(self, datos_cierre):
        """Calcula el resumen usando exactamente los tickets que se van a imprimir."""
        resumen = {
            "total": 0.0,
            "tickets": len(datos_cierre),
            "productos": 0,
            "ganancia": 0.0
        }

        for venta in datos_cierre:
            info = venta["info_venta"]
            prods = venta["productos"]

            try:
                resumen["total"] += float(info[2] or 0)
            except Exception:
                pass

            for p in prods:
                try:
                    cantidad = int(p[1] or 0)
                    precio_unitario = float(p[2] or 0)
                    resumen["productos"] += cantidad

                    # Si database.obtener_detalles_productos_venta devuelve precio_compra como cuarto dato,
                    # se calcula ganancia real automáticamente.
                    if len(p) >= 4:
                        precio_compra = float(p[3] or 0)
                        resumen["ganancia"] += (precio_unitario - precio_compra) * cantidad
                except Exception:
                    pass

        return resumen

    def agrupar_productos_cierre(self, datos_cierre):
        """Agrupa productos iguales para que el PDF sea más compacto."""
        agrupados = {}

        for venta in datos_cierre:
            for p in venta["productos"]:
                try:
                    nombre = str(p[0])
                    cantidad = int(p[1] or 0)
                    precio_unitario = float(p[2] or 0)
                    subtotal = cantidad * precio_unitario

                    if nombre not in agrupados:
                        agrupados[nombre] = {
                            "nombre": nombre,
                            "cantidad": 0,
                            "subtotal": 0.0
                        }

                    agrupados[nombre]["cantidad"] += cantidad
                    agrupados[nombre]["subtotal"] += subtotal
                except Exception:
                    pass

        return list(agrupados.values())

    def generar_pdf_cierre(self, datos_cierre, resumen, fecha_cierre=None):
        """Genera un PDF compacto del cierre de caja."""
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

        ahora = datetime.datetime.now()
        carpeta = "cierres_pdf"
        os.makedirs(carpeta, exist_ok=True)

        if fecha_cierre:
            fecha_pdf = fecha_cierre.strftime("%d/%m/%Y")
            nombre_archivo = f"Cierre_{fecha_cierre.strftime('%d-%m-%Y')}_{ahora.strftime('%H-%M-%S')}.pdf"
        else:
            fecha_pdf = ahora.strftime("%d/%m/%Y %H:%M")
            nombre_archivo = f"Cierre_{ahora.strftime('%d-%m-%Y_%H-%M-%S')}.pdf"

        ruta_pdf = os.path.abspath(os.path.join(carpeta, nombre_archivo))

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
            "TituloCierre",
            parent=styles["Title"],
            fontSize=16,
            leading=18,
            spaceAfter=8
        )
        subtitulo_style = ParagraphStyle(
            "SubtituloCierre",
            parent=styles["Heading2"],
            fontSize=11,
            leading=13,
            spaceBefore=6,
            spaceAfter=4
        )
        normal_style = ParagraphStyle(
            "NormalCompacto",
            parent=styles["Normal"],
            fontSize=8,
            leading=10
        )

        elementos = []
        negocio = self.db.obtener_datos_negocio()
        nombre_negocio = str(negocio.get("nombre_establecimiento", "PlanetBoxer")).upper()
        elementos.append(Paragraph(nombre_negocio, titulo_style))
        elementos.append(Paragraph("CIERRE DE CAJA", subtitulo_style))
        elementos.append(Paragraph(f"Fecha: {fecha_pdf}", normal_style))
        elementos.append(Spacer(1, 6))

        resumen_data = [[
            "Total vendido", "Tickets", "Productos", "Ganancia real"
        ], [
            f"$ {resumen['total']:,.0f}",
            str(resumen['tickets']),
            str(resumen['productos']),
            f"$ {resumen['ganancia']:,.0f}"
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
                    f"$ {item['subtotal']:,.0f}"
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
            info = venta["info_venta"]
            prods = venta["productos"]
            descripcion_productos = []

            for p in prods:
                try:
                    descripcion_productos.append(f"{p[1]}x {str(p[0])[:18]}")
                except Exception:
                    pass

            data_tickets.append([
                f"#{info[0]}",
                str(info[1]),
                str(info[4])[:8],
                ", ".join(descripcion_productos)[:55],
                f"$ {float(info[2] or 0):,.0f}"
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
    def actualizar_estadisticas(self):
        periodo = self.combo_periodo.get()
        extra = self.combo_mes.get() if periodo == "Mes" else (self.combo_anio.get() if periodo == "Año" else None)
        v, p, s = self.db.obtener_estadisticas_dashboard(periodo, extra)
        u = self.db.obtener_utilidad_periodo(periodo, extra)
        top = self.db.obtener_top_productos(periodo, extra)
        
        self.metrica_ventas["valor"].configure(text=f"$ {v:,.0f}")
        self.metrica_utilidad["valor"].configure(text=f"$ {u:,.0f}")
        self.metrica_pedidos["valor"].configure(text=str(p))
        self.metrica_stock["valor"].configure(text=f"{s} items")

        for w in self.contenedor_top.winfo_children(): w.destroy()
        if top:
            for i, (nombre, cant) in enumerate(top):
                item = ctk.CTkFrame(self.contenedor_top, fg_color=COLOR_FONDO_CONTENIDO, corner_radius=8)
                item.pack(fill="x", pady=3)
                txt = f"{i+1}. {nombre[:18]}..." if len(nombre) > 18 else f"{i+1}. {nombre}"
                ctk.CTkLabel(item, text=txt, font=("Inter", 11)).pack(side="left", padx=10, pady=5)
                ctk.CTkLabel(item, text=f"{int(cant)} ud", font=("Inter", 11, "bold"), text_color=COLOR_ACENTO).pack(side="right", padx=10)

    def mostrar_informe_en_pantalla(self, tipo):
        for widget in self.scroll_reporte.winfo_children(): widget.destroy()
        periodo = self.combo_periodo.get()
        extra = self.combo_mes.get() if periodo == "Mes" else (self.combo_anio.get() if periodo == "Año" else None)
        ctk.CTkLabel(self.scroll_reporte, text=f"DETALLE: {tipo}", font=FUERTE_TEXTO_BOLD, text_color=COLOR_ACENTO).pack(pady=10)
        
        if tipo in ["Ventas Netas", "Pedidos"]:
            datos = self.db.obtener_listado_ventas_periodo(periodo, extra)
            for d in datos:
                venta_id = d[0]
                f = ctk.CTkFrame(self.scroll_reporte, fg_color=COLOR_FONDO_CONTENIDO, cursor="hand2")
                f.pack(fill="x", pady=2, padx=5)
                
                # RE-ACTIVAR CLIC PARA DETALLE
                cmd_detalle = lambda e, v_id=venta_id: self.ver_detalle_venta(v_id)
                f.bind("<Button-1>", cmd_detalle)
                
                lbl_id = ctk.CTkLabel(f, text=f"TKT #{d[0]} - {d[1]}")
                lbl_id.pack(side="left", padx=10)
                lbl_id.bind("<Button-1>", cmd_detalle)
                
                btn_eliminar_venta = ctk.CTkButton(
                    f,
                    text="🗑",
                    width=42,
                    height=28,
                    fg_color="#E74C3C",
                    hover_color="#C0392B",
                    command=lambda v_id=venta_id, t=tipo: self.eliminar_venta_desde_dashboard(v_id, t)
                )
                btn_eliminar_venta.pack(side="right", padx=(5, 10), pady=5)

                lbl_monto = ctk.CTkLabel(f, text=f"$ {d[2]:,.0f}", font=("Inter", 12, "bold"))
                lbl_monto.pack(side="right", padx=10)
                lbl_monto.bind("<Button-1>", cmd_detalle)

        elif tipo == "Stock Crítico":
            prods = self.db.obtener_productos_poco_stock()
            for p in prods:
                f = ctk.CTkFrame(self.scroll_reporte, fg_color=COLOR_FONDO_CONTENIDO)
                f.pack(fill="x", pady=2)
                ctk.CTkLabel(f, text=p[0]).pack(side="left", padx=10)
                ctk.CTkLabel(f, text=f"Stock: {p[1]}", text_color=COLOR_PELIGRO).pack(side="right", padx=10)


    def eliminar_venta_desde_dashboard(self, venta_id, tipo_actual="Ventas Netas"):
        """Elimina una venta/ticket de los reportes sin devolver stock al inventario."""
        if not hasattr(self.db, "eliminar_venta"):
            messagebox.showerror(
                "Función no disponible",
                "Tu database.py aún no tiene la función eliminar_venta().\n"
                "Reemplaza primero el database.py modificado."
            )
            return

        confirmar = messagebox.askyesno(
            "Eliminar venta",
            f"¿Seguro que desea eliminar el Ticket #{venta_id}?\n\n"
            "Esta acción quitará la venta de los reportes de Hoy, Mes y Año.\n"
            "No se devolverá stock al inventario."
        )

        if not confirmar:
            return

        try:
            ok = self.db.eliminar_venta(venta_id)
        except Exception as e:
            messagebox.showerror(
                "Error",
                f"No se pudo eliminar la venta:\n{e}"
            )
            return

        if ok:
            messagebox.showinfo(
                "Venta eliminada",
                f"El Ticket #{venta_id} fue eliminado de los reportes."
            )
            self.actualizar_estadisticas()
            self.mostrar_informe_en_pantalla(tipo_actual)
        else:
            messagebox.showerror(
                "Error",
                "No se pudo eliminar la venta. Revise la consola para más detalles."
            )

    def ver_detalle_venta(self, venta_id):
        """Muestra qué se vendió en un ticket específico"""
        for widget in self.scroll_reporte.winfo_children(): widget.destroy()
        
        btn_volver = ctk.CTkButton(
            self.scroll_reporte, text="← Volver al listado", 
            fg_color="transparent", text_color=COLOR_ACENTO, font=("Inter", 11, "underline"),
            command=lambda: self.mostrar_informe_en_pantalla("Ventas Netas")
        )
        btn_volver.pack(anchor="w", padx=10, pady=5)
        
        ctk.CTkLabel(self.scroll_reporte, text=f"PRODUCTOS DEL TICKET #{venta_id}", font=FUERTE_TEXTO_BOLD).pack(pady=10)
        
        detalles = self.db.obtener_detalles_productos_venta(venta_id)
        if not detalles:
            ctk.CTkLabel(self.scroll_reporte, text="Sin detalles guardados").pack(pady=10)
            return

        for p in detalles:
            f = ctk.CTkFrame(self.scroll_reporte, fg_color=COLOR_FONDO_CONTENIDO)
            f.pack(fill="x", pady=2, padx=10)
            ctk.CTkLabel(f, text=f"{p[1]}x {p[0]}").pack(side="left", padx=10)
            ctk.CTkLabel(f, text=f"$ {p[2]:,.0f}", font=("Inter", 11, "bold")).pack(side="right", padx=10)

    # ==========================================================
    # --- PESTAÑA INVENTARIO ---
    # ==========================================================

    def seleccionar_producto(self, codigo):
        if self.producto_seleccionado in self.frames_productos:
            self.frames_productos[self.producto_seleccionado].configure(fg_color=COLOR_FONDO_CONTENIDO, border_width=0)
        self.producto_seleccionado = codigo
        if codigo in self.frames_productos:
            self.frames_productos[codigo].configure(fg_color=COLOR_SELECCION, border_width=1, border_color=COLOR_ACENTO)

    def disenar_pestana_inventario(self):
        self.toolbar_inv = ctk.CTkFrame(self.tab_inventario, fg_color="transparent")
        self.toolbar_inv.pack(fill="x", padx=10, pady=10)

        self.btn_add = ctk.CTkButton(self.toolbar_inv, text="+ Nuevo Producto", fg_color=COLOR_ACENTO, text_color="#000", font=FUERTE_TEXTO_BOLD, width=160, command=self.abrir_modal_nuevo)
        self.btn_add.pack(side="left", padx=5)

        self.btn_edit = ctk.CTkButton(self.toolbar_inv, text="✎ Editar Seleccionado", fg_color=COLOR_TARJETAS, border_width=1, border_color=COLOR_BORDE, width=160, command=self.ejecutar_editar)
        self.btn_edit.pack(side="left", padx=5)

        self.btn_factura = ctk.CTkButton(
            self.toolbar_inv,
            text="📄 Cargar Factura",
            fg_color=COLOR_PRIMARIO,
            hover_color="#2563eb",
            width=150,
            command=self.cargar_factura_inventario
        )
        self.btn_factura.pack(side="left", padx=5)

        # --- BUSCADOR DE INVENTARIO ---
        # Filtra visualmente por SKU, nombre o categoría sin tocar la base de datos.
        self.ent_buscar_inv = ctk.CTkEntry(
            self.toolbar_inv,
            placeholder_text="Buscar producto, SKU o categoría...",
            width=280,
            height=35,
            fg_color=COLOR_TARJETAS,
            border_color=COLOR_BORDE
        )
        self.ent_buscar_inv.pack(side="left", padx=(12, 5))
        self.ent_buscar_inv.bind("<KeyRelease>", lambda e: self.actualizar_tabla_inventario())

        self.btn_limpiar_busqueda_inv = ctk.CTkButton(
            self.toolbar_inv,
            text="✕",
            width=36,
            height=35,
            fg_color=COLOR_TARJETAS,
            border_width=1,
            border_color=COLOR_BORDE,
            hover_color=COLOR_FONDO_CONTENIDO,
            command=self.limpiar_busqueda_inventario
        )
        self.btn_limpiar_busqueda_inv.pack(side="left", padx=5)

        self.btn_del = ctk.CTkButton(self.toolbar_inv, text="🗑 Eliminar", fg_color="#E74C3C", hover_color="#C0392B", width=100, command=self.ejecutar_eliminar)
        self.btn_del.pack(side="right", padx=5)

        # --- RESUMEN DE INVENTARIO / INVERSIÓN Y VALOR DE VENTA ---
        self.resumen_inv_frame = ctk.CTkFrame(
            self.tab_inventario,
            fg_color=COLOR_TARJETAS,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDE
        )
        self.resumen_inv_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.lbl_inversion_inventario = ctk.CTkLabel(
            self.resumen_inv_frame,
            text="💰 Inversión: $ 0",
            font=("Inter", 15, "bold"),
            text_color=COLOR_ACENTO
        )
        self.lbl_inversion_inventario.pack(side="left", padx=18, pady=12)

        self.lbl_valor_venta_inventario = ctk.CTkLabel(
            self.resumen_inv_frame,
            text="💸 Valor en Venta: $ 0",
            font=("Inter", 15, "bold"),
            text_color=COLOR_PRIMARIO
        )
        self.lbl_valor_venta_inventario.pack(side="left", padx=18, pady=12)

        self.lbl_ganancia_potencial_inventario = ctk.CTkLabel(
            self.resumen_inv_frame,
            text="📈 Ganancia Potencial: $ 0",
            font=("Inter", 13, "bold"),
            text_color="#50C878"
        )
        self.lbl_ganancia_potencial_inventario.pack(side="left", padx=18, pady=12)

        self.lbl_unidades_inventario = ctk.CTkLabel(
            self.resumen_inv_frame,
            text="📦 Unidades: 0",
            font=("Inter", 13, "bold"),
            text_color=COLOR_TEXTO_SECUNDARIO
        )
        self.lbl_unidades_inventario.pack(side="right", padx=18, pady=12)

        self.capa_titulos = ctk.CTkFrame(self.tab_inventario, fg_color=COLOR_TARJETAS, height=35, corner_radius=5)
        self.capa_titulos.pack(fill="x", padx=10, pady=(10, 0))
        
        titulos = [
            ("SKU", 0.02),
            ("Descripción del Producto", 0.15),
            ("Categoría", 0.40),
            ("Stock", 0.55),
            ("P. Compra", 0.70),
            ("P. Venta", 0.84)
        ]
        for texto, pos in titulos:
            lbl = ctk.CTkLabel(self.capa_titulos, text=texto, font=("Inter", 11, "bold"), text_color=COLOR_TEXTO_SECUNDARIO)
            lbl.place(relx=pos, rely=0.5, anchor="w")

        self.lbl_resultados_busqueda_inv = ctk.CTkLabel(
            self.tab_inventario,
            text="",
            font=("Inter", 11),
            text_color=COLOR_TEXTO_SECUNDARIO
        )
        self.lbl_resultados_busqueda_inv.pack(anchor="w", padx=14, pady=(3, 0))

        self.scroll_inv = ctk.CTkScrollableFrame(self.tab_inventario, fg_color="transparent")
        self.scroll_inv.pack(fill="both", expand=True, padx=5, pady=5)
        self.actualizar_tabla_inventario()

    def normalizar_busqueda_inventario(self, texto):
        """Normaliza texto para buscar sin importar mayúsculas, tildes o espacios dobles."""
        texto = str(texto or "").lower().strip()
        reemplazos = {
            "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"
        }
        for original, nuevo in reemplazos.items():
            texto = texto.replace(original, nuevo)
        return " ".join(texto.split())

    def obtener_categoria_desde_producto_lista(self, producto):
        """Soporta productos en formato nuevo o viejo para sacar la categoría."""
        try:
            if len(producto) >= 6:
                return producto[5]
            if len(producto) >= 5:
                return producto[4]
        except Exception:
            pass
        return ""

    def producto_coincide_busqueda(self, producto, busqueda):
        """Filtra por SKU, nombre o categoría. Todas las palabras escritas deben coincidir."""
        busqueda = self.normalizar_busqueda_inventario(busqueda)
        if not busqueda:
            return True

        codigo = producto[0] if len(producto) > 0 else ""
        nombre = producto[1] if len(producto) > 1 else ""
        categoria = self.obtener_categoria_desde_producto_lista(producto)

        texto_producto = self.normalizar_busqueda_inventario(
            f"{codigo} {nombre} {categoria}"
        )

        return all(palabra in texto_producto for palabra in busqueda.split())

    def limpiar_busqueda_inventario(self):
        """Limpia el buscador y vuelve a mostrar todo el inventario."""
        if hasattr(self, "ent_buscar_inv"):
            self.ent_buscar_inv.delete(0, "end")
        self.actualizar_tabla_inventario()

    def actualizar_tabla_inventario(self):
        for widget in self.scroll_inv.winfo_children(): widget.destroy()
        self.frames_productos = {} 
        productos = self.db.obtener_productos()

        # El resumen se calcula con TODO el inventario.
        # El filtro solo afecta la tabla visual, no modifica datos.
        productos_totales = productos
        self.actualizar_resumen_inventario(productos_totales)

        busqueda = ""
        if hasattr(self, "ent_buscar_inv"):
            busqueda = self.ent_buscar_inv.get().strip()

        if busqueda:
            productos = [p for p in productos_totales if self.producto_coincide_busqueda(p, busqueda)]
        else:
            productos = productos_totales

        if hasattr(self, "lbl_resultados_busqueda_inv"):
            if busqueda:
                self.lbl_resultados_busqueda_inv.configure(
                    text=f"Mostrando {len(productos)} de {len(productos_totales)} productos para: '{busqueda}'"
                )
            else:
                self.lbl_resultados_busqueda_inv.configure(text=f"Mostrando {len(productos_totales)} productos")

        if self.producto_seleccionado and not any(p[0] == self.producto_seleccionado for p in productos):
            self.producto_seleccionado = None
        
        for p in productos:
            codigo_p = p[0]
            nombre_p = p[1]
            stock_p = int(p[2] or 0)

            # Soporta dos formatos de obtener_productos():
            # Formato nuevo: (codigo, nombre, stock, precio_compra, precio_venta, categoria)
            # Formato viejo:  (codigo, nombre, stock, precio_venta, categoria)
            if len(p) >= 6:
                precio_compra_p = float(p[3] or 0)
                precio_venta_p = float(p[4] or 0)
                categoria_p = p[5]
            else:
                datos_full = self.db.obtener_producto_por_codigo(codigo_p)
                if datos_full:
                    precio_compra_p = float(datos_full[2] or 0)
                    precio_venta_p = float(datos_full[3] or 0)
                    categoria_p = datos_full[5] if len(datos_full) > 5 else ""
                else:
                    precio_compra_p = 0.0
                    precio_venta_p = float(p[3] or 0)
                    categoria_p = p[4] if len(p) > 4 else ""

            f = ctk.CTkFrame(self.scroll_inv, fg_color=COLOR_FONDO_CONTENIDO, height=50, cursor="hand2")
            f.pack(fill="x", pady=2, padx=5)
            self.frames_productos[codigo_p] = f
            
            cmd_seleccionar = lambda e, c=codigo_p: self.seleccionar_producto(c)
            f.bind("<Button-1>", cmd_seleccionar)

            lbl_sku = ctk.CTkLabel(f, text=codigo_p, font=("Inter", 11, "bold"), text_color=COLOR_ACENTO)
            lbl_sku.place(relx=0.02, rely=0.5, anchor="w")
            lbl_sku.bind("<Button-1>", cmd_seleccionar)

            lbl_nom = ctk.CTkLabel(f, text=nombre_p, font=("Inter", 12), anchor="w")
            lbl_nom.place(relx=0.15, rely=0.5, anchor="w")
            lbl_nom.bind("<Button-1>", cmd_seleccionar)

            lbl_cat = ctk.CTkLabel(f, text=str(categoria_p).upper(), font=("Inter", 10), text_color=COLOR_TEXTO_SECUNDARIO)
            lbl_cat.place(relx=0.40, rely=0.5, anchor="w")
            lbl_cat.bind("<Button-1>", cmd_seleccionar)
            
            color_s = COLOR_PELIGRO if stock_p <= 5 else "#50C878"
            lbl_stock = ctk.CTkLabel(f, text=f"{stock_p} Unid.", font=("Inter", 11, "bold"), text_color=color_s)
            lbl_stock.place(relx=0.55, rely=0.5, anchor="w")
            lbl_stock.bind("<Button-1>", cmd_seleccionar)

            lbl_compra = ctk.CTkLabel(
                f,
                text=f"$ {precio_compra_p:,.0f}",
                font=("Inter", 12, "bold"),
                text_color=COLOR_TEXTO_SECUNDARIO
            )
            lbl_compra.place(relx=0.70, rely=0.5, anchor="w")
            lbl_compra.bind("<Button-1>", cmd_seleccionar)

            lbl_venta = ctk.CTkLabel(f, text=f"$ {precio_venta_p:,.0f}", font=("Inter", 12, "bold"))
            lbl_venta.place(relx=0.84, rely=0.5, anchor="w")
            lbl_venta.bind("<Button-1>", cmd_seleccionar)

    def actualizar_resumen_inventario(self, productos=None):
        """Actualiza inversión, valor de venta, ganancia potencial y unidades disponibles."""
        try:
            valor_compra = 0.0
            valor_venta = 0.0
            ganancia_potencial = 0.0
            total_unidades = 0

            if hasattr(self.db, "obtener_resumen_inventario"):
                resumen = self.db.obtener_resumen_inventario()
                valor_compra = float(resumen.get("valor_compra", 0) or 0)
                valor_venta = float(resumen.get("valor_venta", 0) or 0)
                ganancia_potencial = float(resumen.get("ganancia_potencial", valor_venta - valor_compra) or 0)
                total_unidades = int(resumen.get("total_unidades", 0) or 0)

            elif hasattr(self.db, "obtener_valores_inventario"):
                valor_compra, valor_venta = self.db.obtener_valores_inventario()
                valor_compra = float(valor_compra or 0)
                valor_venta = float(valor_venta or 0)
                ganancia_potencial = valor_venta - valor_compra

                if productos is None:
                    productos = self.db.obtener_productos()

                total_unidades = sum(int(p[2] or 0) for p in productos)

            else:
                if productos is None:
                    productos = self.db.obtener_productos()

                total_unidades = sum(int(p[2] or 0) for p in productos)

                for p in productos:
                    datos = self.db.obtener_producto_por_codigo(p[0])
                    if datos:
                        precio_compra = float(datos[2] or 0)
                        precio_venta = float(datos[3] or 0)
                        stock = int(datos[4] or 0)
                        valor_compra += precio_compra * stock
                        valor_venta += precio_venta * stock

                ganancia_potencial = valor_venta - valor_compra

            if hasattr(self, "lbl_inversion_inventario"):
                self.lbl_inversion_inventario.configure(text=f"💰 Inversión: $ {valor_compra:,.0f}")

            if hasattr(self, "lbl_valor_venta_inventario"):
                self.lbl_valor_venta_inventario.configure(text=f"💸 Valor en Venta: $ {valor_venta:,.0f}")

            if hasattr(self, "lbl_ganancia_potencial_inventario"):
                self.lbl_ganancia_potencial_inventario.configure(text=f"📈 Ganancia Potencial: $ {ganancia_potencial:,.0f}")

            if hasattr(self, "lbl_unidades_inventario"):
                self.lbl_unidades_inventario.configure(text=f"📦 Unidades: {total_unidades:,}")

        except Exception as e:
            print(f"Error actualizando resumen de inventario: {e}")
            if hasattr(self, "lbl_inversion_inventario"):
                self.lbl_inversion_inventario.configure(text="💰 Inversión: Error")
            if hasattr(self, "lbl_valor_venta_inventario"):
                self.lbl_valor_venta_inventario.configure(text="💸 Valor en Venta: Error")
            if hasattr(self, "lbl_ganancia_potencial_inventario"):
                self.lbl_ganancia_potencial_inventario.configure(text="📈 Ganancia Potencial: Error")
            if hasattr(self, "lbl_unidades_inventario"):
                self.lbl_unidades_inventario.configure(text="📦 Unidades: Error")

    def ejecutar_editar(self):
        if not self.producto_seleccionado:
            messagebox.showwarning("Atención", "Seleccione un producto de la tabla para editar.")
            return
        datos = self.db.obtener_producto_por_codigo(self.producto_seleccionado)
        if datos:
            NuevoProductoModal(self, self.db, self.actualizar_tabla_inventario, producto_data=datos)

    def ejecutar_eliminar(self):
        if not self.producto_seleccionado:
            messagebox.showwarning("Atención", "Seleccione un producto para eliminar.")
            return
        if messagebox.askyesno("Confirmar", f"¿Eliminar permanentemente {self.producto_seleccionado}?"):
            if self.db.eliminar_producto(self.producto_seleccionado):
                self.producto_seleccionado = None
                self.actualizar_tabla_inventario()

    def cargar_factura_inventario(self):
        """Permite seleccionar una factura en PDF/imagen y revisar los productos detectados."""
        file_path = filedialog.askopenfilename(
            title="Seleccionar factura",
            filetypes=(
                ("Facturas PDF o imagen", "*.pdf;*.png;*.jpg;*.jpeg"),
                ("Archivos PDF", "*.pdf"),
                ("Imágenes", "*.png;*.jpg;*.jpeg")
            )
        )

        if not file_path:
            return

        try:
            productos_detectados = process_invoice(file_path)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo leer la factura:\n{e}")
            return

        productos_normalizados = self.normalizar_productos_factura(productos_detectados)

        if not productos_normalizados:
            messagebox.showwarning(
                "Sin productos",
                "No se detectaron productos en la factura. Revise que el archivo sea claro o que el PDF tenga texto legible."
            )
            return

        self.mostrar_modal_revision_factura(productos_normalizados, file_path)

    def normalizar_productos_factura(self, productos_detectados):
        """
        Acepta varios formatos posibles del procesador:
        - [(nombre, cantidad), ...]
        - [{"nombre": ..., "cantidad": ...}, ...]
        - [{"codigo": ..., "nombre": ..., "cantidad": ...}, ...]
        Y devuelve una lista uniforme de diccionarios.
        """
        normalizados = []

        for item in productos_detectados:
            nombre = ""
            codigo = ""
            cantidad = 0

            if isinstance(item, dict):
                nombre = str(item.get("nombre", "")).strip()
                codigo = str(item.get("codigo", "")).strip()
                cantidad = item.get("cantidad", 0)
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                nombre = str(item[0]).strip()
                cantidad = item[1]
            else:
                continue

            try:
                cantidad = int(float(str(cantidad).replace(",", ".").strip()))
            except:
                cantidad = 0

            if cantidad <= 0:
                continue

            if nombre or codigo:
                normalizados.append({
                    "codigo": codigo,
                    "nombre": nombre,
                    "cantidad": cantidad
                })

        return normalizados

    def buscar_producto_factura(self, codigo, nombre):
        """Busca un producto existente por código o por nombre aproximado, sin crear productos nuevos."""
        producto = None
        codigo = str(codigo or "").strip()
        nombre = str(nombre or "").strip()

        try:
            if codigo:
                producto = self.db.obtener_producto_por_codigo(codigo)

            if not producto and nombre:
                producto = self.db.obtener_producto_por_codigo(nombre)

            if not producto and nombre and hasattr(self.db, "buscar_producto_por_nombre_aproximado"):
                producto = self.db.buscar_producto_por_nombre_aproximado(nombre)
        except Exception as e:
            print(f"Error buscando producto de factura: {e}")
            producto = None

        return producto

    def obtener_stock_producto_db(self, producto_db):
        """Obtiene el stock desde la tupla devuelta por obtener_producto_por_codigo."""
        try:
            if producto_db and len(producto_db) >= 5:
                return int(producto_db[4] or 0)
        except Exception:
            pass
        return 0

    def mostrar_modal_revision_factura(self, productos, archivo_origen=""):
        """Muestra una ventana para revisar lo detectado antes de sumarlo y guardarlo como factura digitalizada."""
        modal = ctk.CTkToplevel(self)
        modal.title("Revisar Factura de Compra")
        modal.geometry("1120x620")
        modal.configure(fg_color=COLOR_TARJETAS)
        modal.grab_set()
        modal.lift()

        ctk.CTkLabel(
            modal,
            text="PRODUCTOS DETECTADOS EN LA FACTURA",
            font=FUERTE_SUBTITULO,
            text_color=COLOR_ACENTO
        ).pack(pady=(18, 5))

        ctk.CTkLabel(
            modal,
            text="Valide productos, cantidades y precio de compra. Solo se sumará stock a productos existentes.",
            font=FUERTE_TEXTO,
            text_color=COLOR_TEXTO_SECUNDARIO
        ).pack(pady=(0, 8))

        info_frame = ctk.CTkFrame(modal, fg_color=COLOR_FONDO_CONTENIDO, corner_radius=10)
        info_frame.pack(fill="x", padx=20, pady=(0, 8))
        info_frame.grid_columnconfigure(1, weight=1)
        info_frame.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(info_frame, text="Proveedor:", font=("Inter", 11, "bold")).grid(row=0, column=0, padx=(12, 5), pady=8, sticky="w")
        ent_proveedor = ctk.CTkEntry(info_frame, height=32, fg_color=COLOR_TARJETAS, border_color=COLOR_BORDE)
        ent_proveedor.insert(0, "Proveedor no especificado")
        ent_proveedor.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

        ctk.CTkLabel(info_frame, text="Archivo:", font=("Inter", 11, "bold")).grid(row=0, column=2, padx=(12, 5), pady=8, sticky="w")
        ctk.CTkLabel(
            info_frame,
            text=os.path.basename(archivo_origen) if archivo_origen else "Sin archivo",
            font=("Inter", 11),
            text_color=COLOR_TEXTO_SECUNDARIO
        ).grid(row=0, column=3, padx=5, pady=8, sticky="w")

        resumen_detectados = ctk.CTkFrame(modal, fg_color=COLOR_FONDO_CONTENIDO, corner_radius=10)
        resumen_detectados.pack(fill="x", padx=20, pady=(0, 10))

        contenedor = ctk.CTkScrollableFrame(modal, fg_color=COLOR_FONDO_CONTENIDO, corner_radius=12)
        contenedor.pack(fill="both", expand=True, padx=20, pady=8)

        filas = []
        encontrados = 0
        pendientes = 0

        header = ctk.CTkFrame(contenedor, fg_color=COLOR_TARJETAS, height=35)
        header.pack(fill="x", pady=(0, 5))
        header.grid_columnconfigure(0, weight=3)
        header.grid_columnconfigure(1, weight=1)
        header.grid_columnconfigure(2, weight=1)
        header.grid_columnconfigure(3, weight=1)
        header.grid_columnconfigure(4, weight=1)
        header.grid_columnconfigure(5, weight=1)
        header.grid_columnconfigure(6, weight=1)
        header.grid_columnconfigure(7, weight=0, minsize=55)

        ctk.CTkLabel(header, text="Producto detectado / corregible", font=("Inter", 10, "bold")).grid(row=0, column=0, padx=8, pady=8, sticky="w")
        ctk.CTkLabel(header, text="Cant.", font=("Inter", 10, "bold")).grid(row=0, column=1, padx=5, pady=8)
        ctk.CTkLabel(header, text="P. Compra", font=("Inter", 10, "bold")).grid(row=0, column=2, padx=5, pady=8)
        ctk.CTkLabel(header, text="Subtotal", font=("Inter", 10, "bold")).grid(row=0, column=3, padx=5, pady=8)
        ctk.CTkLabel(header, text="Stock", font=("Inter", 10, "bold")).grid(row=0, column=4, padx=5, pady=8)
        ctk.CTkLabel(header, text="Nuevo", font=("Inter", 10, "bold")).grid(row=0, column=5, padx=5, pady=8)
        ctk.CTkLabel(header, text="Estado", font=("Inter", 10, "bold")).grid(row=0, column=6, padx=5, pady=8)
        ctk.CTkLabel(header, text="Quitar", font=("Inter", 10, "bold")).grid(row=0, column=7, padx=5, pady=8)

        lbl_total_factura = ctk.CTkLabel(
            resumen_detectados,
            text="Total inversión detectada: $ 0",
            font=("Inter", 12, "bold"),
            text_color=COLOR_ACENTO
        )
        lbl_total_factura.pack(side="right", padx=12, pady=8)

        def formato_valor(valor):
            try:
                return f"$ {float(valor or 0):,.0f}"
            except Exception:
                return "$ 0"

        lbl_estado_resumen = None

        def recalcular_totales():
            total = 0.0
            encontrados_actuales = 0
            pendientes_actuales = 0

            for fila_data in filas:
                try:
                    cant = int(float(fila_data["cantidad_entry"].get().replace(",", ".")))
                    precio = float(fila_data["precio_entry"].get().replace(",", "."))
                    subtotal = max(cant, 0) * max(precio, 0)
                except Exception:
                    subtotal = 0.0

                fila_data["subtotal_label"].configure(text=formato_valor(subtotal))

                producto_db = fila_data.get("producto_db")
                if producto_db:
                    encontrados_actuales += 1
                else:
                    pendientes_actuales += 1

                stock_actual = int(fila_data.get("stock_actual", 0) or 0)
                if producto_db:
                    try:
                        cant_ok = int(float(fila_data["cantidad_entry"].get().replace(",", ".")))
                        fila_data["nuevo_stock_label"].configure(text=str(stock_actual + max(cant_ok, 0)), text_color="#50C878")
                    except Exception:
                        fila_data["nuevo_stock_label"].configure(text="-", text_color=COLOR_TEXTO_SECUNDARIO)
                else:
                    fila_data["nuevo_stock_label"].configure(text="-", text_color=COLOR_TEXTO_SECUNDARIO)

                total += subtotal

            lbl_total_factura.configure(text=f"Total inversión detectada: {formato_valor(total)}")
            if lbl_estado_resumen:
                lbl_estado_resumen.configure(
                    text=f"Detectados: {len(filas)}  |  Encontrados: {encontrados_actuales}  |  Pendientes: {pendientes_actuales}",
                    text_color=COLOR_ACENTO if encontrados_actuales else COLOR_PELIGRO
                )

        def quitar_fila_factura(fila_data):
            if fila_data in filas:
                filas.remove(fila_data)
            try:
                fila_data["frame"].destroy()
            except Exception:
                pass
            recalcular_totales()

        for prod in productos:
            nombre = prod.get("nombre", "").strip()
            codigo = prod.get("codigo", "").strip()
            cantidad = prod.get("cantidad", 0)

            producto_db = self.buscar_producto_factura(codigo, nombre)
            texto_busqueda = codigo or nombre
            stock_actual = self.obtener_stock_producto_db(producto_db)

            try:
                precio_compra_default = float(prod.get("precio_compra", 0) or 0)
            except Exception:
                precio_compra_default = 0.0

            if precio_compra_default <= 0 and producto_db:
                try:
                    precio_compra_default = float(producto_db[2] or 0)
                except Exception:
                    precio_compra_default = 0.0

            if producto_db:
                encontrados += 1
                estado = f"Encontrado: {producto_db[1]}"
                color_estado = COLOR_ACENTO
            else:
                pendientes += 1
                estado = "No encontrado"
                color_estado = COLOR_PELIGRO

            fila = ctk.CTkFrame(contenedor, fg_color="transparent")
            fila.pack(fill="x", pady=3)
            fila.grid_columnconfigure(0, weight=3)
            fila.grid_columnconfigure(1, weight=1)
            fila.grid_columnconfigure(2, weight=1)
            fila.grid_columnconfigure(3, weight=1)
            fila.grid_columnconfigure(4, weight=1)
            fila.grid_columnconfigure(5, weight=1)
            fila.grid_columnconfigure(6, weight=1)
            fila.grid_columnconfigure(7, weight=0, minsize=55)

            ent_nombre = ctk.CTkEntry(fila, height=35, fg_color=COLOR_TARJETAS, border_color=COLOR_BORDE)
            ent_nombre.insert(0, texto_busqueda)
            ent_nombre.grid(row=0, column=0, padx=6, pady=4, sticky="ew")

            ent_cantidad = ctk.CTkEntry(fila, height=35, width=70, fg_color=COLOR_TARJETAS, border_color=COLOR_BORDE)
            ent_cantidad.insert(0, str(cantidad))
            ent_cantidad.grid(row=0, column=1, padx=5, pady=4)

            ent_precio = ctk.CTkEntry(fila, height=35, width=90, fg_color=COLOR_TARJETAS, border_color=COLOR_BORDE)
            ent_precio.insert(0, str(int(precio_compra_default)) if precio_compra_default else "0")
            ent_precio.grid(row=0, column=2, padx=5, pady=4)

            lbl_subtotal = ctk.CTkLabel(fila, text="$ 0", font=("Inter", 10, "bold"), text_color=COLOR_ACENTO)
            lbl_subtotal.grid(row=0, column=3, padx=5, pady=4)

            lbl_stock_actual = ctk.CTkLabel(
                fila,
                text=str(stock_actual) if producto_db else "-",
                font=("Inter", 10, "bold"),
                text_color=COLOR_TEXTO_SECUNDARIO
            )
            lbl_stock_actual.grid(row=0, column=4, padx=5, pady=4)

            lbl_nuevo_stock = ctk.CTkLabel(
                fila,
                text=str(stock_actual + int(float(str(cantidad).replace(",", ".")))) if producto_db else "-",
                font=("Inter", 10, "bold"),
                text_color="#50C878" if producto_db else COLOR_TEXTO_SECUNDARIO
            )
            lbl_nuevo_stock.grid(row=0, column=5, padx=5, pady=4)

            lbl_estado = ctk.CTkLabel(fila, text=estado, text_color=color_estado, font=("Inter", 9, "bold"))
            lbl_estado.grid(row=0, column=6, padx=5, pady=4, sticky="w")

            btn_quitar = ctk.CTkButton(
                fila,
                text="🗑",
                width=38,
                height=30,
                fg_color="#E74C3C",
                hover_color="#C0392B"
            )
            btn_quitar.grid(row=0, column=7, padx=5, pady=4)

            fila_data = {
                "nombre_entry": ent_nombre,
                "cantidad_entry": ent_cantidad,
                "precio_entry": ent_precio,
                "producto_db": producto_db,
                "stock_actual": stock_actual,
                "estado_label": lbl_estado,
                "stock_actual_label": lbl_stock_actual,
                "nuevo_stock_label": lbl_nuevo_stock,
                "subtotal_label": lbl_subtotal,
                "frame": fila
            }
            btn_quitar.configure(command=lambda fd=fila_data: quitar_fila_factura(fd))
            filas.append(fila_data)

            ent_cantidad.bind("<KeyRelease>", lambda e: recalcular_totales())
            ent_precio.bind("<KeyRelease>", lambda e: recalcular_totales())

        lbl_estado_resumen = ctk.CTkLabel(
            resumen_detectados,
            text=f"Detectados: {len(productos)}  |  Encontrados: {encontrados}  |  Pendientes: {pendientes}",
            font=("Inter", 12, "bold"),
            text_color=COLOR_ACENTO if encontrados else COLOR_PELIGRO
        )
        lbl_estado_resumen.pack(side="left", padx=12, pady=8)

        if pendientes:
            ctk.CTkLabel(
                resumen_detectados,
                text="Los pendientes se guardan en la factura, pero NO suman stock.",
                font=("Inter", 11),
                text_color=COLOR_TEXTO_SECUNDARIO
            ).pack(side="left", padx=12, pady=8)

        acciones = ctk.CTkFrame(modal, fg_color="transparent")
        acciones.pack(fill="x", padx=20, pady=(5, 20))

        ctk.CTkButton(
            acciones,
            text="Cancelar",
            fg_color=COLOR_TARJETAS,
            border_width=1,
            border_color=COLOR_BORDE,
            command=modal.destroy
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            acciones,
            text="Validar de nuevo",
            fg_color=COLOR_PRIMARIO,
            hover_color="#2563eb",
            command=lambda: self.revalidar_filas_factura(filas)
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            acciones,
            text="Aplicar y Guardar Factura",
            fg_color=COLOR_ACENTO,
            text_color="#000",
            font=FUERTE_TEXTO_BOLD,
            command=lambda: self.aplicar_factura_al_inventario(filas, modal, archivo_origen, ent_proveedor.get())
        ).pack(side="right", padx=5)

        recalcular_totales()

    def revalidar_filas_factura(self, filas):
        """Vuelve a buscar los productos después de que el usuario corrija nombres/códigos en el modal."""
        for fila in filas:
            texto_producto = fila["nombre_entry"].get().strip()
            producto_db = self.buscar_producto_factura("", texto_producto)
            fila["producto_db"] = producto_db
            stock_actual = self.obtener_stock_producto_db(producto_db)
            fila["stock_actual"] = stock_actual

            try:
                cantidad = int(float(fila["cantidad_entry"].get().replace(",", ".")))
            except Exception:
                cantidad = 0

            if producto_db:
                fila["estado_label"].configure(text=f"Encontrado: {producto_db[1]}", text_color=COLOR_ACENTO)
                fila["stock_actual_label"].configure(text=str(stock_actual), text_color=COLOR_TEXTO_SECUNDARIO)
                fila["nuevo_stock_label"].configure(text=str(stock_actual + max(cantidad, 0)), text_color="#50C878")

                try:
                    precio_actual = float(fila["precio_entry"].get().replace(",", "."))
                except Exception:
                    precio_actual = 0

                if precio_actual <= 0:
                    try:
                        fila["precio_entry"].delete(0, "end")
                        fila["precio_entry"].insert(0, str(int(float(producto_db[2] or 0))))
                    except Exception:
                        pass
            else:
                fila["estado_label"].configure(text="No encontrado", text_color=COLOR_PELIGRO)
                fila["stock_actual_label"].configure(text="-", text_color=COLOR_TEXTO_SECUNDARIO)
                fila["nuevo_stock_label"].configure(text="-", text_color=COLOR_TEXTO_SECUNDARIO)

    def aplicar_factura_al_inventario(self, filas, modal, archivo_origen="", proveedor=""):
        """Suma stock a productos existentes y guarda la factura digitalizada."""
        actualizados = 0
        omitidos = []
        cambios = []
        productos_para_guardar = []

        if not messagebox.askyesno(
            "Confirmar actualización",
            "¿Desea guardar esta factura y sumar al inventario únicamente los productos encontrados?\n\n"
            "Los productos no encontrados se guardarán como pendientes, pero no se creará nada nuevo."
        ):
            return

        for fila in filas:
            texto_producto = fila["nombre_entry"].get().strip()
            cantidad_txt = fila["cantidad_entry"].get().strip()
            precio_txt = fila["precio_entry"].get().strip()

            try:
                cantidad = int(float(cantidad_txt.replace(",", ".")))
            except Exception:
                cantidad = 0

            try:
                precio_compra = float(precio_txt.replace(",", "."))
            except Exception:
                precio_compra = 0.0

            if cantidad <= 0:
                omitidos.append(f"{texto_producto} (cantidad inválida)")
                continue

            producto_db = fila.get("producto_db")
            if not producto_db:
                producto_db = self.buscar_producto_factura("", texto_producto)

            encontrado = bool(producto_db)
            codigo = producto_db[0] if producto_db else ""
            nombre_db = producto_db[1] if producto_db else texto_producto
            stock_anterior = self.obtener_stock_producto_db(producto_db) if producto_db else 0

            productos_para_guardar.append({
                "codigo": codigo,
                "nombre": nombre_db,
                "cantidad": cantidad,
                "precio_compra": precio_compra,
                "subtotal": cantidad * precio_compra,
                "encontrado": 1 if encontrado else 0
            })

            if not producto_db:
                omitidos.append(texto_producto)
                continue

            try:
                if hasattr(self.db, "sumar_stock_producto"):
                    ok = self.db.sumar_stock_producto(codigo, cantidad)
                else:
                    datos_actuales = self.db.obtener_producto_por_codigo(codigo)
                    if not datos_actuales:
                        omitidos.append(texto_producto)
                        continue

                    stock_anterior = self.obtener_stock_producto_db(datos_actuales)
                    nuevo_stock = stock_anterior + cantidad
                    ok = self.db.actualizar_producto(
                        datos_actuales[0],
                        datos_actuales[1],
                        datos_actuales[2],
                        datos_actuales[3],
                        nuevo_stock,
                        datos_actuales[5]
                    )

                if ok:
                    actualizados += 1
                    cambios.append(f"{nombre_db}: {stock_anterior} + {cantidad} = {stock_anterior + cantidad}")
                else:
                    omitidos.append(texto_producto)

            except Exception as e:
                omitidos.append(f"{texto_producto} ({e})")

        factura_id = None
        if hasattr(self.db, "guardar_factura_compra"):
            try:
                factura_id = self.db.guardar_factura_compra(
                    archivo=os.path.basename(archivo_origen) if archivo_origen else "",
                    proveedor=proveedor or "Proveedor no especificado",
                    productos=productos_para_guardar,
                    observacion="Factura digitalizada desde inventario"
                )
            except Exception as e:
                messagebox.showwarning(
                    "Factura no guardada",
                    f"El stock pudo haberse actualizado, pero no se pudo guardar el historial de la factura:\n{e}"
                )
        else:
            messagebox.showwarning(
                "Historial no disponible",
                "Tu database.py aún no tiene las tablas/métodos de facturas de compra. Se aplicará stock, pero no se guardará el historial."
            )

        self.actualizar_tabla_inventario()
        if hasattr(self, "actualizar_facturas_compra"):
            self.actualizar_facturas_compra()
        modal.destroy()

        mensaje = f"Productos con stock actualizado: {actualizados}"
        if factura_id:
            mensaje += f"\nFactura guardada con ID: {factura_id}"

        if cambios:
            mensaje += "\n\nCambios aplicados:\n- " + "\n- ".join(cambios[:8])
            if len(cambios) > 8:
                mensaje += f"\n... y {len(cambios) - 8} más"

        if omitidos:
            mensaje += "\n\nOmitidos/no encontrados:\n- " + "\n- ".join(omitidos[:10])
            if len(omitidos) > 10:
                mensaje += f"\n... y {len(omitidos) - 10} más"

        messagebox.showinfo("Factura procesada", mensaje)

    def abrir_factura_manual(self):
        """Abre una factura de compra manual para sumar stock y guardar historial."""
        modal = ctk.CTkToplevel(self)
        modal.title("Factura Manual de Compra")
        modal.geometry("1120x620")
        modal.configure(fg_color=COLOR_TARJETAS)
        modal.grab_set()
        modal.lift()

        ctk.CTkLabel(
            modal,
            text="FACTURA MANUAL DE COMPRA",
            font=FUERTE_SUBTITULO,
            text_color=COLOR_ACENTO
        ).pack(pady=(18, 5))

        ctk.CTkLabel(
            modal,
            text="Agregue productos existentes, cantidades y precio de compra. Se guardará la factura y se sumará stock.",
            font=FUERTE_TEXTO,
            text_color=COLOR_TEXTO_SECUNDARIO
        ).pack(pady=(0, 8))

        info_frame = ctk.CTkFrame(modal, fg_color=COLOR_FONDO_CONTENIDO, corner_radius=10)
        info_frame.pack(fill="x", padx=20, pady=(0, 8))
        info_frame.grid_columnconfigure(1, weight=1)
        info_frame.grid_columnconfigure(3, weight=1)

        ctk.CTkLabel(
            info_frame,
            text="Proveedor:",
            font=("Inter", 11, "bold")
        ).grid(row=0, column=0, padx=(12, 5), pady=8, sticky="w")

        ent_proveedor = ctk.CTkEntry(
            info_frame,
            height=32,
            fg_color=COLOR_TARJETAS,
            border_color=COLOR_BORDE
        )
        ent_proveedor.insert(0, "Proveedor no especificado")
        ent_proveedor.grid(row=0, column=1, padx=5, pady=8, sticky="ew")

        ctk.CTkLabel(
            info_frame,
            text="Tipo:",
            font=("Inter", 11, "bold")
        ).grid(row=0, column=2, padx=(12, 5), pady=8, sticky="w")

        ctk.CTkLabel(
            info_frame,
            text="Ingreso manual",
            font=("Inter", 11),
            text_color=COLOR_TEXTO_SECUNDARIO
        ).grid(row=0, column=3, padx=5, pady=8, sticky="w")

        resumen_frame = ctk.CTkFrame(modal, fg_color=COLOR_FONDO_CONTENIDO, corner_radius=10)
        resumen_frame.pack(fill="x", padx=20, pady=(0, 10))

        lbl_resumen = ctk.CTkLabel(
            resumen_frame,
            text="Productos: 0  |  Encontrados: 0  |  Pendientes: 0",
            font=("Inter", 12, "bold"),
            text_color=COLOR_TEXTO_SECUNDARIO
        )
        lbl_resumen.pack(side="left", padx=12, pady=8)

        lbl_total = ctk.CTkLabel(
            resumen_frame,
            text="Total inversión: $ 0",
            font=("Inter", 12, "bold"),
            text_color=COLOR_ACENTO
        )
        lbl_total.pack(side="right", padx=12, pady=8)

        contenedor = ctk.CTkScrollableFrame(modal, fg_color=COLOR_FONDO_CONTENIDO, corner_radius=12)
        contenedor.pack(fill="both", expand=True, padx=20, pady=8)

        filas = []

        header = ctk.CTkFrame(contenedor, fg_color=COLOR_TARJETAS, height=35)
        header.pack(fill="x", pady=(0, 5))
        for i, peso in enumerate([3, 1, 1, 1, 1, 1, 1, 0]):
            if i == 7:
                header.grid_columnconfigure(i, weight=0, minsize=55)
            else:
                header.grid_columnconfigure(i, weight=peso)

        encabezados = [
            "Producto existente / SKU",
            "Cant.",
            "P. Compra",
            "Subtotal",
            "Stock",
            "Nuevo",
            "Estado",
            "Quitar"
        ]

        for col, texto in enumerate(encabezados):
            ctk.CTkLabel(
                header,
                text=texto,
                font=("Inter", 10, "bold"),
                text_color=COLOR_TEXTO_SECUNDARIO
            ).grid(row=0, column=col, padx=6, pady=8, sticky="w")

        def formato_valor(valor):
            try:
                return f"$ {float(valor or 0):,.0f}"
            except Exception:
                return "$ 0"

        def recalcular_totales():
            total = 0.0
            encontrados = 0
            pendientes = 0

            for fila_data in filas:
                try:
                    cant = int(float(fila_data["cantidad_entry"].get().replace(",", ".")))
                except Exception:
                    cant = 0

                try:
                    precio = float(fila_data["precio_entry"].get().replace(",", "."))
                except Exception:
                    precio = 0.0

                subtotal = max(cant, 0) * max(precio, 0)
                total += subtotal
                fila_data["subtotal_label"].configure(text=formato_valor(subtotal))

                producto_db = fila_data.get("producto_db")
                if producto_db:
                    encontrados += 1
                    stock_actual = int(fila_data.get("stock_actual", 0) or 0)
                    fila_data["nuevo_stock_label"].configure(
                        text=str(stock_actual + max(cant, 0)),
                        text_color="#50C878"
                    )
                else:
                    pendientes += 1
                    fila_data["nuevo_stock_label"].configure(
                        text="-",
                        text_color=COLOR_TEXTO_SECUNDARIO
                    )

            lbl_resumen.configure(
                text=f"Productos: {len(filas)}  |  Encontrados: {encontrados}  |  Pendientes: {pendientes}",
                text_color=COLOR_ACENTO if encontrados else COLOR_TEXTO_SECUNDARIO
            )
            lbl_total.configure(text=f"Total inversión: {formato_valor(total)}")

        def quitar_fila(fila_data):
            if fila_data in filas:
                filas.remove(fila_data)
            try:
                fila_data["frame"].destroy()
            except Exception:
                pass
            recalcular_totales()

        def validar_fila(fila_data):
            texto_producto = fila_data["nombre_entry"].get().strip()
            producto_db = self.buscar_producto_factura("", texto_producto)
            fila_data["producto_db"] = producto_db

            stock_actual = self.obtener_stock_producto_db(producto_db)
            fila_data["stock_actual"] = stock_actual

            try:
                cantidad = int(float(fila_data["cantidad_entry"].get().replace(",", ".")))
            except Exception:
                cantidad = 0

            if producto_db:
                fila_data["estado_label"].configure(
                    text=f"Encontrado: {producto_db[1]}",
                    text_color=COLOR_ACENTO
                )
                fila_data["stock_actual_label"].configure(
                    text=str(stock_actual),
                    text_color=COLOR_TEXTO_SECUNDARIO
                )
                fila_data["nuevo_stock_label"].configure(
                    text=str(stock_actual + max(cantidad, 0)),
                    text_color="#50C878"
                )

                try:
                    precio_actual = float(fila_data["precio_entry"].get().replace(",", "."))
                except Exception:
                    precio_actual = 0

                if precio_actual <= 0:
                    try:
                        fila_data["precio_entry"].delete(0, "end")
                        fila_data["precio_entry"].insert(0, str(int(float(producto_db[2] or 0))))
                    except Exception:
                        pass
            else:
                fila_data["estado_label"].configure(
                    text="No encontrado",
                    text_color=COLOR_PELIGRO
                )
                fila_data["stock_actual_label"].configure(
                    text="-",
                    text_color=COLOR_TEXTO_SECUNDARIO
                )
                fila_data["nuevo_stock_label"].configure(
                    text="-",
                    text_color=COLOR_TEXTO_SECUNDARIO
                )

            recalcular_totales()

        def agregar_fila(producto_texto="", cantidad="1", precio_compra="0"):
            fila = ctk.CTkFrame(contenedor, fg_color="transparent")
            fila.pack(fill="x", pady=3)

            for i, peso in enumerate([3, 1, 1, 1, 1, 1, 1, 0]):
                if i == 7:
                    fila.grid_columnconfigure(i, weight=0, minsize=55)
                else:
                    fila.grid_columnconfigure(i, weight=peso)

            ent_nombre = ctk.CTkEntry(
                fila,
                height=35,
                fg_color=COLOR_TARJETAS,
                border_color=COLOR_BORDE,
                placeholder_text="SKU o nombre del producto existente"
            )
            ent_nombre.insert(0, producto_texto)
            ent_nombre.grid(row=0, column=0, padx=6, pady=4, sticky="ew")

            ent_cantidad = ctk.CTkEntry(
                fila,
                height=35,
                width=70,
                fg_color=COLOR_TARJETAS,
                border_color=COLOR_BORDE
            )
            ent_cantidad.insert(0, str(cantidad))
            ent_cantidad.grid(row=0, column=1, padx=5, pady=4)

            ent_precio = ctk.CTkEntry(
                fila,
                height=35,
                width=90,
                fg_color=COLOR_TARJETAS,
                border_color=COLOR_BORDE
            )
            ent_precio.insert(0, str(precio_compra))
            ent_precio.grid(row=0, column=2, padx=5, pady=4)

            lbl_subtotal = ctk.CTkLabel(
                fila,
                text="$ 0",
                font=("Inter", 10, "bold"),
                text_color=COLOR_ACENTO
            )
            lbl_subtotal.grid(row=0, column=3, padx=5, pady=4)

            lbl_stock = ctk.CTkLabel(
                fila,
                text="-",
                font=("Inter", 10, "bold"),
                text_color=COLOR_TEXTO_SECUNDARIO
            )
            lbl_stock.grid(row=0, column=4, padx=5, pady=4)

            lbl_nuevo = ctk.CTkLabel(
                fila,
                text="-",
                font=("Inter", 10, "bold"),
                text_color=COLOR_TEXTO_SECUNDARIO
            )
            lbl_nuevo.grid(row=0, column=5, padx=5, pady=4)

            lbl_estado = ctk.CTkLabel(
                fila,
                text="Sin validar",
                text_color=COLOR_TEXTO_SECUNDARIO,
                font=("Inter", 9, "bold")
            )
            lbl_estado.grid(row=0, column=6, padx=5, pady=4, sticky="w")

            btn_quitar = ctk.CTkButton(
                fila,
                text="🗑",
                width=38,
                height=30,
                fg_color="#E74C3C",
                hover_color="#C0392B"
            )
            btn_quitar.grid(row=0, column=7, padx=5, pady=4)

            fila_data = {
                "nombre_entry": ent_nombre,
                "cantidad_entry": ent_cantidad,
                "precio_entry": ent_precio,
                "producto_db": None,
                "stock_actual": 0,
                "estado_label": lbl_estado,
                "stock_actual_label": lbl_stock,
                "nuevo_stock_label": lbl_nuevo,
                "subtotal_label": lbl_subtotal,
                "frame": fila
            }

            filas.append(fila_data)

            btn_quitar.configure(command=lambda fd=fila_data: quitar_fila(fd))
            ent_nombre.bind("<KeyRelease>", lambda e, fd=fila_data: validar_fila(fd))
            ent_nombre.bind("<FocusOut>", lambda e, fd=fila_data: validar_fila(fd))
            ent_cantidad.bind("<KeyRelease>", lambda e: recalcular_totales())
            ent_precio.bind("<KeyRelease>", lambda e: recalcular_totales())

            validar_fila(fila_data)

        acciones = ctk.CTkFrame(modal, fg_color="transparent")
        acciones.pack(fill="x", padx=20, pady=(5, 20))

        ctk.CTkButton(
            acciones,
            text="Cancelar",
            fg_color=COLOR_TARJETAS,
            border_width=1,
            border_color=COLOR_BORDE,
            command=modal.destroy
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            acciones,
            text="+ Agregar producto",
            fg_color=COLOR_PRIMARIO,
            hover_color="#2563eb",
            command=lambda: agregar_fila()
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            acciones,
            text="Validar todo",
            fg_color=COLOR_PRIMARIO,
            hover_color="#2563eb",
            command=lambda: self.revalidar_filas_factura(filas)
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            acciones,
            text="Guardar Factura Manual",
            fg_color=COLOR_ACENTO,
            text_color="#000",
            font=FUERTE_TEXTO_BOLD,
            command=lambda: self.aplicar_factura_al_inventario(
                filas,
                modal,
                "Factura manual",
                ent_proveedor.get()
            )
        ).pack(side="right", padx=5)

        agregar_fila()
        recalcular_totales()

    def disenar_pestana_facturas_compra(self):
        """Crea el apartado de facturas de compra digitalizadas."""
        toolbar = ctk.CTkFrame(self.tab_facturas, fg_color="transparent")
        toolbar.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(toolbar, text="Filtrar por:", font=FUERTE_TEXTO).pack(side="left", padx=(5, 10))

        self.combo_facturas_periodo = ctk.CTkComboBox(
            toolbar,
            values=["Todas", "Mes", "Año"],
            width=100,
            command=lambda e: self.gestionar_filtros_facturas_compra()
        )
        self.combo_facturas_periodo.set("Todas")
        self.combo_facturas_periodo.pack(side="left", padx=5)

        self.combo_facturas_mes = ctk.CTkComboBox(
            toolbar,
            values=self.meses_nombres,
            width=130,
            command=lambda e: self.actualizar_facturas_compra()
        )

        self.combo_facturas_anio = ctk.CTkComboBox(
            toolbar,
            values=[str(a) for a in range(2024, 2031)],
            width=100,
            command=lambda e: self.actualizar_facturas_compra()
        )

        ctk.CTkButton(
            toolbar,
            text="Actualizar",
            fg_color=COLOR_PRIMARIO,
            hover_color="#2563eb",
            width=100,
            command=self.actualizar_facturas_compra
        ).pack(side="left", padx=8)

        ctk.CTkButton(
            toolbar,
            text="📄 Cargar Nueva Factura",
            fg_color=COLOR_ACENTO,
            text_color="#000",
            font=FUERTE_TEXTO_BOLD,
            width=170,
            command=self.cargar_factura_inventario
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            toolbar,
            text="✍️ Factura Manual",
            fg_color=COLOR_PRIMARIO,
            hover_color="#2563eb",
            font=FUERTE_TEXTO_BOLD,
            width=150,
            command=self.abrir_factura_manual
        ).pack(side="right", padx=5)

        self.resumen_facturas_frame = ctk.CTkFrame(
            self.tab_facturas,
            fg_color=COLOR_TARJETAS,
            corner_radius=12,
            border_width=1,
            border_color=COLOR_BORDE
        )
        self.resumen_facturas_frame.pack(fill="x", padx=10, pady=(0, 10))

        self.lbl_total_facturas_compra = ctk.CTkLabel(
            self.resumen_facturas_frame,
            text="💰 Inversión en facturas: $ 0",
            font=("Inter", 15, "bold"),
            text_color=COLOR_ACENTO
        )
        self.lbl_total_facturas_compra.pack(side="left", padx=18, pady=12)

        self.lbl_cantidad_facturas_compra = ctk.CTkLabel(
            self.resumen_facturas_frame,
            text="🧾 Facturas: 0",
            font=("Inter", 13, "bold"),
            text_color=COLOR_TEXTO_SECUNDARIO
        )
        self.lbl_cantidad_facturas_compra.pack(side="left", padx=18, pady=12)

        titulos = ctk.CTkFrame(self.tab_facturas, fg_color=COLOR_TARJETAS, height=35, corner_radius=5)
        titulos.pack(fill="x", padx=10, pady=(0, 0))

        for texto, pos in [
            ("ID", 0.02),
            ("Fecha", 0.10),
            ("Proveedor", 0.28),
            ("Archivo", 0.48),
            ("Inversión", 0.72),
            ("Acciones", 0.88)
        ]:
            ctk.CTkLabel(titulos, text=texto, font=("Inter", 11, "bold"), text_color=COLOR_TEXTO_SECUNDARIO).place(relx=pos, rely=0.5, anchor="w")

        self.scroll_facturas_compra = ctk.CTkScrollableFrame(self.tab_facturas, fg_color="transparent")
        self.scroll_facturas_compra.pack(fill="both", expand=True, padx=5, pady=5)

        self.gestionar_filtros_facturas_compra()

    def gestionar_filtros_facturas_compra(self):
        """Muestra/oculta filtros de mes/año para facturas."""
        if hasattr(self, "combo_facturas_mes"):
            self.combo_facturas_mes.pack_forget()
        if hasattr(self, "combo_facturas_anio"):
            self.combo_facturas_anio.pack_forget()

        periodo = self.combo_facturas_periodo.get() if hasattr(self, "combo_facturas_periodo") else "Todas"

        if periodo == "Mes":
            mes_actual = self.meses_nombres[datetime.datetime.now().month - 1]
            self.combo_facturas_mes.set(mes_actual)
            self.combo_facturas_mes.pack(side="left", padx=5)
        elif periodo == "Año":
            self.combo_facturas_anio.set(str(datetime.datetime.now().year))
            self.combo_facturas_anio.pack(side="left", padx=5)

        self.actualizar_facturas_compra()

    def obtener_filtro_facturas_compra(self):
        periodo = self.combo_facturas_periodo.get() if hasattr(self, "combo_facturas_periodo") else "Todas"
        if periodo == "Mes":
            return periodo, self.combo_facturas_mes.get()
        if periodo == "Año":
            return periodo, self.combo_facturas_anio.get()
        return "Todas", None

    def actualizar_facturas_compra(self):
        """Actualiza listado y total invertido en facturas de compra."""
        if not hasattr(self, "scroll_facturas_compra"):
            return

        for widget in self.scroll_facturas_compra.winfo_children():
            widget.destroy()

        if not hasattr(self.db, "obtener_facturas_compra"):
            ctk.CTkLabel(
                self.scroll_facturas_compra,
                text="Actualiza database.py para habilitar el historial de facturas de compra.",
                font=FUERTE_TEXTO,
                text_color=COLOR_PELIGRO
            ).pack(pady=40)
            return

        periodo, valor = self.obtener_filtro_facturas_compra()
        facturas = self.db.obtener_facturas_compra(periodo, valor)

        try:
            total = self.db.obtener_total_invertido_facturas(periodo, valor)
        except Exception:
            total = sum(float(f[4] or 0) for f in facturas)

        if hasattr(self, "lbl_total_facturas_compra"):
            self.lbl_total_facturas_compra.configure(text=f"💰 Inversión en facturas: $ {total:,.0f}")

        if hasattr(self, "lbl_cantidad_facturas_compra"):
            self.lbl_cantidad_facturas_compra.configure(text=f"🧾 Facturas: {len(facturas)}")

        if not facturas:
            ctk.CTkLabel(
                self.scroll_facturas_compra,
                text="No hay facturas guardadas para este filtro.",
                font=FUERTE_TEXTO,
                text_color=COLOR_TEXTO_SECUNDARIO
            ).pack(pady=40)
            return

        for factura in facturas:
            factura_id, fecha, archivo, proveedor, total_inversion, observacion = factura

            f = ctk.CTkFrame(self.scroll_facturas_compra, fg_color=COLOR_FONDO_CONTENIDO, height=50, cursor="hand2")
            f.pack(fill="x", pady=2, padx=5)

            ctk.CTkLabel(f, text=str(factura_id), font=("Inter", 11, "bold"), text_color=COLOR_ACENTO).place(relx=0.02, rely=0.5, anchor="w")
            ctk.CTkLabel(f, text=str(fecha), font=("Inter", 11)).place(relx=0.10, rely=0.5, anchor="w")
            ctk.CTkLabel(f, text=str(proveedor or "Sin proveedor")[:22], font=("Inter", 11)).place(relx=0.28, rely=0.5, anchor="w")
            ctk.CTkLabel(f, text=str(archivo or "Sin archivo")[:28], font=("Inter", 10), text_color=COLOR_TEXTO_SECUNDARIO).place(relx=0.48, rely=0.5, anchor="w")
            ctk.CTkLabel(f, text=f"$ {float(total_inversion or 0):,.0f}", font=("Inter", 12, "bold"), text_color=COLOR_ACENTO).place(relx=0.72, rely=0.5, anchor="w")

            ctk.CTkButton(
                f,
                text="Ver",
                width=50,
                height=28,
                fg_color=COLOR_PRIMARIO,
                hover_color="#2563eb",
                command=lambda fid=factura_id: self.ver_detalle_factura_compra(fid)
            ).place(relx=0.88, rely=0.5, anchor="w")

            ctk.CTkButton(
                f,
                text="🗑",
                width=42,
                height=28,
                fg_color="#E74C3C",
                hover_color="#C0392B",
                command=lambda fid=factura_id: self.eliminar_factura_compra_dashboard(fid)
            ).place(relx=0.94, rely=0.5, anchor="w")

    def ver_detalle_factura_compra(self, factura_id):
        """Muestra detalle de una factura de compra guardada."""
        if not hasattr(self.db, "obtener_detalle_factura_compra"):
            messagebox.showerror("No disponible", "Actualiza database.py para ver detalles de facturas.")
            return

        detalle = self.db.obtener_detalle_factura_compra(factura_id)

        modal = ctk.CTkToplevel(self)
        modal.title(f"Detalle Factura #{factura_id}")
        modal.geometry("760x520")
        modal.configure(fg_color=COLOR_TARJETAS)
        modal.grab_set()
        modal.lift()

        ctk.CTkLabel(
            modal,
            text=f"DETALLE FACTURA #{factura_id}",
            font=FUERTE_SUBTITULO,
            text_color=COLOR_ACENTO
        ).pack(pady=(20, 8))

        scroll = ctk.CTkScrollableFrame(modal, fg_color=COLOR_FONDO_CONTENIDO, corner_radius=12)
        scroll.pack(fill="both", expand=True, padx=20, pady=10)

        header = ctk.CTkFrame(scroll, fg_color=COLOR_TARJETAS)
        header.pack(fill="x", pady=(0, 5))
        header.grid_columnconfigure(0, weight=2)
        header.grid_columnconfigure(1, weight=1)
        header.grid_columnconfigure(2, weight=1)
        header.grid_columnconfigure(3, weight=1)
        header.grid_columnconfigure(4, weight=1)

        for col, texto in enumerate(["Producto", "Cant.", "P. Compra", "Subtotal", "Estado"]):
            ctk.CTkLabel(header, text=texto, font=("Inter", 11, "bold")).grid(row=0, column=col, padx=8, pady=8, sticky="w")

        total = 0.0
        for item in detalle:
            codigo, nombre, cantidad, precio_compra, subtotal, encontrado = item
            total += float(subtotal or 0)

            fila = ctk.CTkFrame(scroll, fg_color="transparent")
            fila.pack(fill="x", pady=2)
            fila.grid_columnconfigure(0, weight=2)
            fila.grid_columnconfigure(1, weight=1)
            fila.grid_columnconfigure(2, weight=1)
            fila.grid_columnconfigure(3, weight=1)
            fila.grid_columnconfigure(4, weight=1)

            ctk.CTkLabel(fila, text=str(nombre)[:35], font=("Inter", 11)).grid(row=0, column=0, padx=8, pady=5, sticky="w")
            ctk.CTkLabel(fila, text=str(cantidad), font=("Inter", 11)).grid(row=0, column=1, padx=8, pady=5, sticky="w")
            ctk.CTkLabel(fila, text=f"$ {float(precio_compra or 0):,.0f}", font=("Inter", 11)).grid(row=0, column=2, padx=8, pady=5, sticky="w")
            ctk.CTkLabel(fila, text=f"$ {float(subtotal or 0):,.0f}", font=("Inter", 11, "bold"), text_color=COLOR_ACENTO).grid(row=0, column=3, padx=8, pady=5, sticky="w")
            ctk.CTkLabel(
                fila,
                text="Aplicado" if encontrado else "Pendiente",
                font=("Inter", 11, "bold"),
                text_color=COLOR_ACENTO if encontrado else COLOR_PELIGRO
            ).grid(row=0, column=4, padx=8, pady=5, sticky="w")

        ctk.CTkLabel(
            modal,
            text=f"TOTAL INVERSIÓN: $ {total:,.0f}",
            font=("Inter", 14, "bold"),
            text_color=COLOR_ACENTO
        ).pack(pady=(0, 15))

    def eliminar_factura_compra_dashboard(self, factura_id):
        """Elimina del historial una factura de compra. No revierte stock."""
        if not hasattr(self.db, "eliminar_factura_compra"):
            messagebox.showerror("No disponible", "Actualiza database.py para eliminar facturas guardadas.")
            return

        if not messagebox.askyesno(
            "Eliminar factura",
            f"¿Eliminar la factura #{factura_id} del historial?\n\n"
            "Esto NO revierte el stock que ya fue sumado."
        ):
            return

        if self.db.eliminar_factura_compra(factura_id):
            messagebox.showinfo("Factura eliminada", "La factura fue eliminada del historial.")
            self.actualizar_facturas_compra()
        else:
            messagebox.showerror("Error", "No se pudo eliminar la factura.")

    def abrir_modal_nuevo(self):
        NuevoProductoModal(self, self.db, self.actualizar_tabla_inventario)

    def disenar_pestana_usuarios(self):
        toolbar = ctk.CTkFrame(self.tab_usuarios, fg_color="transparent")
        toolbar.pack(fill="x", padx=12, pady=(12, 8))

        ctk.CTkButton(
            toolbar,
            text="+ Nuevo usuario",
            fg_color=COLOR_ACENTO,
            text_color="#000",
            font=FUERTE_TEXTO_BOLD,
            command=self.crear_usuario_desde_dashboard
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            toolbar,
            text="🔐 Cambiar contraseña",
            fg_color=COLOR_PRIMARIO,
            hover_color="#2563eb",
            command=self.cambiar_password_desde_dashboard
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            toolbar,
            text="🗑 Eliminar usuario",
            fg_color="#E74C3C",
            hover_color="#C0392B",
            command=self.eliminar_usuario_desde_dashboard
        ).pack(side="left", padx=5)

        ctk.CTkButton(
            toolbar,
            text="🔒 Clave Dashboard",
            fg_color=COLOR_TARJETAS,
            border_width=1,
            border_color=COLOR_BORDE,
            command=self.cambiar_clave_dashboard
        ).pack(side="right", padx=5)

        info = ctk.CTkFrame(
            self.tab_usuarios,
            fg_color=COLOR_TARJETAS,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDE
        )
        info.pack(fill="x", padx=12, pady=(0, 10))

        ctk.CTkLabel(
            info,
            text="Gestiona usuarios y contraseñas sin tocar código.",
            font=FUERTE_TEXTO,
            text_color=COLOR_TEXTO_SECUNDARIO
        ).pack(side="left", padx=12, pady=10)

        self.lbl_clave_dashboard_actual = ctk.CTkLabel(
            info,
            text=f"Clave Dashboard actual: {self.db.obtener_clave_dashboard()}",
            font=("Inter", 12, "bold"),
            text_color=COLOR_ACENTO
        )
        self.lbl_clave_dashboard_actual.pack(side="right", padx=12, pady=10)

        header = ctk.CTkFrame(self.tab_usuarios, fg_color=COLOR_TARJETAS, height=34, corner_radius=6)
        header.pack(fill="x", padx=12, pady=(0, 0))
        for texto, pos in [("ID", 0.03), ("Usuario", 0.16), ("Rol", 0.70)]:
            ctk.CTkLabel(
                header,
                text=texto,
                font=("Inter", 11, "bold"),
                text_color=COLOR_TEXTO_SECUNDARIO
            ).place(relx=pos, rely=0.5, anchor="w")

        self.scroll_usuarios = ctk.CTkScrollableFrame(self.tab_usuarios, fg_color="transparent")
        self.scroll_usuarios.pack(fill="both", expand=True, padx=8, pady=8)

        self.usuario_seleccionado_id = None
        self.frames_usuarios = {}
        self.actualizar_tabla_usuarios()

    def actualizar_tabla_usuarios(self):
        if not hasattr(self, "scroll_usuarios"):
            return

        for widget in self.scroll_usuarios.winfo_children():
            widget.destroy()
        self.frames_usuarios = {}

        usuarios = self.db.listar_usuarios() if hasattr(self.db, "listar_usuarios") else []
        if not usuarios:
            ctk.CTkLabel(
                self.scroll_usuarios,
                text="No hay usuarios registrados.",
                font=FUERTE_TEXTO,
                text_color=COLOR_TEXTO_SECUNDARIO
            ).pack(pady=40)
            return

        for user_id, username, rol in usuarios:
            fila = ctk.CTkFrame(self.scroll_usuarios, fg_color=COLOR_FONDO_CONTENIDO, height=44, cursor="hand2")
            fila.pack(fill="x", padx=6, pady=2)

            ctk.CTkLabel(fila, text=str(user_id), font=("Inter", 11, "bold"), text_color=COLOR_ACENTO).place(relx=0.03, rely=0.5, anchor="w")
            ctk.CTkLabel(fila, text=str(username), font=("Inter", 12)).place(relx=0.16, rely=0.5, anchor="w")
            ctk.CTkLabel(
                fila,
                text=str(rol).upper(),
                font=("Inter", 11, "bold"),
                text_color=COLOR_PRIMARIO if str(rol).lower() == "admin" else COLOR_TEXTO_SECUNDARIO
            ).place(relx=0.70, rely=0.5, anchor="w")

            fila.bind("<Button-1>", lambda e, uid=user_id: self.seleccionar_usuario(uid))
            self.frames_usuarios[user_id] = fila

        self.refrescar_estilo_usuarios()

    def seleccionar_usuario(self, user_id):
        self.usuario_seleccionado_id = user_id
        self.refrescar_estilo_usuarios()

    def refrescar_estilo_usuarios(self):
        if not hasattr(self, "frames_usuarios"):
            return
        for uid, frame in self.frames_usuarios.items():
            frame.configure(fg_color=COLOR_SELECCION if uid == self.usuario_seleccionado_id else COLOR_FONDO_CONTENIDO)

    def crear_usuario_desde_dashboard(self):
        username = ctk.CTkInputDialog(text="Nombre del nuevo usuario:", title="Crear usuario").get_input()
        if username is None:
            return
        username = username.strip()
        if not username:
            messagebox.showwarning("Datos incompletos", "Debes escribir un usuario.")
            return

        password = ctk.CTkInputDialog(text="Contraseña del usuario:", title="Crear usuario").get_input()
        if password is None:
            return
        password = password.strip()
        if not password:
            messagebox.showwarning("Datos incompletos", "Debes escribir una contraseña.")
            return

        rol = ctk.CTkInputDialog(
            text="Rol del usuario (admin o cajero):",
            title="Crear usuario"
        ).get_input()
        if rol is None:
            return
        rol = rol.strip().lower() or "cajero"

        ok, msg = self.db.crear_usuario(username, password, rol)
        if ok:
            messagebox.showinfo("Éxito", msg)
            self.actualizar_tabla_usuarios()
        else:
            messagebox.showerror("No se pudo crear", msg)

    def cambiar_password_desde_dashboard(self):
        if not self.usuario_seleccionado_id:
            messagebox.showwarning("Selecciona un usuario", "Primero selecciona un usuario.")
            return

        nueva = ctk.CTkInputDialog(
            text="Nueva contraseña:",
            title="Cambiar contraseña"
        ).get_input()
        if nueva is None:
            return
        nueva = nueva.strip()

        ok, msg = self.db.cambiar_password_usuario(self.usuario_seleccionado_id, nueva)
        if ok:
            messagebox.showinfo("Contraseña actualizada", msg)
        else:
            messagebox.showerror("Error", msg)

    def eliminar_usuario_desde_dashboard(self):
        if not self.usuario_seleccionado_id:
            messagebox.showwarning("Selecciona un usuario", "Primero selecciona un usuario.")
            return

        if not messagebox.askyesno(
            "Eliminar usuario",
            "¿Seguro que deseas eliminar el usuario seleccionado?"
        ):
            return

        ok, msg = self.db.eliminar_usuario(self.usuario_seleccionado_id)
        if ok:
            self.usuario_seleccionado_id = None
            messagebox.showinfo("Usuario eliminado", msg)
            self.actualizar_tabla_usuarios()
        else:
            messagebox.showerror("No se pudo eliminar", msg)

    def cambiar_clave_dashboard(self):
        nueva = ctk.CTkInputDialog(
            text="Nueva clave para abrir el Dashboard:",
            title="Clave Dashboard"
        ).get_input()
        if nueva is None:
            return
        nueva = nueva.strip()

        ok, msg = self.db.actualizar_clave_dashboard(nueva)
        if ok:
            if hasattr(self, "lbl_clave_dashboard_actual"):
                self.lbl_clave_dashboard_actual.configure(
                    text=f"Clave Dashboard actual: {self.db.obtener_clave_dashboard()}"
                )
            messagebox.showinfo("Clave actualizada", msg)
        else:
            messagebox.showerror("Error", msg)

    def disenar_pestana_configuracion(self):
        """Formulario para personalizar nombre del sistema y datos del ticket."""
        contenedor = ctk.CTkScrollableFrame(self.tab_config, fg_color="transparent")
        contenedor.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            contenedor,
            text="Personalización del negocio",
            font=FUERTE_SUBTITULO,
            text_color=COLOR_ACENTO
        ).pack(anchor="w", pady=(0, 5))

        ctk.CTkLabel(
            contenedor,
            text="Estos datos se usan en login, menú, tickets de venta y cierres de caja.",
            font=FUERTE_TEXTO,
            text_color=COLOR_TEXTO_SECUNDARIO
        ).pack(anchor="w", pady=(0, 20))

        form = ctk.CTkFrame(contenedor, fg_color=COLOR_TARJETAS, corner_radius=12, border_width=1, border_color=COLOR_BORDE)
        form.pack(fill="x", pady=(0, 15))

        campos = [
            ("nombre_sistema", "Nombre del sistema (ventana, login, menú)"),
            ("nombre_establecimiento", "Nombre del establecimiento (ticket / factura)"),
            ("subtitulo_sistema", "Subtítulo en pantalla de login"),
            ("nit", "NIT o documento"),
            ("ciudad", "Ciudad / ubicación"),
            ("telefono", "Teléfono"),
        ]

        self.entries_config = {}
        for clave, etiqueta in campos:
            ctk.CTkLabel(
                form,
                text=etiqueta,
                font=FUERTE_TEXTO_BOLD,
                text_color=COLOR_TEXTO_SECUNDARIO
            ).pack(anchor="w", padx=20, pady=(15, 2))

            entry = ctk.CTkEntry(
                form,
                height=40,
                fg_color=COLOR_FONDO_CONTENIDO,
                border_color=COLOR_BORDE
            )
            entry.pack(fill="x", padx=20, pady=(0, 5))
            self.entries_config[clave] = entry

        ctk.CTkLabel(
            form,
            text="Logo del negocio",
            font=FUERTE_SUBTITULO,
            text_color=COLOR_ACENTO
        ).pack(anchor="w", padx=20, pady=(25, 5))

        logo_frame = ctk.CTkFrame(
            form,
            fg_color=COLOR_FONDO_CONTENIDO,
            corner_radius=10,
            border_width=1,
            border_color=COLOR_BORDE
        )
        logo_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.logo_preview_image = None
        self.logo_preview = ctk.CTkLabel(
            logo_frame,
            text="Sin logo",
            width=120,
            height=95,
            fg_color=COLOR_TARJETAS,
            corner_radius=8,
            text_color=COLOR_TEXTO_SECUNDARIO
        )
        self.logo_preview.pack(side="left", padx=12, pady=12)

        logo_actions = ctk.CTkFrame(logo_frame, fg_color="transparent")
        logo_actions.pack(side="left", fill="both", expand=True, padx=8, pady=12)

        self.lbl_logo_ruta = ctk.CTkLabel(
            logo_actions,
            text="PNG, JPG, JPEG o WEBP. Se copia al sistema local.",
            font=FUERTE_TEXTO,
            text_color=COLOR_TEXTO_SECUNDARIO,
            anchor="w"
        )
        self.lbl_logo_ruta.pack(fill="x", pady=(0, 10))

        ctk.CTkButton(
            logo_actions,
            text="Cargar logo",
            fg_color=COLOR_PRIMARIO,
            hover_color=COLOR_ACENTO,
            command=self.seleccionar_logo_negocio
        ).pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            logo_actions,
            text="Quitar logo",
            fg_color=COLOR_TARJETAS,
            border_width=1,
            border_color=COLOR_BORDE,
            command=self.quitar_logo_negocio
        ).pack(side="left")

        ctk.CTkLabel(
            form,
            text="Apariencia",
            font=FUERTE_SUBTITULO,
            text_color=COLOR_ACENTO
        ).pack(anchor="w", padx=20, pady=(25, 5))

        ctk.CTkLabel(
            form,
            text="Modo visual",
            font=FUERTE_TEXTO_BOLD,
            text_color=COLOR_TEXTO_SECUNDARIO
        ).pack(anchor="w", padx=20, pady=(10, 2))

        self.combo_tema_modo = ctk.CTkComboBox(
            form,
            values=["Oscuro", "Claro"],
            height=40,
            fg_color=COLOR_FONDO_CONTENIDO,
            border_color=COLOR_BORDE,
            button_color=COLOR_PRIMARIO,
            button_hover_color=COLOR_ACENTO
        )
        self.combo_tema_modo.pack(fill="x", padx=20, pady=(0, 5))

        self.entries_apariencia = {}
        for clave, etiqueta in [
            ("color_acento", "Color de acento"),
            ("color_primario", "Color primario"),
        ]:
            ctk.CTkLabel(
                form,
                text=etiqueta,
                font=FUERTE_TEXTO_BOLD,
                text_color=COLOR_TEXTO_SECUNDARIO
            ).pack(anchor="w", padx=20, pady=(10, 2))

            entry = ctk.CTkEntry(
                form,
                height=40,
                fg_color=COLOR_FONDO_CONTENIDO,
                border_color=COLOR_BORDE
            )
            entry.pack(fill="x", padx=20, pady=(0, 5))
            self.entries_apariencia[clave] = entry
            self.crear_paleta_colores(form, clave)

        presets = ctk.CTkFrame(form, fg_color="transparent")
        presets.pack(fill="x", padx=20, pady=(8, 5))

        for nombre, acento, primario in [
            ("Verde", "#10b981", "#3b82f6"),
            ("Dorado", "#f59e0b", "#2563eb"),
            ("Rojo", "#ef4444", "#0ea5e9"),
            ("Morado", "#8b5cf6", "#06b6d4"),
        ]:
            ctk.CTkButton(
                presets,
                text=nombre,
                width=90,
                height=32,
                fg_color=acento,
                hover_color=primario,
                command=lambda a=acento, p=primario: self.aplicar_preset_colores(a, p)
            ).pack(side="left", padx=(0, 8), pady=4)

        ctk.CTkButton(
            form,
            text="GUARDAR CONFIGURACIÓN",
            fg_color=COLOR_ACENTO,
            text_color="#000",
            font=FUERTE_TEXTO_BOLD,
            height=45,
            command=self.guardar_configuracion_negocio
        ).pack(fill="x", padx=20, pady=25)

        self.cargar_formulario_configuracion()

    def crear_paleta_colores(self, parent, clave):
        paleta = ctk.CTkFrame(parent, fg_color="transparent")
        paleta.pack(fill="x", padx=20, pady=(0, 8))

        colores = [
            "#10b981", "#059669", "#14b8a6", "#06b6d4",
            "#3b82f6", "#2563eb", "#6366f1", "#8b5cf6",
            "#a855f7", "#ec4899", "#ef4444", "#f97316",
            "#f59e0b", "#eab308", "#84cc16", "#22c55e",
            "#64748b", "#0f172a", "#111827", "#ffffff",
        ]

        for color in colores:
            borde = COLOR_BORDE if color != "#ffffff" else "#94a3b8"
            ctk.CTkButton(
                paleta,
                text="",
                width=30,
                height=24,
                fg_color=color,
                hover_color=color,
                border_width=1,
                border_color=borde,
                command=lambda c=color, k=clave: self.seleccionar_color_apariencia(k, c)
            ).pack(side="left", padx=(0, 5), pady=3)

    def seleccionar_color_apariencia(self, clave, color):
        if not hasattr(self, "entries_apariencia") or clave not in self.entries_apariencia:
            return
        entry = self.entries_apariencia[clave]
        entry.delete(0, "end")
        entry.insert(0, color)

    def seleccionar_logo_negocio(self):
        ruta = filedialog.askopenfilename(
            title="Seleccionar logo",
            filetypes=[
                ("Imagen", "*.png *.jpg *.jpeg *.webp"),
                ("PNG", "*.png"),
                ("JPG", "*.jpg *.jpeg"),
                ("WEBP", "*.webp"),
            ]
        )
        if not ruta:
            return

        try:
            carpeta = "assets"
            os.makedirs(carpeta, exist_ok=True)
            extension = os.path.splitext(ruta)[1].lower()
            destino = os.path.join(carpeta, f"logo_negocio{extension}")
            shutil.copy2(ruta, destino)
            ok, msg = self.db.guardar_configuracion("logo_path", destino)
            if ok:
                self.actualizar_preview_logo()
                messagebox.showinfo("Logo guardado", "El logo fue cargado correctamente.")
            else:
                messagebox.showerror("Error", msg)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo cargar el logo:\n{e}")

    def quitar_logo_negocio(self):
        if not messagebox.askyesno("Quitar logo", "¿Deseas quitar el logo del sistema?"):
            return
        ok, msg = self.db.guardar_configuracion("logo_path", "")
        if ok:
            self.actualizar_preview_logo()
            messagebox.showinfo("Logo quitado", "El sistema volverá a mostrar solo el nombre del negocio.")
        else:
            messagebox.showerror("Error", msg)

    def actualizar_preview_logo(self):
        if not hasattr(self, "logo_preview"):
            return

        self.logo_preview_image = cargar_logo_ctk(self.db, size=(96, 80))
        ruta_logo = self.db.obtener_configuracion("logo_path", "") if hasattr(self.db, "obtener_configuracion") else ""

        if self.logo_preview_image:
            self.logo_preview.configure(image=self.logo_preview_image, text="")
            if hasattr(self, "lbl_logo_ruta"):
                self.lbl_logo_ruta.configure(text=os.path.basename(str(ruta_logo)))
        else:
            self.logo_preview.configure(image=None, text="Sin logo")
            if hasattr(self, "lbl_logo_ruta"):
                self.lbl_logo_ruta.configure(text="PNG, JPG, JPEG o WEBP. Se copia al sistema local.")

    def aplicar_preset_colores(self, acento, primario):
        if not hasattr(self, "entries_apariencia"):
            return
        self.entries_apariencia["color_acento"].delete(0, "end")
        self.entries_apariencia["color_acento"].insert(0, acento)
        self.entries_apariencia["color_primario"].delete(0, "end")
        self.entries_apariencia["color_primario"].insert(0, primario)

    def cargar_formulario_configuracion(self):
        if not hasattr(self, "entries_config"):
            return
        negocio = self.db.obtener_datos_negocio()
        for clave, entry in self.entries_config.items():
            entry.delete(0, "end")
            entry.insert(0, str(negocio.get(clave, "")))

        self.actualizar_preview_logo()

        if hasattr(self, "combo_tema_modo") and hasattr(self.db, "obtener_apariencia"):
            apariencia = self.db.obtener_apariencia()
            self.combo_tema_modo.set(apariencia.get("tema_modo", "Oscuro"))
            for clave, entry in self.entries_apariencia.items():
                entry.delete(0, "end")
                entry.insert(0, str(apariencia.get(clave, "")))

    def guardar_configuracion_negocio(self):
        if not hasattr(self.db, "guardar_datos_negocio"):
            messagebox.showerror("Error", "Actualiza database.py para guardar la configuración.")
            return

        datos = {clave: entry.get().strip() for clave, entry in self.entries_config.items()}
        ok, msg = self.db.guardar_datos_negocio(datos)

        if ok and hasattr(self.db, "guardar_apariencia") and hasattr(self, "entries_apariencia"):
            apariencia = {
                "tema_modo": self.combo_tema_modo.get().strip(),
                "color_acento": self.entries_apariencia["color_acento"].get().strip(),
                "color_primario": self.entries_apariencia["color_primario"].get().strip(),
            }
            ok, msg_apariencia = self.db.guardar_apariencia(apariencia)
            if ok:
                msg = f"{msg}\n{msg_apariencia}"

        if ok:
            if callable(self.on_config_guardada):
                self.on_config_guardada()
            messagebox.showinfo(
                "Configuración guardada",
                f"{msg}\n\nLos cambios ya se reflejan en login y menú."
            )
        else:
            messagebox.showerror("Error", msg)
