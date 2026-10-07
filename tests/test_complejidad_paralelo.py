"""
Pruebas de complejidad espacial y algoritmos paralelos.
Ejecutar: python -m unittest tests.test_complejidad_paralelo
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import complejidad_espacial as ce
import algoritmos_paralelos as ap
from db import Database


class TestComplejidadEspacial(unittest.TestCase):
    def test_estatica_es_constante(self):
        r = ce.medir_memoria_estatica()
        self.assertEqual(r['total_bytes'], sum(r['variables'].values()))

    def test_dinamica_crece_con_los_datos(self):
        chico = ce.medir_memoria_dinamica([], [{'id': 1, 'name': 'a'}])
        grande = ce.medir_memoria_dinamica(
            [{'id': i, 'qty': 1} for i in range(50)],
            [{'id': i, 'name': 'x' * 10} for i in range(300)],
        )
        self.assertGreater(grande['total_bytes'], chico['total_bytes'])
        self.assertEqual(grande['complejidad_total'], 'O(n + k)')

    def test_jerarquia_tiene_tres_niveles(self):
        self.assertEqual(len(ce.analisis_jerarquia_memoria()['niveles']), 3)


class TestAlgoritmosParalelos(unittest.TestCase):
    def test_formulas(self):
        self.assertAlmostEqual(ap.calcular_speedup(10, 5), 2.0)
        self.assertAlmostEqual(ap.calcular_eficiencia(2.0, 4), 0.5)
        self.assertAlmostEqual(ap.calcular_overhead(10, 6, 2), 2.0)
        self.assertEqual(ap.calcular_speedup(10, 0), 0.0)
        self.assertEqual(ap.calcular_eficiencia(2.0, 0), 0.0)

    def test_isoeficiencia(self):
        self.assertEqual(ap.calcular_isoeficiencia('anillo')['orden'], 'p²')
        self.assertEqual(ap.calcular_isoeficiencia('inexistente')['orden'], 'p log p')

    def test_benchmark_con_base_real(self):
        with tempfile.TemporaryDirectory() as d:
            db = Database(Path(d) / 'tienda.db')
            db.seed_demo()
            m = ap.ejecutar_benchmark_paralelo(db, None)
            self.assertEqual(m.procesadores, 2)
            self.assertGreater(m.tiempo_secuencial, 0)
            self.assertGreater(m.tiempo_paralelo, 0)
            rep = ce.reporte_completo([], db.list_products())  # sqlite3.Row
            self.assertGreater(rep['dinamica']['inventario']['productos'], 0)


if __name__ == '__main__':
    unittest.main()
