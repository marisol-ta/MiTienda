"""
Módulo de algoritmos del curso (Unidades I–II).
Contiene implementaciones propias de:
  - Algoritmo voraz (cambio de moneda)
  - Búsqueda binaria / divide y vencerás
  - Recursividad
  - Programación dinámica (mochila 0/1)
  - Algoritmo probabilista (Monte Carlo)
  - Utilidad paralela (hilo para reporte)

Cada función documenta su complejidad temporal en notación O grande.
"""

from __future__ import annotations
import random
from typing import List, Dict, Tuple, Optional, Any
import threading
import time


# ---------------------------------------------------------------------------
# 1. ALGORITMO VORAZ – Desglose de vuelto (semana 3)
# Complejidad: O(d) donde d = número de denominaciones (constante ≈ 10)
# ---------------------------------------------------------------------------
DENOMINACIONES = [
    200.0, 100.0, 50.0, 20.0, 10.0, 5.0, 2.0, 1.0, 0.50, 0.20, 0.10
]


def desglosar_vuelto(monto: float) -> List[Tuple[float, int]]:
    """
    Algoritmo voraz de cambio de moneda.
    Toma siempre la mayor denominación posible sin excedarse.
    Complejidad: O(d)  — d es constante (11 denominaciones).
    """
    if monto < 0:
        raise ValueError("El monto no puede ser negativo")
    resultado = []
    restante = round(float(monto), 2)
    for denom in DENOMINACIONES:
        if restante >= denom - 1e-9:
            cantidad = int(restante // denom)
            if cantidad > 0:
                resultado.append((denom, cantidad))
                restante = round(restante - cantidad * denom, 2)
    return resultado


def formatear_desglose(desglose: List[Tuple[float, int]]) -> str:
    """Convierte el desglose a texto legible."""
    if not desglose:
        return "Sin vuelto"
    partes = []
    for denom, cant in desglose:
        if denom >= 1:
            partes.append(f"{cant} × S/ {denom:.0f}")
        else:
            partes.append(f"{cant} × S/ {denom:.2f}")
    return " + ".join(partes)


# ---------------------------------------------------------------------------
# 2. BÚSQUEDA BINARIA / DIVIDE Y VENCERÁS (semana 3–4)
# Complejidad: O(log n)
# ---------------------------------------------------------------------------
def binary_search_by_code(productos: List[Any], codigo: str) -> Optional[Any]:
    """
    Búsqueda binaria sobre una lista de productos ya ordenada por código.
    Divide y vencerás: en cada paso se descarta la mitad del espacio.
    Complejidad: O(log n)
    Precondición: productos debe estar ordenada por code (ascendente).
    """
    codigo = codigo.strip().upper()
    izq, der = 0, len(productos) - 1
    while izq <= der:
        mid = (izq + der) // 2
        mid_code = str(productos[mid]["code"] if hasattr(productos[mid], "keys") else productos[mid].code).upper()
        if mid_code == codigo:
            return productos[mid]
        if mid_code < codigo:
            izq = mid + 1
        else:
            der = mid - 1
    return None


def merge_sort_by_code(productos: List[Any]) -> List[Any]:
    """
    Ordenamiento por mezcla (divide y vencerás).
    Complejidad: O(n log n) tiempo, O(n) espacio auxiliar.
    """
    if len(productos) <= 1:
        return list(productos)

    mid = len(productos) // 2
    izquierda = merge_sort_by_code(productos[:mid])
    derecha = merge_sort_by_code(productos[mid:])

    # Mezcla
    resultado = []
    i = j = 0
    while i < len(izquierda) and j < len(derecha):
        c_i = str(izquierda[i]["code"] if hasattr(izquierda[i], "keys") else izquierda[i].code).upper()
        c_j = str(derecha[j]["code"] if hasattr(derecha[j], "keys") else derecha[j].code).upper()
        if c_i <= c_j:
            resultado.append(izquierda[i])
            i += 1
        else:
            resultado.append(derecha[j])
            j += 1
    resultado.extend(izquierda[i:])
    resultado.extend(derecha[j:])
    return resultado


# ---------------------------------------------------------------------------
# 3. RECURSIVIDAD (semana 3)
# Complejidad: O(k) donde k = número de ítems
# ---------------------------------------------------------------------------
def recursive_cart_total(items: List[Dict], index: int = 0) -> float:
    """
    Calcula el total del carrito de forma recursiva.
    Caso base: lista vacía o índice fuera de rango → 0
    Caso recursivo: precio*cantidad del ítem actual + total del resto
    Complejidad: O(k)
    """
    if index >= len(items):
        return 0.0
    item = items[index]
    linea = float(item["quantity"]) * float(item["price"])
    return round(linea + recursive_cart_total(items, index + 1), 2)


def recursive_group_by_category(productos: List[Any], index: int = 0, grupos: Optional[Dict] = None) -> Dict[str, list]:
    """
    Agrupa productos por categoría de forma recursiva.
    Complejidad: O(n)
    """
    if grupos is None:
        grupos = {}
    if index >= len(productos):
        return grupos
    p = productos[index]
    cat = p["category"] if hasattr(p, "keys") else p.category
    cat = cat or "Sin categoría"
    if cat not in grupos:
        grupos[cat] = []
    grupos[cat].append(p)
    return recursive_group_by_category(productos, index + 1, grupos)


# ---------------------------------------------------------------------------
# 4. PROGRAMACIÓN DINÁMICA – Problema de la mochila 0/1 (semana 5)
# Complejidad: O(n * W) donde n = productos candidatos, W = presupuesto (discretizado)
# ---------------------------------------------------------------------------
def optimal_restock(
    productos: List[Dict],
    presupuesto: float,
    paso: float = 1.0
) -> Dict[str, Any]:
    """
    Problema de la mochila 0/1:
    Dado un presupuesto, elegir un subconjunto de productos a reponer
    (1 unidad de cada uno) que maximice la ganancia potencial
    (sale_price - purchase_price).

    Se discretiza el presupuesto en pasos de `paso` soles.
    Complejidad: O(n * W)  — W = presupuesto / paso
    """
    candidatos = []
    for p in productos:
        stock = float(p.get("stock", 0))
        min_stock = float(p.get("min_stock", 0))
        purchase = float(p.get("purchase_price", 0))
        sale = float(p.get("sale_price", 0))
        # Solo candidatos con stock bajo o nulo y ganancia positiva
        if stock <= min_stock and purchase > 0 and sale > purchase:
            ganancia = sale - purchase
            candidatos.append({
                "id": p.get("id"),
                "code": p.get("code"),
                "name": p.get("name"),
                "cost": purchase,
                "profit": ganancia,
            })

    if not candidatos or presupuesto <= 0:
        return {"selected": [], "total_cost": 0.0, "total_profit": 0.0, "message": "Sin candidatos o presupuesto nulo"}

    # Discretización
    W = int(presupuesto / paso)
    n = len(candidatos)
    # dp[i][w] = máxima ganancia usando los primeros i ítems con capacidad w
    dp = [[0.0] * (W + 1) for _ in range(n + 1)]
    keep = [[False] * (W + 1) for _ in range(n + 1)]

    for i in range(1, n + 1):
        cost_units = int(candidatos[i - 1]["cost"] / paso)
        profit = candidatos[i - 1]["profit"]
        for w in range(W + 1):
            # No tomar el ítem
            dp[i][w] = dp[i - 1][w]
            # Tomar el ítem si cabe
            if cost_units <= w:
                valor = dp[i - 1][w - cost_units] + profit
                if valor > dp[i][w]:
                    dp[i][w] = valor
                    keep[i][w] = True

    # Reconstrucción
    selected = []
    w = W
    total_cost = 0.0
    for i in range(n, 0, -1):
        if keep[i][w]:
            item = candidatos[i - 1]
            selected.append(item)
            total_cost += item["cost"]
            w -= int(item["cost"] / paso)

    selected.reverse()
    return {
        "selected": selected,
        "total_cost": round(total_cost, 2),
        "total_profit": round(dp[n][W], 2),
        "message": f"Se seleccionaron {len(selected)} producto(s) con ganancia potencial S/ {dp[n][W]:.2f}"
    }


# ---------------------------------------------------------------------------
# 5. ALGORITMO PROBABILISTA – Monte Carlo (semana 6)
# Complejidad: O(s * n)  s = número de simulaciones, n = productos
# ---------------------------------------------------------------------------
def monte_carlo_demand_simulation(
    productos: List[Dict],
    dias: int = 30,
    simulaciones: int = 500
) -> Dict[str, Any]:
    """
    Simulación Monte Carlo de demanda futura.
    Para cada producto genera demanda diaria ~ Uniforme(0, stock_actual*0.15)
    y estima la probabilidad de quiebre de stock en `dias` días.
    Complejidad: O(s * n * d) ≈ O(s * n) con d constante.
    """
    resultados = []
    for p in productos:
        stock = float(p.get("stock", 0))
        if stock <= 0:
            resultados.append({
                "code": p.get("code"),
                "name": p.get("name"),
                "stock": stock,
                "prob_quiebre": 1.0,
                "demanda_media": 0.0,
            })
            continue

        max_diario = max(1.0, stock * 0.15)
        quiebres = 0
        demandas = []
        for _ in range(simulaciones):
            s = stock
            demanda_total = 0.0
            for _ in range(dias):
                d = random.uniform(0, max_diario)
                demanda_total += d
                s -= d
                if s < 0:
                    quiebres += 1
                    break
            demandas.append(demanda_total)

        prob = quiebres / simulaciones
        resultados.append({
            "code": p.get("code"),
            "name": p.get("name"),
            "stock": stock,
            "prob_quiebre": round(prob, 3),
            "demanda_media": round(sum(demandas) / len(demandas), 2),
        })

    # Ordenar por mayor probabilidad de quiebre
    resultados.sort(key=lambda x: x["prob_quiebre"], reverse=True)
    return {
        "dias": dias,
        "simulaciones": simulaciones,
        "productos": resultados[:15],  # top 15 más críticos
        "message": f"Simulación Monte Carlo ({simulaciones} iteraciones, {dias} días)"
    }


# ---------------------------------------------------------------------------
# 6. ALGORITMO PARALELO – Hilo para generar reporte en segundo plano
# ---------------------------------------------------------------------------
def generar_reporte_background(callback, datos: Dict, delay: float = 0.8):
    """
    Ejecuta la generación de un resumen en un hilo separado
    para no bloquear la interfaz (demostración de paralelismo).
    Complejidad del trabajo: O(n)
    """
    def trabajador():
        time.sleep(delay)  # simula trabajo de I/O o cálculo
        resumen = {
            "productos": datos.get("products", 0),
            "ventas_hoy": datos.get("sales_count", 0),
            "total_ventas": datos.get("sales_total", 0),
            "stock_bajo": datos.get("low", 0),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        callback(resumen)

    hilo = threading.Thread(target=trabajador, daemon=True)
    hilo.start()
    return hilo
