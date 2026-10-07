"""
Módulo de análisis de complejidad espacial.
Basado en el documento 'Complejidad Computacional Espacial'.

Clasifica la memoria utilizada por el sistema en:
  - Memoria estática: variables declaradas, tipos primitivos
  - Memoria dinámica: estructuras de datos (listas, dicts, pilas, colas)

Cada tipo de dato primitivo tiene un tamaño en bytes (según tabla del documento):
  byte: 1, char: 2, short: 2, int: 4, float: 4, long: 8, double: 8
"""

from typing import Dict, List, Any
import sys


# Tabla de tipos primitivos del documento (tamaño en bytes)
TAMANO_PRIMITIVOS = {
    'byte': 1,
    'char': 2,
    'short': 2,
    'int': 4,
    'float': 4,
    'long': 8,
    'double': 8,
}

# En Python, los tamaños reales son mayores (overhead del intérprete).
# Se usa sys.getsizeof() para medición real, pero se documenta el modelo teórico.


def medir_memoria_estatica() -> Dict[str, Any]:
    """
    Calcula la memoria estática del programa: variables simples declaradas.

    En este sistema, las variables estáticas son:
      - self.cart: lista (referencia)
      - self.selected_product_id: int
      - self.sale_search, self.wh_search: StringVar (Tkinter)
      - self.pay_method, self.received: StringVar
      - Contadores y banderas en bucles

    Complejidad espacial: O(1) — cantidad fija de variables.
    """
    variables = {
        'cart_reference': sys.getsizeof([]),          # 56 bytes (lista vacía)
        'selected_product_id': sys.getsizeof(None),   # 16 bytes
        'sale_search_var': 64,                        # StringVar Tkinter (aprox)
        'wh_search_var': 64,
        'pay_method_var': 64,
        'received_var': 64,
        'contadores_bucles': 28,                      # int pequeño
        'banderas_booleanas': 28,
    }
    total = sum(variables.values())
    return {
        'variables': variables,
        'total_bytes': total,
        'total_kb': round(total / 1024, 3),
        'nota': 'Memoria estática O(1): no depende del tamaño de la entrada.',
    }


def _a_dict(registro) -> Dict[str, Any]:
    """Convierte sqlite3.Row (o dict) a dict para poder medirlo."""
    return registro if isinstance(registro, dict) else dict(registro)


def medir_memoria_dinamica(cart: List[Dict], productos: List[Dict]) -> Dict[str, Any]:
    """
    Calcula la memoria dinámica: estructuras que crecen con los datos.

    - Carrito (lista de diccionarios): O(k) donde k = ítems en carrito
    - Inventario (lista de registros): O(n) donde n = productos activos
    - Caché ordenada para búsqueda binaria: O(n)
    - Estructuras temporales (merge sort): O(n) espacio auxiliar

    Complejidad espacial total: O(n + k)
    """
    cart = [_a_dict(i) for i in cart]
    productos = [_a_dict(p) for p in productos]

    # Memoria del carrito
    memoria_cart = sys.getsizeof(cart)
    for item in cart:
        memoria_cart += sys.getsizeof(item)
        for key, value in item.items():
            memoria_cart += sys.getsizeof(key) + sys.getsizeof(value)

    # Memoria del inventario
    memoria_productos = sys.getsizeof(productos)
    for p in productos[:100]:  # Muestra de 100 para no saturar
        memoria_productos += sys.getsizeof(p)
        for key, value in p.items():
            memoria_productos += sys.getsizeof(key) + sys.getsizeof(value)
    # Extrapolar si hay más de 100
    if len(productos) > 100:
        factor = len(productos) / 100
        memoria_productos = int(memoria_productos * factor)

    # Caché ordenada (merge sort auxiliar)
    memoria_cache = memoria_productos  # mismo orden de magnitud

    total = memoria_cart + memoria_productos + memoria_cache

    return {
        'carrito': {
            'items': len(cart),
            'bytes': memoria_cart,
            'kb': round(memoria_cart / 1024, 3),
            'complejidad': 'O(k)',
        },
        'inventario': {
            'productos': len(productos),
            'bytes': memoria_productos,
            'kb': round(memoria_productos / 1024, 3),
            'complejidad': 'O(n)',
        },
        'cache_busqueda_binaria': {
            'bytes': memoria_cache,
            'kb': round(memoria_cache / 1024, 3),
            'complejidad': 'O(n)',
        },
        'total_bytes': total,
        'total_kb': round(total / 1024, 3),
        'complejidad_total': 'O(n + k)',
        'nota': 'Memoria dinámica: crece con el número de productos (n) y de ítems en carrito (k).',
    }


def analisis_jerarquia_memoria() -> Dict[str, Any]:
    """
    Describe los 3 niveles de memoria del documento:
      - Memoria caché (RAM estática): velocidad comparable al CPU
      - Memoria física principal (RAM dinámica): más lenta que CPU
      - Memoria virtual (disco): miles de veces más lenta

    Complejidad espacial del sistema: O(n + k)
    """
    return {
        'niveles': [
            {
                'nombre': 'Memoria caché (RAM estática)',
                'velocidad': '~1 ns',
                'uso_en_sistema': 'Variables locales, contadores de bucles, índices de búsqueda',
                'complejidad': 'O(1)',
            },
            {
                'nombre': 'Memoria física principal (RAM dinámica)',
                'velocidad': '~100 ns',
                'uso_en_sistema': 'Lista de productos, carrito, caché ordenada',
                'complejidad': 'O(n + k)',
            },
            {
                'nombre': 'Memoria virtual (disco)',
                'velocidad': '~10 ms',
                'uso_en_sistema': 'Base de datos SQLite (tienda.db), archivos temporales',
                'complejidad': 'O(n) en disco',
            },
        ],
        'conclusion': (
            'El sistema mantiene los datos críticos en RAM (O(n+k)). '
            'SQLite gestiona la persistencia en disco con transacciones ACID. '
            'Las computadoras modernas con 16 GB+ hacen que la restricción de memoria '
            'sea menos crítica que en la EDSAC (1024 palabras de 17 bits, 1949).'
        ),
    }


def reporte_completo(cart: List[Dict], productos: List[Dict]) -> Dict[str, Any]:
    """Genera reporte unificado de complejidad espacial."""
    return {
        'estatica': medir_memoria_estatica(),
        'dinamica': medir_memoria_dinamica(cart, productos),
        'jerarquia': analisis_jerarquia_memoria(),
    }