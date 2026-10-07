"""
Pruebas unitarias de los algoritmos del curso.
Ejecutar: python -m unittest tests.test_algorithms
"""

import unittest
import sys
from pathlib import Path

# Permitir importar desde el directorio padre
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


class TestVoraz(unittest.TestCase):
    def test_desglose_exacto(self):
        d = desglosar_vuelto(47.80)
        total = sum(denom * cant for denom, cant in d)
        self.assertAlmostEqual(total, 47.80, places=2)

    def test_cero(self):
        self.assertEqual(desglosar_vuelto(0), [])

    def test_formato(self):
        d = desglosar_vuelto(150)
        texto = formatear_desglose(d)
        self.assertIn("S/", texto)


class TestBinarySearch(unittest.TestCase):
    def setUp(self):
        self.productos = [
            {"code": "A001", "name": "Arroz"},
            {"code": "B002", "name": "Azúcar"},
            {"code": "C003", "name": "Café"},
        ]
        self.sorted_p = merge_sort_by_code(self.productos)

    def test_encuentra(self):
        r = binary_search_by_code(self.sorted_p, "B002")
        self.assertIsNotNone(r)
        self.assertEqual(r["name"], "Azúcar")

    def test_no_encuentra(self):
        r = binary_search_by_code(self.sorted_p, "Z999")
        self.assertIsNone(r)

    def test_merge_sort(self):
        desordenado = [
            {"code": "C003", "name": "Café"},
            {"code": "A001", "name": "Arroz"},
            {"code": "B002", "name": "Azúcar"},
        ]
        ordenado = merge_sort_by_code(desordenado)
        codigos = [p["code"] for p in ordenado]
        self.assertEqual(codigos, ["A001", "B002", "C003"])


class TestRecursion(unittest.TestCase):
    def test_total_carrito(self):
        cart = [
            {"quantity": 2, "price": 4.50},
            {"quantity": 1, "price": 8.50},
        ]
        self.assertAlmostEqual(recursive_cart_total(cart), 17.50, places=2)

    def test_total_vacio(self):
        self.assertEqual(recursive_cart_total([]), 0.0)

    def test_agrupar(self):
        productos = [
            {"code": "1", "category": "Abarrotes"},
            {"code": "2", "category": "Lácteos"},
            {"code": "3", "category": "Abarrotes"},
        ]
        grupos = recursive_group_by_category(productos)
        self.assertEqual(len(grupos["Abarrotes"]), 2)
        self.assertEqual(len(grupos["Lácteos"]), 1)


class TestDP(unittest.TestCase):
    def test_mochila_basica(self):
        productos = [
            {"id": 1, "code": "A", "name": "P1", "stock": 1, "min_stock": 5,
             "purchase_price": 10, "sale_price": 15},
            {"id": 2, "code": "B", "name": "P2", "stock": 0, "min_stock": 3,
             "purchase_price": 20, "sale_price": 30},
            {"id": 3, "code": "C", "name": "P3", "stock": 2, "min_stock": 4,
             "purchase_price": 5, "sale_price": 8},
        ]
        res = optimal_restock(productos, presupuesto=25)
        self.assertGreaterEqual(res["total_profit"], 0)
        self.assertLessEqual(res["total_cost"], 25)


class TestMonteCarlo(unittest.TestCase):
    def test_simulacion_basica(self):
        productos = [
            {"code": "X", "name": "Prod", "stock": 10},
            {"code": "Y", "name": "Sin stock", "stock": 0},
        ]
        res = monte_carlo_demand_simulation(productos, dias=7, simulaciones=50)
        self.assertEqual(res["simulaciones"], 50)
        self.assertTrue(any(p["prob_quiebre"] == 1.0 for p in res["productos"]))


if __name__ == "__main__":
    unittest.main()
