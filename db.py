"""
Capa de datos y lógica de negocio.
Separación de responsabilidades: main.py (UI) → db.py (lógica + persistencia) → SQLite.

Análisis de complejidad de las funciones principales (notación O grande):
  - list_products          : O(n log n)  — escaneo + ORDER BY del motor SQLite
  - get_product            : O(log n)    — búsqueda por PK (árbol B)
  - create_sale            : O(k log n)  — k ítems × búsquedas por clave
  - add_selected_to_cart   : O(k)        — búsqueda lineal en carrito (UI)
  - dashboard              : O(n)        — COUNT / SUM sobre productos
  - create_purchase        : O(k log n)  — k ítems × actualización por PK
  - void_sale              : O(k log n)  — reversa de k ítems de la venta
  - binary_search (alg)    : O(log n)    — búsqueda binaria en memoria
  - desglosar_vuelto       : O(1)        — d denominaciones constantes
  - optimal_restock (DP)   : O(n · W)    — mochila 0/1
  - monte_carlo            : O(s · n)    — s simulaciones
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

from algorithms import (
    desglosar_vuelto,
    formatear_desglose,
    binary_search_by_code,
    merge_sort_by_code,
    recursive_cart_total,
    recursive_group_by_category,
    optimal_restock,
    monte_carlo_demand_simulation,
)

APP_DIR = Path.home() / "TiendaAbarrotesData"
APP_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = APP_DIR / "tienda.db"


class Database:
    def __init__(self, path=DB_PATH):
        self.path = str(path)
        self.init_db()
        # Caché ordenada por código para búsqueda binaria (divide y vencerás)
        self._sorted_cache: List[Any] = []
        self._cache_dirty = True

    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row  # Registros: acceso por nombre de campo
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def init_db(self):
        with self.connect() as con:
            con.executescript('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                category TEXT DEFAULT '',
                unit TEXT DEFAULT 'UND',
                purchase_price REAL NOT NULL DEFAULT 0,
                sale_price REAL NOT NULL DEFAULT 0,
                stock REAL NOT NULL DEFAULT 0,
                min_stock REAL NOT NULL DEFAULT 0,
                active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sales (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_number TEXT NOT NULL UNIQUE,
                date TEXT NOT NULL,
                subtotal REAL NOT NULL,
                total REAL NOT NULL,
                payment_method TEXT NOT NULL,
                received REAL NOT NULL DEFAULT 0,
                change_amount REAL NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS sale_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sale_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                unit_price REAL NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY(sale_id) REFERENCES sales(id) ON DELETE CASCADE,
                FOREIGN KEY(product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS cash_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                concept TEXT NOT NULL,
                amount REAL NOT NULL,
                payment_method TEXT DEFAULT 'EFECTIVO',
                sale_id INTEGER,
                FOREIGN KEY(sale_id) REFERENCES sales(id)
            );

            CREATE TABLE IF NOT EXISTS stock_movements (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                product_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                quantity REAL NOT NULL,
                note TEXT DEFAULT '',
                FOREIGN KEY(product_id) REFERENCES products(id)
            );

            CREATE TABLE IF NOT EXISTS purchases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_number TEXT NOT NULL UNIQUE,
                date TEXT NOT NULL,
                supplier TEXT NOT NULL DEFAULT '',
                total REAL NOT NULL,
                payment_method TEXT NOT NULL DEFAULT 'EFECTIVO',
                note TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS purchase_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purchase_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                unit_cost REAL NOT NULL,
                line_total REAL NOT NULL,
                FOREIGN KEY(purchase_id) REFERENCES purchases(id) ON DELETE CASCADE,
                FOREIGN KEY(product_id) REFERENCES products(id)
            );
            ''')
            self._migrate(con)

    @staticmethod
    def _columns(con, table):
        return {r['name'] for r in con.execute(f"PRAGMA table_info({table})")}

    def _migrate(self, con):
        """Agrega columnas nuevas a bases creadas con versiones anteriores."""
        cols = self._columns(con, 'sales')
        if 'status' not in cols:
            con.execute("ALTER TABLE sales ADD COLUMN status TEXT NOT NULL DEFAULT 'ACTIVA'")
        if 'voided_at' not in cols:
            con.execute("ALTER TABLE sales ADD COLUMN voided_at TEXT")
        if 'void_reason' not in cols:
            con.execute("ALTER TABLE sales ADD COLUMN void_reason TEXT DEFAULT ''")
        if 'purchase_id' not in self._columns(con, 'cash_movements'):
            con.execute("ALTER TABLE cash_movements ADD COLUMN purchase_id INTEGER")

    def _invalidate_cache(self):
        self._cache_dirty = True

    def _ensure_sorted_cache(self):
        """Mantiene lista ordenada por código para búsqueda binaria O(log n)."""
        if not self._cache_dirty and self._sorted_cache:
            return
        with self.connect() as con:
            rows = con.execute(
                "SELECT * FROM products WHERE active=1"
            ).fetchall()
        # Convertir Row a dict para facilitar el ordenamiento propio
        productos = [dict(r) for r in rows]
        self._sorted_cache = merge_sort_by_code(productos)  # O(n log n) propio
        self._cache_dirty = False

    # ------------------------------------------------------------------
    # PRODUCTS
    # ------------------------------------------------------------------
    def list_products(self, search: str = ""):
        """
        Escaneo completo + ORDER BY name.
        Complejidad: O(n log n) por el ordenamiento interno de SQLite.
        Con LIKE '%texto%' no se usa índice → fuerza bruta O(n) en el filtro.
        """
        s = f"%{search.strip()}%"
        with self.connect() as con:
            return con.execute('''
                SELECT * FROM products
                WHERE active=1 AND (code LIKE ? OR name LIKE ? OR category LIKE ?)
                ORDER BY name COLLATE NOCASE
            ''', (s, s, s)).fetchall()

    def get_product(self, product_id: int):
        """
        Búsqueda por clave primaria.
        Complejidad: O(log n) — árbol B interno de SQLite.
        """
        with self.connect() as con:
            return con.execute(
                "SELECT * FROM products WHERE id=?", (product_id,)
            ).fetchone()

    def get_product_by_code_binary(self, codigo: str) -> Optional[Dict]:
        """
        Búsqueda binaria en memoria (divide y vencerás).
        Complejidad: O(log n) tras construir la caché O(n log n).
        """
        self._ensure_sorted_cache()
        return binary_search_by_code(self._sorted_cache, codigo)

    def save_product(self, data: Dict, product_id=None):
        values = (
            data['code'].strip(), data['name'].strip(), data['category'].strip(),
            data['unit'].strip().upper() or 'UND', float(data['purchase_price']),
            float(data['sale_price']), float(data['stock']), float(data['min_stock'])
        )
        with self.connect() as con:
            if product_id:
                old = con.execute(
                    "SELECT stock FROM products WHERE id=?", (product_id,)
                ).fetchone()
                con.execute('''
                    UPDATE products SET code=?,name=?,category=?,unit=?,
                    purchase_price=?,sale_price=?,stock=?,min_stock=? WHERE id=?
                ''', values + (product_id,))
                if old and float(old['stock']) != float(data['stock']):
                    diff = float(data['stock']) - float(old['stock'])
                    con.execute(
                        "INSERT INTO stock_movements(date,product_id,type,quantity,note) VALUES(?,?,?,?,?)",
                        (self.now(), product_id, 'AJUSTE', diff, 'Edición manual de stock')
                    )
            else:
                cur = con.execute('''
                    INSERT INTO products(code,name,category,unit,purchase_price,sale_price,stock,min_stock)
                    VALUES(?,?,?,?,?,?,?,?)
                ''', values)
                pid = cur.lastrowid
                if float(data['stock']) != 0:
                    con.execute(
                        "INSERT INTO stock_movements(date,product_id,type,quantity,note) VALUES(?,?,?,?,?)",
                        (self.now(), pid, 'ENTRADA', float(data['stock']), 'Stock inicial')
                    )
        self._invalidate_cache()

    def deactivate_product(self, product_id: int):
        """Soft-delete: active=0 para no romper historial de ventas (FK)."""
        with self.connect() as con:
            con.execute("UPDATE products SET active=0 WHERE id=?", (product_id,))
        self._invalidate_cache()

    def adjust_stock(self, product_id: int, qty, move_type: str, note: str = ""):
        qty = float(qty)
        delta = qty if move_type == 'ENTRADA' else -qty
        with self.connect() as con:
            p = con.execute(
                "SELECT stock FROM products WHERE id=? AND active=1", (product_id,)
            ).fetchone()
            if not p:
                raise ValueError("Producto no encontrado")
            new_stock = float(p['stock']) + delta
            if new_stock < 0:
                raise ValueError("El stock no puede quedar negativo")
            con.execute("UPDATE products SET stock=? WHERE id=?", (new_stock, product_id))
            con.execute(
                "INSERT INTO stock_movements(date,product_id,type,quantity,note) VALUES(?,?,?,?,?)",
                (self.now(), product_id, move_type, qty, note)
            )
        self._invalidate_cache()

    # ------------------------------------------------------------------
    # SALES
    # ------------------------------------------------------------------
    def next_sale_number(self) -> str:
        today = datetime.now().strftime('%Y%m%d')
        with self.connect() as con:
            n = con.execute(
                "SELECT COUNT(*) n FROM sales WHERE sale_number LIKE ?",
                (f"V{today}-%",)
            ).fetchone()['n'] + 1
        return f"V{today}-{n:04d}"

    def create_sale(self, cart: List[Dict], payment_method: str, received):
        """
        Flujo crítico del sistema (transacción atómica).
        Complejidad: O(k log n) — k ítems × búsquedas por PK.
        Si falla cualquier paso, SQLite revierte toda la transacción.
        """
        if not cart:
            raise ValueError("El carrito está vacío")

        # Total calculado también de forma recursiva (demostración)
        total_rec = recursive_cart_total(cart)
        total = round(sum(float(i['quantity']) * float(i['price']) for i in cart), 2)
        # Ambos deben coincidir
        assert abs(total - total_rec) < 0.01, "Inconsistencia en cálculo de total"

        received = float(received or 0)
        if payment_method == 'EFECTIVO' and received < total:
            raise ValueError("El monto recibido es menor al total")
        change = round(received - total, 2) if payment_method == 'EFECTIVO' else 0
        number = self.next_sale_number()
        dt = self.now()

        with self.connect() as con:
            # Validar stock bajo la misma transacción
            for item in cart:
                p = con.execute(
                    "SELECT name,stock FROM products WHERE id=? AND active=1",
                    (item['product_id'],)
                ).fetchone()
                if not p:
                    raise ValueError("Uno de los productos ya no está disponible")
                if float(item['quantity']) > float(p['stock']):
                    raise ValueError(
                        f"Stock insuficiente para {p['name']}. Disponible: {p['stock']}"
                    )
            cur = con.execute('''
                INSERT INTO sales(sale_number,date,subtotal,total,payment_method,received,change_amount)
                VALUES(?,?,?,?,?,?,?)
            ''', (number, dt, total, total, payment_method, received, change))
            sale_id = cur.lastrowid
            for item in cart:
                qty = float(item['quantity'])
                price = float(item['price'])
                con.execute('''
                    INSERT INTO sale_items(sale_id,product_id,quantity,unit_price,line_total)
                    VALUES(?,?,?,?,?)
                ''', (sale_id, item['product_id'], qty, price, round(qty * price, 2)))
                con.execute(
                    "UPDATE products SET stock=stock-? WHERE id=?",
                    (qty, item['product_id'])
                )
                con.execute(
                    "INSERT INTO stock_movements(date,product_id,type,quantity,note) VALUES(?,?,?,?,?)",
                    (dt, item['product_id'], 'SALIDA', qty, f'Venta {number}')
                )
            con.execute(
                "INSERT INTO cash_movements(date,type,concept,amount,payment_method,sale_id) VALUES(?,?,?,?,?,?)",
                (dt, 'INGRESO', f'Venta {number}', total, payment_method, sale_id)
            )

        self._invalidate_cache()

        # Desglose voraz del vuelto
        desglose = desglosar_vuelto(change) if change > 0 else []
        return {
            'sale_id': sale_id,
            'number': number,
            'total': total,
            'received': received,
            'change': change,
            'change_breakdown': desglose,
            'change_text': formatear_desglose(desglose),
            'date': dt,
        }

    def sales_today(self):
        today = datetime.now().strftime('%Y-%m-%d')
        with self.connect() as con:
            return con.execute(
                "SELECT * FROM sales WHERE date LIKE ? ORDER BY id DESC",
                (today + '%',)
            ).fetchall()

    def list_sales(self, limit: int = 200):
        """Ventas recientes (activas y anuladas), de la más nueva a la más antigua."""
        with self.connect() as con:
            return con.execute(
                "SELECT * FROM sales ORDER BY id DESC LIMIT ?", (int(limit),)
            ).fetchall()

    def get_sale_items(self, sale_id: int):
        with self.connect() as con:
            return con.execute('''
                SELECT si.*, p.name, p.code
                FROM sale_items si JOIN products p ON p.id = si.product_id
                WHERE si.sale_id = ?
            ''', (sale_id,)).fetchall()

    def void_sale(self, sale_id: int, reason: str):
        """
        Anula una venta (transacción atómica). Complejidad: O(k log n).
          - Marca la venta como ANULADA con motivo y fecha (no se borra: queda el historial).
          - Devuelve al stock las cantidades vendidas y registra una ENTRADA por ítem.
          - Registra un EGRESO en caja que revierte el ingreso de la venta.
        Una venta ya anulada no puede anularse otra vez.
        """
        reason = (reason or '').strip()
        if not reason:
            raise ValueError("Indica el motivo de la anulación")
        dt = self.now()
        with self.connect() as con:
            sale = con.execute("SELECT * FROM sales WHERE id=?", (sale_id,)).fetchone()
            if not sale:
                raise ValueError("La venta no existe")
            if sale['status'] == 'ANULADA':
                raise ValueError(f"La venta {sale['sale_number']} ya está anulada")
            items = con.execute(
                "SELECT product_id, quantity FROM sale_items WHERE sale_id=?", (sale_id,)
            ).fetchall()
            con.execute(
                "UPDATE sales SET status='ANULADA', voided_at=?, void_reason=? WHERE id=?",
                (dt, reason, sale_id)
            )
            for it in items:
                con.execute(
                    "UPDATE products SET stock=stock+? WHERE id=?",
                    (it['quantity'], it['product_id'])
                )
                con.execute(
                    "INSERT INTO stock_movements(date,product_id,type,quantity,note) VALUES(?,?,?,?,?)",
                    (dt, it['product_id'], 'ENTRADA', it['quantity'],
                     f"Anulación {sale['sale_number']}")
                )
            con.execute(
                "INSERT INTO cash_movements(date,type,concept,amount,payment_method,sale_id) VALUES(?,?,?,?,?,?)",
                (dt, 'EGRESO', f"Anulación {sale['sale_number']}", sale['total'],
                 sale['payment_method'], sale_id)
            )
        self._invalidate_cache()
        return {'sale_number': sale['sale_number'], 'total': sale['total'], 'items': len(items)}

    # ------------------------------------------------------------------
    # PURCHASES (compras a proveedores: aumentan el stock)
    # ------------------------------------------------------------------
    def next_purchase_number(self) -> str:
        today = datetime.now().strftime('%Y%m%d')
        with self.connect() as con:
            n = con.execute(
                "SELECT COUNT(*) n FROM purchases WHERE purchase_number LIKE ?",
                (f"C{today}-%",)
            ).fetchone()['n'] + 1
        return f"C{today}-{n:04d}"

    def create_purchase(self, items: List[Dict], supplier: str = '',
                        payment_method: str = 'EFECTIVO', register_cash: bool = True,
                        note: str = ''):
        """
        Registra una compra (transacción atómica). Complejidad: O(k log n).
        items: [{'product_id', 'quantity', 'cost'}]
          - Suma la cantidad comprada al stock y registra una ENTRADA por ítem.
          - Actualiza el precio de compra del producto con el último costo pagado.
          - Si register_cash=True, registra un EGRESO en caja por el total.
        """
        if not items:
            raise ValueError("La compra no tiene productos")
        clean = []
        for it in items:
            qty = float(it['quantity'])
            cost = float(it['cost'])
            if qty <= 0:
                raise ValueError("La cantidad debe ser mayor que cero")
            if cost < 0:
                raise ValueError("El costo no puede ser negativo")
            clean.append((int(it['product_id']), qty, cost))
        total = round(sum(q * c for _, q, c in clean), 2)
        number = self.next_purchase_number()
        dt = self.now()
        supplier = (supplier or '').strip()

        with self.connect() as con:
            for pid, _, _ in clean:
                if not con.execute(
                    "SELECT 1 FROM products WHERE id=? AND active=1", (pid,)
                ).fetchone():
                    raise ValueError("Uno de los productos ya no está disponible")
            cur = con.execute(
                "INSERT INTO purchases(purchase_number,date,supplier,total,payment_method,note) "
                "VALUES(?,?,?,?,?,?)",
                (number, dt, supplier, total, payment_method, note)
            )
            purchase_id = cur.lastrowid
            for pid, qty, cost in clean:
                con.execute(
                    "INSERT INTO purchase_items(purchase_id,product_id,quantity,unit_cost,line_total) "
                    "VALUES(?,?,?,?,?)",
                    (purchase_id, pid, qty, cost, round(qty * cost, 2))
                )
                con.execute(
                    "UPDATE products SET stock=stock+?, purchase_price=? WHERE id=?",
                    (qty, cost, pid)
                )
                con.execute(
                    "INSERT INTO stock_movements(date,product_id,type,quantity,note) VALUES(?,?,?,?,?)",
                    (dt, pid, 'ENTRADA', qty, f"Compra {number}")
                )
            if register_cash and total > 0:
                concept = f"Compra {number}" + (f" · {supplier}" if supplier else "")
                con.execute(
                    "INSERT INTO cash_movements(date,type,concept,amount,payment_method,purchase_id) "
                    "VALUES(?,?,?,?,?,?)",
                    (dt, 'EGRESO', concept, total, payment_method, purchase_id)
                )
        self._invalidate_cache()
        return {'purchase_id': purchase_id, 'number': number, 'total': total,
                'items': len(clean), 'date': dt}

    def list_purchases(self, limit: int = 200):
        with self.connect() as con:
            return con.execute(
                "SELECT * FROM purchases ORDER BY id DESC LIMIT ?", (int(limit),)
            ).fetchall()

    # ------------------------------------------------------------------
    # CASH
    # ------------------------------------------------------------------
    def add_cash_movement(self, move_type, concept, amount, payment_method='EFECTIVO'):
        amount = float(amount)
        if amount <= 0:
            raise ValueError("El monto debe ser mayor que cero")
        with self.connect() as con:
            con.execute(
                "INSERT INTO cash_movements(date,type,concept,amount,payment_method) VALUES(?,?,?,?,?)",
                (self.now(), move_type, concept.strip(), amount, payment_method)
            )

    def cash_movements_today(self):
        today = datetime.now().strftime('%Y-%m-%d')
        with self.connect() as con:
            return con.execute(
                "SELECT * FROM cash_movements WHERE date LIKE ? ORDER BY id DESC",
                (today + '%',)
            ).fetchall()

    def cash_summary_today(self):
        today = datetime.now().strftime('%Y-%m-%d')
        with self.connect() as con:
            r = con.execute('''
                SELECT
                  COALESCE(SUM(CASE WHEN type='INGRESO' THEN amount ELSE 0 END),0) ingresos,
                  COALESCE(SUM(CASE WHEN type='EGRESO' THEN amount ELSE 0 END),0) egresos,
                  COALESCE(SUM(CASE WHEN type='INGRESO' AND payment_method='EFECTIVO' THEN amount ELSE 0 END),0) efectivo_ing,
                  COALESCE(SUM(CASE WHEN type='EGRESO' AND payment_method='EFECTIVO' THEN amount ELSE 0 END),0) efectivo_egr
                FROM cash_movements WHERE date LIKE ?
            ''', (today + '%',)).fetchone()
            sales_count = con.execute(
                "SELECT COUNT(*) n FROM sales WHERE date LIKE ? AND status='ACTIVA'",
                (today + '%',)
            ).fetchone()['n']
        return dict(r) | {
            'sales_count': sales_count,
            'balance': float(r['ingresos']) - float(r['egresos']),
            'cash_balance': float(r['efectivo_ing']) - float(r['efectivo_egr']),
        }

    def dashboard(self):
        """
        Complejidad: O(n) — COUNT y SUM sobre la tabla de productos.
        """
        today = datetime.now().strftime('%Y-%m-%d')
        with self.connect() as con:
            products = con.execute(
                "SELECT COUNT(*) n FROM products WHERE active=1"
            ).fetchone()['n']
            low = con.execute(
                "SELECT COUNT(*) n FROM products WHERE active=1 AND stock<=min_stock"
            ).fetchone()['n']
            stock_value = con.execute(
                "SELECT COALESCE(SUM(stock*purchase_price),0) v FROM products WHERE active=1"
            ).fetchone()['v']
            sales_total = con.execute(
                "SELECT COALESCE(SUM(total),0) v FROM sales WHERE date LIKE ? AND status='ACTIVA'",
                (today + '%',)
            ).fetchone()['v']
            sales_count = con.execute(
                "SELECT COUNT(*) n FROM sales WHERE date LIKE ? AND status='ACTIVA'",
                (today + '%',)
            ).fetchone()['n']
        return {
            'products': products,
            'low': low,
            'stock_value': stock_value,
            'sales_total': sales_total,
            'sales_count': sales_count,
        }

    # ------------------------------------------------------------------
    # ALGORITMOS AVANZADOS (expuestos para la UI)
    # ------------------------------------------------------------------
    def sugerir_reposicion(self, presupuesto: float) -> Dict:
        """Programación dinámica: mochila 0/1 para maximizar ganancia."""
        productos = [dict(r) for r in self.list_products()]
        return optimal_restock(productos, presupuesto)

    def simular_demanda(self, dias: int = 30, simulaciones: int = 400) -> Dict:
        """Algoritmo probabilista: Monte Carlo de quiebre de stock."""
        productos = [dict(r) for r in self.list_products()]
        return monte_carlo_demand_simulation(productos, dias, simulaciones)

    def agrupar_por_categoria(self) -> Dict:
        """Recursividad: agrupa productos por categoría."""
        productos = [dict(r) for r in self.list_products()]
        return recursive_group_by_category(productos)

    def seed_demo(self):
        with self.connect() as con:
            count = con.execute("SELECT COUNT(*) n FROM products").fetchone()['n']
            if count:
                return False
            samples = [
                ('775001', 'Arroz Extra 1 kg', 'Abarrotes', 'UND', 3.60, 4.50, 40, 8),
                ('775002', 'Azúcar Rubia 1 kg', 'Abarrotes', 'UND', 3.20, 4.00, 35, 8),
                ('775003', 'Aceite Vegetal 900 ml', 'Abarrotes', 'UND', 7.20, 8.50, 24, 6),
                ('775004', 'Leche Evaporada 400 g', 'Lácteos', 'UND', 3.50, 4.20, 36, 8),
                ('775005', 'Fideos Spaghetti 500 g', 'Abarrotes', 'UND', 2.30, 3.00, 30, 5),
                ('775006', 'Atún 170 g', 'Conservas', 'UND', 5.20, 6.50, 18, 4),
                ('775007', 'Galletas Soda', 'Galletas', 'UND', 1.20, 1.80, 50, 10),
                ('775008', 'Detergente 750 g', 'Limpieza', 'UND', 5.80, 7.00, 20, 5),
                ('775009', 'Café Instantáneo 50 g', 'Abarrotes', 'UND', 4.50, 6.00, 3, 5),
                ('775010', 'Jabón Líquido 500 ml', 'Limpieza', 'UND', 6.00, 8.50, 2, 4),
            ]
            con.executemany('''
                INSERT INTO products(code,name,category,unit,purchase_price,sale_price,stock,min_stock)
                VALUES(?,?,?,?,?,?,?,?)
            ''', samples)
            ids = con.execute("SELECT id,stock FROM products").fetchall()
            for r in ids:
                con.execute(
                    "INSERT INTO stock_movements(date,product_id,type,quantity,note) VALUES(?,?,?,?,?)",
                    (self.now(), r['id'], 'ENTRADA', r['stock'], 'Datos de demostración')
                )
        self._invalidate_cache()
        return True

    @staticmethod
    def now():
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
