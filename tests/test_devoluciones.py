"""
Pruebas del protocolo de devoluciones, backtracking y catálogo de 15 productos.
Ejecutar: python -m unittest tests.test_devoluciones
"""
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from db import Database
from algorithms import backtracking_cambio


def fecha(dias):
    return (datetime.now() + timedelta(days=dias)).strftime('%Y-%m-%d')


class Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self._tmp.name) / 'tienda.db')
        self.db.seed_catalog_15()
        self.yogurt = self.pid('776004')    # Lácteos 6.80
        self.queso = self.pid('776005')     # Lácteos 8.50
        self.mantequilla = self.pid('776006')  # Lácteos 6.50

    def tearDown(self):
        self._tmp.cleanup()

    def pid(self, code):
        return self.db.list_products(code)[0]['id']

    def stock(self, pid):
        return float(self.db.get_product(pid)['stock'])

    def cash_total(self, typ):
        return sum(r['amount'] for r in self.db.cash_movements_today() if r['type'] == typ)


class TestCatalogo(Base):
    def test_15_productos_5_categorias(self):
        prods = self.db.list_products()
        self.assertEqual(len(prods), 15)
        cats = {}
        for p in prods:
            cats[p['category']] = cats.get(p['category'], 0) + 1
        self.assertEqual(len(cats), 5)
        self.assertTrue(all(n == 3 for n in cats.values()))

    def test_idempotente(self):
        self.assertEqual(self.db.seed_catalog_15(), 0)
        self.assertEqual(len(self.db.list_products()), 15)


class TestBacktracking(unittest.TestCase):
    def test_combinacion_exacta(self):
        c = [{'id': 1, 'name': 'A', 'sale_price': 4.5, 'stock': 10},
             {'id': 2, 'name': 'B', 'sale_price': 3.0, 'stock': 5}]
        r = backtracking_cambio(c, 9.0)
        self.assertEqual(r['total'], 9.0)
        self.assertEqual(r['diferencia'], 0.0)

    def test_nunca_supera_credito_ni_stock(self):
        c = [{'id': 1, 'name': 'A', 'sale_price': 5.0, 'stock': 1},
             {'id': 2, 'name': 'B', 'sale_price': 3.0, 'stock': 10}]
        r = backtracking_cambio(c, 11.0)
        self.assertLessEqual(r['total'], 11.0)
        for it in r['items']:
            if it['id'] == 1:
                self.assertLessEqual(it['qty'], 1)
        self.assertEqual(r['total'], 11.0)   # 5 + 3 + 3

    def test_sin_candidatos(self):
        r = backtracking_cambio([], 10)
        self.assertEqual(r['items'], [])
        self.assertEqual(r['diferencia'], 10)


class TestRegistro(Base):
    def test_registrar_no_toca_stock(self):
        antes = self.stock(self.yogurt)
        self.db.register_return(self.yogurt, 1, 'VENCIMIENTO', fecha(-3))
        self.assertEqual(self.stock(self.yogurt), antes)
        self.assertEqual(self.db.list_returns('PENDIENTE')[0]['status'], 'PENDIENTE')

    def test_validaciones(self):
        with self.assertRaises(ValueError):
            self.db.register_return(self.yogurt, 0, 'VENCIMIENTO', fecha(-1))
        with self.assertRaises(ValueError):
            self.db.register_return(self.yogurt, 1, 'VENCIMIENTO', '')
        with self.assertRaises(ValueError):
            self.db.register_return(self.yogurt, 1, 'VENCIMIENTO', '31/12/2025')
        with self.assertRaises(ValueError):
            self.db.register_return(self.yogurt, 1, 'MAL_ESTADO', '', '')
        with self.assertRaises(ValueError):
            self.db.register_return(self.yogurt, 1, 'OTRO')


class TestEvaluacion(Base):
    def test_aprobada_cambio_descuenta_stock_y_registra_merma(self):
        r = self.db.register_return(self.yogurt, 1, 'VENCIMIENTO', fecha(-2))
        s_yog, s_que = self.stock(self.yogurt), self.stock(self.queso)
        res = self.db.evaluate_return(
            r['id'], 'APROBADA', 'Vencido confirmado', 'CAMBIO',
            [{'id': self.yogurt, 'qty': 1}])
        self.assertEqual(res['difference'], 0.0)
        # el reemplazo sale del stock; el producto devuelto NO vuelve
        self.assertEqual(self.stock(self.yogurt), s_yog - 1)
        self.assertEqual(self.stock(self.queso), s_que)
        tipos = [m['type'] for m in self._movs(self.yogurt)]
        self.assertIn('MERMA', tipos)
        self.assertEqual(self.db.get_return(r['id'])['status'], 'APROBADA')
        self.assertEqual(len(self.db.get_return_items(r['id'])), 1)

    def _movs(self, pid):
        with self.db.connect() as con:
            return con.execute(
                "SELECT * FROM stock_movements WHERE product_id=?", (pid,)).fetchall()

    def test_cambio_por_producto_mas_caro_cobra_diferencia(self):
        r = self.db.register_return(self.yogurt, 1, 'MAL_ESTADO', '', 'Envase inflado')
        res = self.db.evaluate_return(
            r['id'], 'APROBADA', 'Envase inflado', 'CAMBIO',
            [{'id': self.queso, 'qty': 1}])
        self.assertAlmostEqual(res['difference'], 1.70, places=2)
        self.assertAlmostEqual(self.cash_total('INGRESO'), 1.70, places=2)

    def test_cambio_por_mas_barato_devuelve_vuelto(self):
        r = self.db.register_return(self.queso, 1, 'MAL_ESTADO', '', 'Moho')
        res = self.db.evaluate_return(
            r['id'], 'APROBADA', 'Moho', 'CAMBIO',
            [{'id': self.mantequilla, 'qty': 1}])
        self.assertAlmostEqual(res['difference'], -2.00, places=2)
        self.assertAlmostEqual(self.cash_total('EGRESO'), 2.00, places=2)

    def test_reembolso(self):
        r = self.db.register_return(self.yogurt, 2, 'VENCIMIENTO', fecha(-1))
        s = self.stock(self.yogurt)
        self.db.evaluate_return(r['id'], 'APROBADA', 'Vencido', 'REEMBOLSO')
        self.assertEqual(self.stock(self.yogurt), s)
        self.assertAlmostEqual(self.cash_total('EGRESO'), 13.60, places=2)

    def test_rechazada_no_modifica_nada(self):
        r = self.db.register_return(self.yogurt, 1, 'MAL_ESTADO', '', 'Dice que sabe raro')
        s = self.stock(self.yogurt)
        self.db.evaluate_return(r['id'], 'RECHAZADA', 'Producto en buen estado')
        self.assertEqual(self.stock(self.yogurt), s)
        self.assertEqual(self.db.get_return(r['id'])['status'], 'RECHAZADA')
        self.assertEqual(self.cash_total('EGRESO'), 0)
        self.assertEqual(self._movs(self.yogurt)[-1]['type'], 'ENTRADA')

    def test_vencimiento_futuro_no_se_puede_aprobar(self):
        r = self.db.register_return(self.yogurt, 1, 'VENCIMIENTO', fecha(10))
        with self.assertRaises(ValueError):
            self.db.evaluate_return(r['id'], 'APROBADA', 'ok', 'REEMBOLSO')
        self.assertEqual(self.db.get_return(r['id'])['status'], 'PENDIENTE')

    def test_stock_insuficiente_revierte_todo(self):
        r = self.db.register_return(self.yogurt, 1, 'VENCIMIENTO', fecha(-1))
        s = self.stock(self.queso)
        with self.assertRaises(ValueError):
            self.db.evaluate_return(
                r['id'], 'APROBADA', 'ok', 'CAMBIO',
                [{'id': self.queso, 'qty': 1}, {'id': self.mantequilla, 'qty': 9999}])
        self.assertEqual(self.stock(self.queso), s)
        self.assertEqual(self.db.get_return(r['id'])['status'], 'PENDIENTE')

    def test_no_se_evalua_dos_veces(self):
        r = self.db.register_return(self.yogurt, 1, 'VENCIMIENTO', fecha(-1))
        self.db.evaluate_return(r['id'], 'RECHAZADA', 'No procede')
        with self.assertRaises(ValueError):
            self.db.evaluate_return(r['id'], 'APROBADA', 'x', 'REEMBOLSO')

    def test_cambio_requiere_productos_y_notas(self):
        r = self.db.register_return(self.yogurt, 1, 'VENCIMIENTO', fecha(-1))
        with self.assertRaises(ValueError):
            self.db.evaluate_return(r['id'], 'APROBADA', 'ok', 'CAMBIO', [])
        with self.assertRaises(ValueError):
            self.db.evaluate_return(r['id'], 'APROBADA', '', 'REEMBOLSO')

    def test_sugerir_cambio_backtracking(self):
        r = self.db.register_return(self.queso, 1, 'MAL_ESTADO', '', 'Moho')   # crédito 8.50
        sug = self.db.sugerir_cambio(r['id'], misma_categoria=True)
        self.assertLessEqual(sug['total'], 8.50)
        self.assertGreater(len(sug['items']), 0)
        res = self.db.evaluate_return(
            r['id'], 'APROBADA', 'Moho confirmado', 'CAMBIO',
            [{'id': i['id'], 'qty': i['qty']} for i in sug['items']])
        self.assertLessEqual(res['exchange_total'], 8.50)


if __name__ == '__main__':
    unittest.main()
