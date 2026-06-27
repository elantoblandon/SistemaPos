import sqlite3
import re
import datetime
from difflib import SequenceMatcher
from tkinter import messagebox

try:
    from modules.your_image_pdf_processor import process_invoice
except Exception:
    process_invoice = None


class Database:
    def __init__(self, db_name="licorera_pro.db"):
        self.db_name = db_name
        self.conectar()
        self.crear_tablas()
        self.crear_admin_defecto()

    def conectar(self):
        """Establece la conexión con SQLite."""
        try:
            self.conexion = sqlite3.connect(self.db_name, check_same_thread=False)
            self.cursor = self.conexion.cursor()
        except sqlite3.Error as e:
            messagebox.showerror("Error de DB", f"No se pudo conectar: {e}")

    def crear_tablas(self):
        """Crea la estructura del sistema."""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                rol TEXT NOT NULL
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                precio_compra REAL NOT NULL,
                precio_venta REAL NOT NULL,
                stock INTEGER NOT NULL,
                categoria TEXT
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                total REAL NOT NULL,
                metodo_pago TEXT,
                usuario_id INTEGER,
                FOREIGN KEY(usuario_id) REFERENCES usuarios(id)
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS detalles_ventas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                venta_id INTEGER,
                producto_codigo TEXT,
                cantidad INTEGER,
                precio_unitario REAL,
                FOREIGN KEY(venta_id) REFERENCES ventas(id)
            )
        ''')

        # ======================================================
        # TABLAS NUEVAS: FACTURAS DE COMPRA DIGITALIZADAS
        # No modifican ni eliminan tablas existentes.
        # Sirven para guardar las facturas cargadas desde PDF/imagen
        # y consultar cuánto se invirtió por mes o año.
        # ======================================================
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS facturas_compras (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                archivo TEXT,
                proveedor TEXT,
                total_inversion REAL DEFAULT 0,
                observacion TEXT
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS facturas_compras_detalle (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                factura_id INTEGER NOT NULL,
                producto_codigo TEXT,
                producto_nombre TEXT NOT NULL,
                cantidad INTEGER NOT NULL,
                precio_compra REAL DEFAULT 0,
                subtotal REAL DEFAULT 0,
                encontrado INTEGER DEFAULT 0,
                FOREIGN KEY(factura_id) REFERENCES facturas_compras(id)
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS configuracion (
                clave TEXT PRIMARY KEY,
                valor TEXT
            )
        ''')

        self.conexion.commit()

    def crear_admin_defecto(self):
        try:
            self.cursor.execute(
                "INSERT OR IGNORE INTO usuarios (username, password, rol) VALUES (?, ?, ?)",
                ('admin', '1234', 'admin')
            )
            defaults_negocio = self._defaults_datos_negocio()
            for clave, valor in defaults_negocio.items():
                self.cursor.execute(
                    "INSERT OR IGNORE INTO configuracion (clave, valor) VALUES (?, ?)",
                    (clave, valor)
                )
            defaults_apariencia = self._defaults_apariencia()
            for clave, valor in defaults_apariencia.items():
                self.cursor.execute(
                    "INSERT OR IGNORE INTO configuracion (clave, valor) VALUES (?, ?)",
                    (clave, valor)
                )
            self.cursor.execute(
                "INSERT OR IGNORE INTO configuracion (clave, valor) VALUES (?, ?)",
                ("clave_dashboard", "1219")
            )
            self.conexion.commit()
        except Exception as e:
            print(f"Error admin: {e}")

    # ==========================================================
    # --- MÉTODOS DE USUARIO ---
    # ==========================================================

    def validar_usuario(self, user, password):
        try:
            self.cursor.execute(
                "SELECT rol FROM usuarios WHERE username = ? AND password = ?",
                (user, password)
            )
            res = self.cursor.fetchone()
            return res[0] if res else None
        except Exception as e:
            print(f"Error al validar usuario: {e}")
            return None

    def listar_usuarios(self):
        try:
            self.cursor.execute(
                "SELECT id, username, rol FROM usuarios ORDER BY username ASC"
            )
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error listando usuarios: {e}")
            return []

    def crear_usuario(self, username, password, rol="cajero"):
        try:
            username = str(username or "").strip()
            password = str(password or "").strip()
            rol = str(rol or "cajero").strip().lower()

            if not username or not password:
                return False, "Usuario y contraseña son obligatorios."

            if rol not in ("admin", "cajero"):
                return False, "Rol no válido."

            self.cursor.execute(
                "INSERT INTO usuarios (username, password, rol) VALUES (?, ?, ?)",
                (username, password, rol)
            )
            self.conexion.commit()
            return True, "Usuario creado correctamente."
        except sqlite3.IntegrityError:
            return False, "Ese usuario ya existe."
        except Exception as e:
            print(f"Error creando usuario: {e}")
            self.conexion.rollback()
            return False, "No se pudo crear el usuario."

    def cambiar_password_usuario(self, user_id, nueva_password):
        try:
            nueva_password = str(nueva_password or "").strip()
            if not nueva_password:
                return False, "La nueva contraseña no puede estar vacía."

            self.cursor.execute(
                "UPDATE usuarios SET password = ? WHERE id = ?",
                (nueva_password, user_id)
            )
            self.conexion.commit()
            if self.cursor.rowcount <= 0:
                return False, "Usuario no encontrado."
            return True, "Contraseña actualizada."
        except Exception as e:
            print(f"Error cambiando contraseña: {e}")
            self.conexion.rollback()
            return False, "No se pudo actualizar la contraseña."

    def eliminar_usuario(self, user_id):
        try:
            self.cursor.execute(
                "SELECT username, rol FROM usuarios WHERE id = ?",
                (user_id,)
            )
            usuario = self.cursor.fetchone()
            if not usuario:
                return False, "Usuario no encontrado."

            username, rol = usuario
            if username == "admin" or rol == "admin":
                self.cursor.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'admin'")
                total_admins = int(self.cursor.fetchone()[0] or 0)
                if total_admins <= 1:
                    return False, "No puedes eliminar el único administrador."

            self.cursor.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
            self.conexion.commit()
            if self.cursor.rowcount <= 0:
                return False, "No se pudo eliminar el usuario."
            return True, "Usuario eliminado."
        except Exception as e:
            print(f"Error eliminando usuario: {e}")
            self.conexion.rollback()
            return False, "No se pudo eliminar el usuario."

    def _defaults_datos_negocio(self):
        return {
            "nombre_sistema": "PlanetBoxer",
            "nombre_establecimiento": "PlanetBoxer",
            "nit": "1035416902",
            "ciudad": "Corozal - Colombia",
            "telefono": "3148283750",
            "logo_path": "",
            "subtitulo_sistema": "Gestión de Inventario y Ventas",
        }

    def _defaults_apariencia(self):
        return {
            "tema_modo": "Oscuro",
            "color_acento": "#10b981",
            "color_primario": "#3b82f6",
        }

    def obtener_configuracion(self, clave, valor_default=None):
        try:
            self.cursor.execute(
                "SELECT valor FROM configuracion WHERE clave = ?",
                (clave,)
            )
            res = self.cursor.fetchone()
            if res and res[0] is not None:
                return str(res[0])
            return valor_default
        except Exception as e:
            print(f"Error obteniendo configuración {clave}: {e}")
            return valor_default

    def guardar_configuracion(self, clave, valor):
        try:
            clave = str(clave or "").strip()
            valor = str(valor or "").strip()
            if not clave:
                return False, "Clave de configuración inválida."

            self.cursor.execute(
                """
                INSERT INTO configuracion (clave, valor)
                VALUES (?, ?)
                ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor
                """,
                (clave, valor)
            )
            self.conexion.commit()
            return True, "Configuración guardada."
        except Exception as e:
            print(f"Error guardando configuración {clave}: {e}")
            self.conexion.rollback()
            return False, "No se pudo guardar la configuración."

    def obtener_datos_negocio(self):
        """Datos de marca y factura para personalizar el sistema por cliente."""
        defaults = self._defaults_datos_negocio()
        datos = {}
        for clave, valor_defecto in defaults.items():
            datos[clave] = self.obtener_configuracion(clave, valor_defecto) or valor_defecto
        return datos

    def obtener_apariencia(self):
        """Devuelve modo visual y colores configurables."""
        defaults = self._defaults_apariencia()
        datos = {}
        for clave, valor_defecto in defaults.items():
            datos[clave] = self.obtener_configuracion(clave, valor_defecto) or valor_defecto

        modo = str(datos.get("tema_modo", "Oscuro")).strip().capitalize()
        datos["tema_modo"] = modo if modo in ("Oscuro", "Claro") else defaults["tema_modo"]
        return datos

    def guardar_apariencia(self, datos):
        """Guarda modo claro/oscuro y colores principales."""
        try:
            datos = datos or {}
            modo = str(datos.get("tema_modo", "Oscuro")).strip().capitalize()
            color_acento = str(datos.get("color_acento", "#10b981")).strip()
            color_primario = str(datos.get("color_primario", "#3b82f6")).strip()

            if modo not in ("Oscuro", "Claro"):
                return False, "El modo visual debe ser Oscuro o Claro."
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", color_acento):
                return False, "El color de acento debe tener formato #RRGGBB."
            if not re.fullmatch(r"#[0-9a-fA-F]{6}", color_primario):
                return False, "El color primario debe tener formato #RRGGBB."

            valores = {
                "tema_modo": modo,
                "color_acento": color_acento.lower(),
                "color_primario": color_primario.lower(),
            }

            for clave, valor in valores.items():
                ok, msg = self.guardar_configuracion(clave, valor)
                if not ok:
                    return False, msg

            return True, "Apariencia actualizada correctamente."
        except Exception as e:
            print(f"Error guardando apariencia: {e}")
            return False, "No se pudo guardar la apariencia."

    def guardar_datos_negocio(self, datos):
        """Guarda nombre del sistema, establecimiento y datos del ticket."""
        try:
            datos = datos or {}
            defaults = self._defaults_datos_negocio()

            nombre_sistema = str(datos.get("nombre_sistema", "")).strip()
            nombre_establecimiento = str(datos.get("nombre_establecimiento", "")).strip()
            nit = str(datos.get("nit", "")).strip()
            ciudad = str(datos.get("ciudad", "")).strip()
            telefono = str(datos.get("telefono", "")).strip()
            subtitulo = str(datos.get("subtitulo_sistema", "")).strip()

            if not nombre_sistema:
                return False, "El nombre del sistema es obligatorio."
            if not nombre_establecimiento:
                return False, "El nombre del establecimiento es obligatorio."

            valores = {
                "nombre_sistema": nombre_sistema,
                "nombre_establecimiento": nombre_establecimiento,
                "nit": nit or defaults["nit"],
                "ciudad": ciudad or defaults["ciudad"],
                "telefono": telefono or defaults["telefono"],
                "subtitulo_sistema": subtitulo or defaults["subtitulo_sistema"],
            }

            for clave, valor in valores.items():
                ok, msg = self.guardar_configuracion(clave, valor)
                if not ok:
                    return False, msg

            return True, "Datos del negocio actualizados correctamente."
        except Exception as e:
            print(f"Error guardando datos del negocio: {e}")
            return False, "No se pudieron guardar los datos del negocio."

    def obtener_clave_dashboard(self):
        try:
            self.cursor.execute(
                "SELECT valor FROM configuracion WHERE clave = ?",
                ("clave_dashboard",)
            )
            res = self.cursor.fetchone()
            return str(res[0]) if res and res[0] is not None else "1219"
        except Exception as e:
            print(f"Error obteniendo clave dashboard: {e}")
            return "1219"

    def actualizar_clave_dashboard(self, nueva_clave):
        try:
            nueva_clave = str(nueva_clave or "").strip()
            if not nueva_clave:
                return False, "La contraseña no puede estar vacía."

            self.cursor.execute(
                """
                INSERT INTO configuracion (clave, valor)
                VALUES (?, ?)
                ON CONFLICT(clave) DO UPDATE SET valor = excluded.valor
                """,
                ("clave_dashboard", nueva_clave)
            )
            self.conexion.commit()
            return True, "Clave de Dashboard actualizada."
        except Exception as e:
            print(f"Error actualizando clave dashboard: {e}")
            self.conexion.rollback()
            return False, "No se pudo actualizar la clave."

    # ==========================================================
    # --- MÉTODOS DE VENTA ---
    # ==========================================================

    def registrar_venta(self, carrito, total, metodo_pago, usuario_username="admin"):
        try:
            self.cursor.execute(
                "SELECT id FROM usuarios WHERE username = ?",
                (usuario_username,)
            )
            res_user = self.cursor.fetchone()
            user_id = res_user[0] if res_user else 1

            total_real = 0

            # Validar stock antes de guardar
            for item in carrito:
                cantidad = item.get('cantidad', 1)

                self.cursor.execute(
                    "SELECT stock, precio_venta FROM productos WHERE codigo = ?",
                    (item['sku'],)
                )
                res_p = self.cursor.fetchone()

                if not res_p:
                    raise Exception(f"Producto no encontrado: {item['sku']}")

                stock_actual, precio_v = res_p

                if stock_actual < cantidad:
                    raise Exception(f"Stock insuficiente para {item['sku']}")

                total_real += (precio_v * cantidad)

            self.cursor.execute(
                "INSERT INTO ventas (total, metodo_pago, usuario_id) VALUES (?, ?, ?)",
                (total_real, metodo_pago, user_id)
            )
            venta_id = self.cursor.lastrowid

            for item in carrito:
                self.cursor.execute(
                    "SELECT precio_venta FROM productos WHERE codigo = ?",
                    (item['sku'],)
                )
                res_p = self.cursor.fetchone()
                precio_final = res_p[0] if res_p else item['precio']

                cantidad = item.get('cantidad', 1)

                self.cursor.execute(
                    '''
                    INSERT INTO detalles_ventas
                    (venta_id, producto_codigo, cantidad, precio_unitario)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (venta_id, item['sku'], cantidad, precio_final)
                )

                self.cursor.execute(
                    "UPDATE productos SET stock = stock - ? WHERE codigo = ?",
                    (cantidad, item['sku'])
                )

            self.conexion.commit()
            return True

        except Exception as e:
            print(f"Error crítico al registrar venta: {e}")
            self.conexion.rollback()
            return False

    def obtener_detalles_productos_venta(self, venta_id):
        """
        Devuelve los productos vendidos en un ticket.
        Orden de columnas:
        nombre, cantidad, precio_unitario, precio_compra

        El precio_compra se incluye para que el cierre PDF pueda calcular
        correctamente la ganancia real.
        """
        try:
            query = """
                SELECT
                    p.nombre,
                    d.cantidad,
                    d.precio_unitario,
                    p.precio_compra
                FROM detalles_ventas d
                JOIN productos p ON d.producto_codigo = p.codigo
                WHERE d.venta_id = ?
            """
            self.cursor.execute(query, (venta_id,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error detalles: {e}")
            return []


    def eliminar_venta(self, venta_id):
        """
        Elimina una venta/ticket y sus detalles SIN devolver stock al inventario.

        Útil para quitar ventas de prueba de los reportes de Hoy, Mes, Año,
        cierres y estadísticas, sin alterar las existencias actuales.
        """
        try:
            self.cursor.execute(
                "SELECT id FROM ventas WHERE id = ?",
                (venta_id,)
            )
            existe = self.cursor.fetchone()

            if not existe:
                return False

            self.cursor.execute(
                "DELETE FROM detalles_ventas WHERE venta_id = ?",
                (venta_id,)
            )

            self.cursor.execute(
                "DELETE FROM ventas WHERE id = ?",
                (venta_id,)
            )

            self.conexion.commit()
            return True

        except Exception as e:
            print(f"Error eliminando venta: {e}")
            self.conexion.rollback()
            return False

    # ==========================================================
    # --- ESTADÍSTICAS ---
    # ==========================================================

    def _construir_condicion(self, periodo, valor_especifico):
        """Construye filtros de fecha usando hora local.
        Esto evita que las ventas hechas en la noche queden fuera de "Hoy"
        por diferencias entre UTC y la hora local del computador.
        """
        if periodo == "Hoy":
            return "date(fecha, 'localtime') = date('now', 'localtime')"

        elif periodo == "Ayer":
            return "date(fecha, 'localtime') = date('now', '-1 day', 'localtime')"

        elif periodo == "Mes" and valor_especifico:
            meses_map = {
                "Enero": "01", "Febrero": "02", "Marzo": "03", "Abril": "04",
                "Mayo": "05", "Junio": "06", "Julio": "07", "Agosto": "08",
                "Septiembre": "09", "Octubre": "10", "Noviembre": "11", "Diciembre": "12"
            }
            mes_num = meses_map.get(valor_especifico, "01")
            return (
                f"strftime('%m', fecha, 'localtime') = '{mes_num}' "
                f"AND strftime('%Y', fecha, 'localtime') = strftime('%Y', 'now', 'localtime')"
            )

        elif periodo == "Año" and valor_especifico:
            return f"strftime('%Y', fecha, 'localtime') = '{valor_especifico}'"

        return "1=1"

    def obtener_estadisticas_dashboard(self, periodo="Hoy", valor_especifico=None):
        condicion = self._construir_condicion(periodo, valor_especifico)

        self.cursor.execute(f"SELECT SUM(total) FROM ventas WHERE {condicion}")
        v = self.cursor.fetchone()[0] or 0.0

        self.cursor.execute(f"SELECT COUNT(id) FROM ventas WHERE {condicion}")
        p = self.cursor.fetchone()[0] or 0

        self.cursor.execute("SELECT COUNT(id) FROM productos WHERE stock <= 5")
        s = self.cursor.fetchone()[0] or 0

        return v, p, s

    def obtener_utilidad_periodo(self, periodo="Hoy", valor_especifico=None):
        condicion = self._construir_condicion(periodo, valor_especifico)

        query = f"""
            SELECT SUM((d.precio_unitario - p.precio_compra) * d.cantidad)
            FROM detalles_ventas d
            JOIN productos p ON d.producto_codigo = p.codigo
            JOIN ventas v ON d.venta_id = v.id
            WHERE {condicion.replace('fecha', 'v.fecha')}
        """
        self.cursor.execute(query)
        res = self.cursor.fetchone()[0]
        return res if res else 0.0

    def obtener_top_productos(self, periodo="Hoy", valor_especifico=None):
        condicion = self._construir_condicion(periodo, valor_especifico)

        query = f"""
            SELECT p.nombre, SUM(d.cantidad) as total_vendido
            FROM detalles_ventas d
            JOIN productos p ON d.producto_codigo = p.codigo
            JOIN ventas v ON d.venta_id = v.id
            WHERE {condicion.replace('fecha', 'v.fecha')}
            GROUP BY p.codigo
            ORDER BY total_vendido DESC
            LIMIT 5
        """
        self.cursor.execute(query)
        return self.cursor.fetchall()

    def obtener_listado_ventas_periodo(self, periodo="Hoy", valor_especifico=None):
        condicion = self._construir_condicion(periodo, valor_especifico)
        self.cursor.execute(
            f"SELECT id, strftime('%d/%m %H:%M', fecha, 'localtime'), total, metodo_pago FROM ventas WHERE {condicion} ORDER BY fecha DESC"
        )
        return self.cursor.fetchall()

    def obtener_datos_cierre_caja(self):
        """Ventas del día actual para cierre de caja."""
        hoy = datetime.datetime.now().strftime("%Y-%m-%d")
        return self.obtener_datos_cierre_fecha(hoy)

    def obtener_datos_cierre_fecha(self, fecha_iso):
        """
        Ventas de un día específico para cierre de caja.
        fecha_iso: 'YYYY-MM-DD' (hora local del equipo).
        """
        try:
            fecha_iso = str(fecha_iso or "").strip()
            datetime.datetime.strptime(fecha_iso, "%Y-%m-%d")
        except Exception:
            return []

        self.cursor.execute(
            """
            SELECT v.id,
                   strftime('%H:%M', v.fecha, 'localtime') AS hora,
                   v.total,
                   v.metodo_pago,
                   u.username
            FROM ventas v
            JOIN usuarios u ON v.usuario_id = u.id
            WHERE date(v.fecha, 'localtime') = ?
            ORDER BY v.fecha ASC
            """,
            (fecha_iso,)
        )
        ventas = self.cursor.fetchall()
        reporte = []

        for v in ventas:
            prods = self.obtener_detalles_productos_venta(v[0])
            reporte.append({"info_venta": v, "productos": prods})

        return reporte

    def obtener_datos_cierre_rango(self, dias_atras=7):
        """
        Devuelve las ventas y sus productos entre hoy y N días atrás (incluye hoy).
        No modifica datos; solo lectura para cierres semanales u otros rangos cortos.
        """
        try:
            dias_atras = int(dias_atras)
        except Exception:
            dias_atras = 7

        if dias_atras < 1:
            dias_atras = 1

        self.cursor.execute(
            """
            SELECT v.id,
                   strftime('%d/%m %H:%M', v.fecha, 'localtime') AS fecha_hora,
                   v.total,
                   v.metodo_pago,
                   u.username
            FROM ventas v
            JOIN usuarios u ON v.usuario_id = u.id
            WHERE date(v.fecha, 'localtime')
                  BETWEEN date('now', ? || ' day', 'localtime')
                  AND date('now', 'localtime')
            ORDER BY v.fecha ASC
            """,
            (-dias_atras + 1,)
        )
        ventas = self.cursor.fetchall()
        reporte = []

        for v in ventas:
            prods = self.obtener_detalles_productos_venta(v[0])
            reporte.append({"info_venta": v, "productos": prods})

        return reporte


    def obtener_resumen_cierre(self):
        """Devuelve un resumen profesional del cierre de caja del día actual."""
        try:
            # Total vendido y cantidad de tickets del día
            self.cursor.execute("""
                SELECT
                    COALESCE(SUM(total), 0),
                    COUNT(id)
                FROM ventas
                WHERE date(fecha, 'localtime') = date('now', 'localtime')
            """)
            total_vendido, total_tickets = self.cursor.fetchone()

            # Total de productos vendidos del día
            self.cursor.execute("""
                SELECT COALESCE(SUM(d.cantidad), 0)
                FROM detalles_ventas d
                JOIN ventas v ON d.venta_id = v.id
                WHERE date(v.fecha, 'localtime') = date('now', 'localtime')
            """)
            productos_vendidos = self.cursor.fetchone()[0]

            # Ganancia real del día: (precio vendido - precio compra) * cantidad
            self.cursor.execute("""
                SELECT COALESCE(SUM((d.precio_unitario - p.precio_compra) * d.cantidad), 0)
                FROM detalles_ventas d
                JOIN productos p ON d.producto_codigo = p.codigo
                JOIN ventas v ON d.venta_id = v.id
                WHERE date(v.fecha, 'localtime') = date('now', 'localtime')
            """)
            ganancia_real = self.cursor.fetchone()[0]

            total_vendido = float(total_vendido or 0)
            total_tickets = int(total_tickets or 0)
            productos_vendidos = int(productos_vendidos or 0)
            ganancia_real = float(ganancia_real or 0)

            return {
                # Nombres nuevos/descriptivos
                "total_vendido": total_vendido,
                "total_tickets": total_tickets,
                "productos_vendidos": productos_vendidos,
                "ganancia_real": ganancia_real,

                # Nombres compatibles con dashboards anteriores
                "total": total_vendido,
                "tickets": total_tickets,
                "productos": productos_vendidos,
                "ganancia": ganancia_real
            }

        except Exception as e:
            print(f"Error obteniendo resumen de cierre: {e}")
            return {
                "total_vendido": 0.0,
                "total_tickets": 0,
                "productos_vendidos": 0,
                "ganancia_real": 0.0,
                "total": 0.0,
                "tickets": 0,
                "productos": 0,
                "ganancia": 0.0
            }

    # ==========================================================
    # --- INVENTARIO ---
    # ==========================================================

    def guardar_producto(self, codigo, nombre, p_compra, p_venta, stock, cat):
        try:
            self.cursor.execute(
                "INSERT INTO productos (codigo, nombre, precio_compra, precio_venta, stock, categoria) VALUES (?, ?, ?, ?, ?, ?)",
                (codigo, nombre, p_compra, p_venta, stock, cat)
            )
            self.conexion.commit()
            return True
        except Exception as e:
            print(f"Error guardando producto: {e}")
            return False

    def obtener_productos(self):
        """
        Devuelve productos para la tabla de inventario.
        Orden de columnas:
        codigo, nombre, stock, precio_compra, precio_venta, categoria
        """
        self.cursor.execute(
            """
            SELECT codigo, nombre, stock, precio_compra, precio_venta, categoria
            FROM productos
            ORDER BY nombre ASC
            """
        )
        return self.cursor.fetchall()

    def obtener_producto_por_codigo(self, codigo):
        self.cursor.execute(
            "SELECT codigo, nombre, precio_compra, precio_venta, stock, categoria FROM productos WHERE codigo = ?",
            (codigo,)
        )
        return self.cursor.fetchone()

    def buscar_producto_por_codigo(self, codigo):
        self.cursor.execute("""
            SELECT codigo, nombre, precio_venta, stock
            FROM productos
            WHERE codigo = ?
        """, (codigo,))
        return self.cursor.fetchone()

    def actualizar_producto(self, codigo, nombre, p_compra, p_venta, stock, categoria):
        try:
            self.cursor.execute(
                """
                UPDATE productos
                SET nombre=?, precio_compra=?, precio_venta=?, stock=?, categoria=?
                WHERE codigo=?
                """,
                (nombre, p_compra, p_venta, stock, categoria, codigo)
            )
            self.conexion.commit()
            return True
        except Exception as e:
            print(f"Error actualizando producto: {e}")
            return False

    def eliminar_producto(self, codigo):
        try:
            self.cursor.execute("DELETE FROM productos WHERE codigo = ?", (codigo,))
            self.conexion.commit()
            return True
        except Exception as e:
            print(f"Error eliminando producto: {e}")
            return False

    def buscar_productos_coincidentes(self, query):
        t = f"%{query}%"
        self.cursor.execute(
            "SELECT codigo, nombre, precio_venta FROM productos WHERE nombre LIKE ? OR codigo LIKE ?",
            (t, t)
        )
        return self.cursor.fetchall()

    def obtener_productos_poco_stock(self):
        self.cursor.execute(
            "SELECT nombre, stock FROM productos WHERE stock <= 5 ORDER BY stock ASC"
        )
        return self.cursor.fetchall()

    def obtener_valor_inventario(self):
        """Calcula la inversión total actual del inventario: precio_compra * stock."""
        try:
            self.cursor.execute("""
                SELECT SUM(precio_compra * stock)
                FROM productos
            """)
            res = self.cursor.fetchone()[0]
            return float(res) if res else 0.0
        except Exception as e:
            print(f"Error calculando valor del inventario: {e}")
            return 0.0


    def obtener_valores_inventario(self):
        """
        Calcula dos valores del inventario actual:
        - inversion: precio_compra * stock
        - valor_venta: precio_venta * stock
        """
        try:
            self.cursor.execute("""
                SELECT
                    COALESCE(SUM(precio_compra * stock), 0),
                    COALESCE(SUM(precio_venta * stock), 0)
                FROM productos
            """)
            res = self.cursor.fetchone()

            inversion = float(res[0] or 0)
            valor_venta = float(res[1] or 0)

            return inversion, valor_venta

        except Exception as e:
            print(f"Error calculando valores del inventario: {e}")
            return 0.0, 0.0

    def obtener_resumen_inventario(self):
        """Devuelve métricas útiles del inventario para mostrar en el dashboard."""
        try:
            self.cursor.execute("""
                SELECT
                    COUNT(id),
                    COALESCE(SUM(stock), 0),
                    COALESCE(SUM(precio_compra * stock), 0),
                    COALESCE(SUM(precio_venta * stock), 0)
                FROM productos
            """)
            total_productos, total_unidades, valor_compra, valor_venta = self.cursor.fetchone()

            return {
                "total_productos": int(total_productos or 0),
                "total_unidades": int(total_unidades or 0),
                "valor_compra": float(valor_compra or 0),
                "valor_venta": float(valor_venta or 0),
                "ganancia_potencial": float((valor_venta or 0) - (valor_compra or 0))
            }
        except Exception as e:
            print(f"Error obteniendo resumen de inventario: {e}")
            return {
                "total_productos": 0,
                "total_unidades": 0,
                "valor_compra": 0.0,
                "valor_venta": 0.0,
                "ganancia_potencial": 0.0
            }

    def sumar_stock_producto(self, codigo, cantidad):
        """Suma unidades al stock de un producto existente."""
        try:
            cantidad = int(cantidad)
            if cantidad <= 0:
                return False

            self.cursor.execute(
                "UPDATE productos SET stock = stock + ? WHERE codigo = ?",
                (cantidad, codigo)
            )
            self.conexion.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            print(f"Error sumando stock: {e}")
            self.conexion.rollback()
            return False

    def _normalizar_texto_producto(self, texto):
        """Normaliza texto para comparar nombres de productos de facturas contra inventario."""
        texto = str(texto or "").lower().strip()
        reemplazos = {
            "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"
        }
        for original, nuevo in reemplazos.items():
            texto = texto.replace(original, nuevo)
        texto = re.sub(r"[^a-z0-9 ]+", " ", texto)
        texto = re.sub(r"\s+", " ", texto).strip()
        return texto

    def buscar_producto_por_nombre_aproximado(self, nombre, minimo_similitud=0.62):
        """
        Busca un producto por nombre exacto, parcial o aproximado.
        Devuelve la misma estructura de obtener_producto_por_codigo:
        (codigo, nombre, precio_compra, precio_venta, stock, categoria)
        """
        nombre_original = str(nombre or "").strip()
        if not nombre_original:
            return None

        # 1) Búsqueda parcial directa en SQLite
        like = f"%{nombre_original}%"
        self.cursor.execute(
            """
            SELECT codigo, nombre, precio_compra, precio_venta, stock, categoria
            FROM productos
            WHERE nombre LIKE ?
            LIMIT 1
            """,
            (like,)
        )
        res = self.cursor.fetchone()
        if res:
            return res

        # 2) Búsqueda aproximada en Python
        objetivo = self._normalizar_texto_producto(nombre_original)
        if not objetivo:
            return None

        self.cursor.execute(
            "SELECT codigo, nombre, precio_compra, precio_venta, stock, categoria FROM productos"
        )
        productos = self.cursor.fetchall()

        mejor_producto = None
        mejor_puntaje = 0.0

        for prod in productos:
            nombre_db = self._normalizar_texto_producto(prod[1])
            if not nombre_db:
                continue

            puntaje = SequenceMatcher(None, objetivo, nombre_db).ratio()

            # Bonus cuando una cadena contiene a la otra.
            if objetivo in nombre_db or nombre_db in objetivo:
                puntaje = max(puntaje, 0.90)

            if puntaje > mejor_puntaje:
                mejor_puntaje = puntaje
                mejor_producto = prod

        if mejor_producto and mejor_puntaje >= minimo_similitud:
            return mejor_producto

        return None

    # ==========================================================
    # --- FACTURAS DE COMPRA DIGITALIZADAS ---
    # ==========================================================

    def guardar_factura_compra(self, archivo="", proveedor="", productos=None, observacion=""):
        """
        Guarda una factura de compra digitalizada y su detalle.

        productos debe ser una lista de diccionarios con llaves posibles:
        - codigo / producto_codigo
        - nombre / producto_nombre
        - cantidad
        - precio_compra
        - subtotal
        - encontrado

        Esta función NO crea productos nuevos y NO modifica stock.
        El stock se debe sumar desde el flujo validado del dashboard.
        """
        productos = productos or []

        try:
            total_inversion = 0.0
            detalles_limpios = []

            for item in productos:
                codigo = str(item.get("codigo", item.get("producto_codigo", "")) or "").strip()
                nombre = str(item.get("nombre", item.get("producto_nombre", "")) or "").strip()

                try:
                    cantidad = int(float(str(item.get("cantidad", 0)).replace(",", ".")))
                except Exception:
                    cantidad = 0

                try:
                    precio_compra = float(str(item.get("precio_compra", 0)).replace(",", "."))
                except Exception:
                    precio_compra = 0.0

                try:
                    subtotal = float(str(item.get("subtotal", 0)).replace(",", "."))
                except Exception:
                    subtotal = 0.0

                if subtotal <= 0 and cantidad > 0 and precio_compra > 0:
                    subtotal = cantidad * precio_compra

                encontrado = 1 if item.get("encontrado", False) else 0

                if not nombre and codigo:
                    producto = self.obtener_producto_por_codigo(codigo)
                    if producto:
                        nombre = producto[1]

                if not nombre or cantidad <= 0:
                    continue

                total_inversion += subtotal
                detalles_limpios.append({
                    "codigo": codigo,
                    "nombre": nombre,
                    "cantidad": cantidad,
                    "precio_compra": precio_compra,
                    "subtotal": subtotal,
                    "encontrado": encontrado
                })

            self.cursor.execute(
                """
                INSERT INTO facturas_compras (archivo, proveedor, total_inversion, observacion)
                VALUES (?, ?, ?, ?)
                """,
                (archivo, proveedor, total_inversion, observacion)
            )
            factura_id = self.cursor.lastrowid

            for item in detalles_limpios:
                self.cursor.execute(
                    """
                    INSERT INTO facturas_compras_detalle
                    (factura_id, producto_codigo, producto_nombre, cantidad, precio_compra, subtotal, encontrado)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        factura_id,
                        item["codigo"],
                        item["nombre"],
                        item["cantidad"],
                        item["precio_compra"],
                        item["subtotal"],
                        item["encontrado"]
                    )
                )

            self.conexion.commit()
            return factura_id

        except Exception as e:
            print(f"Error guardando factura de compra: {e}")
            self.conexion.rollback()
            return None

    def _condicion_facturas_compra(self, periodo="Todas", valor_especifico=None):
        """Construye filtros de fecha para facturas de compra usando hora local."""
        if periodo == "Hoy":
            return "date(fecha, 'localtime') = date('now', 'localtime')"

        elif periodo == "Mes" and valor_especifico:
            meses_map = {
                "Enero": "01", "Febrero": "02", "Marzo": "03", "Abril": "04",
                "Mayo": "05", "Junio": "06", "Julio": "07", "Agosto": "08",
                "Septiembre": "09", "Octubre": "10", "Noviembre": "11", "Diciembre": "12"
            }
            mes_num = meses_map.get(valor_especifico, "01")
            return (
                f"strftime('%m', fecha, 'localtime') = '{mes_num}' "
                f"AND strftime('%Y', fecha, 'localtime') = strftime('%Y', 'now', 'localtime')"
            )

        elif periodo == "Año" and valor_especifico:
            return f"strftime('%Y', fecha, 'localtime') = '{valor_especifico}'"

        return "1=1"

    def obtener_facturas_compra(self, periodo="Todas", valor_especifico=None):
        """
        Devuelve facturas de compra guardadas.
        Orden: id, fecha_formateada, archivo, proveedor, total_inversion, observacion
        """
        try:
            condicion = self._condicion_facturas_compra(periodo, valor_especifico)
            self.cursor.execute(f"""
                SELECT
                    id,
                    strftime('%d/%m/%Y %H:%M', fecha, 'localtime') AS fecha_fmt,
                    archivo,
                    proveedor,
                    COALESCE(total_inversion, 0),
                    observacion
                FROM facturas_compras
                WHERE {condicion}
                ORDER BY fecha DESC
            """)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error obteniendo facturas de compra: {e}")
            return []

    def obtener_detalle_factura_compra(self, factura_id):
        """
        Devuelve el detalle de una factura de compra.
        Orden: producto_codigo, producto_nombre, cantidad, precio_compra, subtotal, encontrado
        """
        try:
            self.cursor.execute("""
                SELECT
                    producto_codigo,
                    producto_nombre,
                    cantidad,
                    COALESCE(precio_compra, 0),
                    COALESCE(subtotal, 0),
                    COALESCE(encontrado, 0)
                FROM facturas_compras_detalle
                WHERE factura_id = ?
                ORDER BY producto_nombre ASC
            """, (factura_id,))
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Error obteniendo detalle factura compra: {e}")
            return []

    def obtener_total_invertido_facturas(self, periodo="Todas", valor_especifico=None):
        """Devuelve el total invertido en facturas de compra según filtro."""
        try:
            condicion = self._condicion_facturas_compra(periodo, valor_especifico)
            self.cursor.execute(f"""
                SELECT COALESCE(SUM(total_inversion), 0)
                FROM facturas_compras
                WHERE {condicion}
            """)
            res = self.cursor.fetchone()[0]
            return float(res or 0)
        except Exception as e:
            print(f"Error obteniendo total invertido en facturas: {e}")
            return 0.0

    def eliminar_factura_compra(self, factura_id):
        """
        Elimina una factura de compra guardada y su detalle.
        No modifica productos ni stock.
        """
        try:
            self.cursor.execute("DELETE FROM facturas_compras_detalle WHERE factura_id = ?", (factura_id,))
            self.cursor.execute("DELETE FROM facturas_compras WHERE id = ?", (factura_id,))
            self.conexion.commit()
            return True
        except Exception as e:
            print(f"Error eliminando factura de compra: {e}")
            self.conexion.rollback()
            return False

    # ==========================================================
    # --- FACTURAS / PDF / IMAGEN ---
    # ==========================================================

    def _normalizar_items_factura(self, line_items):
        """
        Acepta productos extraídos en estos formatos:
        - [(nombre, cantidad), ...]
        - [{"nombre": ..., "cantidad": ...}, ...]
        - [{"codigo": ..., "nombre": ..., "cantidad": ...}, ...]
        """
        normalizados = []

        for item in line_items or []:
            codigo = ""
            nombre = ""
            cantidad = 0

            if isinstance(item, dict):
                codigo = str(item.get("codigo", "")).strip()
                nombre = str(item.get("nombre", "")).strip()
                cantidad = item.get("cantidad", 0)
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                nombre = str(item[0]).strip()
                cantidad = item[1]
            else:
                continue

            try:
                cantidad = int(float(str(cantidad).replace(",", ".").strip()))
            except Exception:
                cantidad = 0

            if cantidad <= 0:
                continue

            if codigo or nombre:
                normalizados.append({
                    "codigo": codigo,
                    "nombre": nombre,
                    "cantidad": cantidad
                })

        return normalizados

    def agregar_factura(self, file_path):
        """
        Procesa una factura desde imagen/PDF y suma stock a productos existentes.
        OJO: este método aplica los cambios directo. Para revisar antes de aplicar,
        usa el flujo del Dashboard modificado.
        """
        if process_invoice is None:
            print("No se pudo importar process_invoice")
            return {
                "ok": False,
                "actualizados": [],
                "no_encontrados": ["No se pudo importar process_invoice"]
            }

        actualizados = []
        no_encontrados = []

        try:
            line_items = process_invoice(file_path)
            items = self._normalizar_items_factura(line_items)

            for item in items:
                codigo = item.get("codigo", "")
                nombre = item.get("nombre", "")
                cantidad = item.get("cantidad", 0)

                producto = None
                if codigo:
                    producto = self.obtener_producto_por_codigo(codigo)

                if not producto and nombre:
                    producto = self.buscar_producto_por_nombre_aproximado(nombre)

                if not producto:
                    no_encontrados.append(nombre or codigo)
                    continue

                if self.sumar_stock_producto(producto[0], cantidad):
                    actualizados.append({
                        "codigo": producto[0],
                        "nombre": producto[1],
                        "cantidad": cantidad
                    })
                else:
                    no_encontrados.append(nombre or codigo)

            return {
                "ok": True,
                "actualizados": actualizados,
                "no_encontrados": no_encontrados
            }

        except Exception as e:
            print(f"Error al agregar factura: {e}")
            self.conexion.rollback()
            return {
                "ok": False,
                "actualizados": actualizados,
                "no_encontrados": no_encontrados,
                "error": str(e)
            }
