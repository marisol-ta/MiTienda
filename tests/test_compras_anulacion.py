"""
Pruebas de compras (aumento de stock) y anulación de ventas.
Ejecutar: python -m unittest tests.test_compras_anulacion
"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import Database


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self._tmp.name) / 'tienda.db')
        self.db.seed_demo()
        self.arroz = self.db.list_products('775001')[0]['id']
        self.aceite = self.db.list_products('775003')[0]['id']

    def tearDown(self):
        self._tmp.cleanup()

    def stock(self, pid):
        return float(self.db.get_product(pid)['stock'])

    def sell(self, qty=2):
        return self.db.create_sale(
            [{'product_id': self.arroz, 'name': 'Arroz', 'quantity': qty, 'price': 4.5}],
            'EFECTIVO', 100)


class TestCompras(Base):
    def test_compra_aumenta_stock_y_registra_movimientos(self):
        antes = self.stock(self.arroz)
        r = self.db.create_purchase(
            [{'product_id': self.arroz, 'quantity': 10, 'cost': 3.8}], supplier='Distribuidora X')
        self.assertEqual(self.stock(self.arroz), antes + 10)
        self.assertEqual(r['total'], 38.0)
        self.assertEqual(float(self.db.get_product(self.arroz)['purchase_price']), 3.8)
        with self.db.connect() as con:
            mov = con.execute("SELECT type,quantity,note FROM stock_movements "
                              "WHERE note LIKE 'Compra%'").fetchone()
            caja = con.execute("SELECT type,amount FROM cash_movements "
                               "WHERE purchase_id=?", (r['purchase_id'],)).fetchone()
        self.assertEqual((mov['type'], mov['quantity']), ('ENTRADA', 10))
        self.assertEqual((caja['type'], caja['amount']), ('EGRESO', 38.0))

    def test_compra_sin_caja(self):
        r = self.db.create_purchase(
            [{'product_id': self.arroz, 'quantity': 1, 'cost': 3}], register_cash=False)
        with self.db.connect() as con:
            n = con.execute("SELECT COUNT(*) n FROM cash_movements WHERE purchase_id=?",
                            (r['purchase_id'],)).fetchone()['n']
        self.assertEqual(n, 0)

    def test_validaciones(self):
        with self.assertRaises(ValueError):
            self.db.create_purchase([])
        with self.assertRaises(ValueError):
            self.db.create_purchase([{'product_id': self.arroz, 'quantity': 0, 'cost': 1}])
        with self.assertRaises(ValueError):
            self.db.create_purchase([{'product_id': self.arroz, 'quantity': 1, 'cost': -1}])

    def test_compra_es_atomica(self):
        antes = self.stock(self.arroz)
        with self.assertRaises(ValueError):
            self.db.create_purchase([
                {'product_id': self.arroz, 'quantity': 5, 'cost': 3},
                {'product_id': 99999, 'quantity': 1, 'cost': 1},
            ])
        self.assertEqual(self.stock(self.arroz), antes)
        self.assertEqual(len(self.db.list_purchases()), 0)

    def test_numeros_de_compra_correlativos(self):
        a = self.db.create_purchase([{'product_id': self.arroz, 'quantity': 1, 'cost': 1}])
        b = self.db.create_purchase([{'product_id': self.arroz, 'quantity': 1, 'cost': 1}])
        self.assertNotEqual(a['number'], b['number'])


class TestAnularVenta(Base):
    def test_anular_restituye_stock_y_revierte_caja(self):
        antes = self.stock(self.arroz)
        v = self.sell(2)
        self.assertEqual(self.stock(self.arroz), antes - 2)
        self.db.void_sale(v['sale_id'], 'Error de digitación')
        self.assertEqual(self.stock(self.arroz), antes)
        resumen = self.db.cash_summary_today()
        self.assertAlmostEqual(resumen['balance'], 0.0)
        with self.db.connect() as con:
            s = con.execute("SELECT status,void_reason FROM sales WHERE id=?",
                            (v['sale_id'],)).fetchone()
        self.assertEqual((s['status'], s['void_reason']), ('ANULADA', 'Error de digitación'))

    def test_anulada_no_cuenta_en_indicadores(self):
        v = self.sell(2)
        self.assertEqual(self.db.dashboard()['sales_count'], 1)
        self.db.void_sale(v['sale_id'], 'Cliente devolvió')
        d = self.db.dashboard()
        self.assertEqual((d['sales_count'], d['sales_total']), (0, 0))
        self.assertEqual(self.db.cash_summary_today()['sales_count'], 0)

    def test_no_se_puede_anular_dos_veces(self):
        v = self.sell()
        self.db.void_sale(v['sale_id'], 'Motivo')
        antes = self.stock(self.arroz)
        with self.assertRaises(ValueError):
            self.db.void_sale(v['sale_id'], 'Otra vez')
        self.assertEqual(self.stock(self.arroz), antes)

    def test_motivo_obligatorio_y_venta_inexistente(self):
        v = self.sell()
        with self.assertRaises(ValueError):
            self.db.void_sale(v['sale_id'], '   ')
        with self.assertRaises(ValueError):
            self.db.void_sale(99999, 'x')
        self.assertEqual(self.db.list_sales()[0]['status'], 'ACTIVA')

    def test_numero_de_venta_no_se_reutiliza(self):
        v1 = self.sell()
        self.db.void_sale(v1['sale_id'], 'x')
        v2 = self.sell()
        self.assertNotEqual(v1['number'], v2['number'])


class TestMigracion(unittest.TestCase):
    def test_base_antigua_se_actualiza(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'vieja.db'
            con = sqlite3.connect(path)
            con.executescript('''
                CREATE TABLE sales (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    sale_number TEXT NOT NULL UNIQUE, date TEXT NOT NULL,
                    subtotal REAL NOT NULL, total REAL NOT NULL, payment_method TEXT NOT NULL,
                    received REAL NOT NULL DEFAULT 0, change_amount REAL NOT NULL DEFAULT 0);
                CREATE TABLE cash_movements (id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL, type TEXT NOT NULL, concept TEXT NOT NULL,
                    amount REAL NOT NULL, payment_method TEXT DEFAULT 'EFECTIVO', sale_id INTEGER);
                INSERT INTO sales(sale_number,date,subtotal,total,payment_method)
                    VALUES('V20260101-0001','2026-01-01 10:00:00',5,5,'EFECTIVO');
            ''')
            con.commit(); con.close()
            db = Database(path)
            self.assertEqual(db.list_sales()[0]['status'], 'ACTIVA')
            Database(path)  # reabrir no debe fallar (migración idempotente)


if __name__ == '__main__':
    unittest.main()
