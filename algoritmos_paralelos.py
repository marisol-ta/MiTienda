"""
Módulo de análisis de algoritmos paralelos.
Basado en el documento 'Análisis de algoritmos paralelos'.

Implementa las métricas del documento:
  - Tiempo secuencial t(n)
  - Tiempo paralelo t(n, p)
  - Speed-up S(n, p) = t(n) / t(n, p)
  - Eficiencia E(n, p) = S(n, p) / p
  - Overhead t₀(n, p) = p·t(n, p) - t(n)
  - Isoeficiencia: cómo debe crecer n con p para mantener E constante
  - Granularidad (fina/gruesa)
"""

import time
import threading
from typing import Dict, Any, Callable, List
from dataclasses import dataclass, field


@dataclass
class MetricasParalelas:
    """Almacena las métricas de una ejecución paralela."""
    tiempo_secuencial: float = 0.0
    tiempo_paralelo: float = 0.0
    procesadores: int = 1
    speedup: float = 0.0
    eficiencia: float = 0.0
    overhead: float = 0.0
    solapamiento: float = 0.0
    granularidad: str = 'gruesa'
    notas: List[str] = field(default_factory=list)


def medir_tiempo_secuencial(funcion: Callable, *args, **kwargs) -> float:
    """
    Mide el tiempo de ejecución secuencial de una función.
    t(n) = tiempo desde que empieza hasta que acaba.
    """
    inicio = time.perf_counter()
    funcion(*args, **kwargs)
    fin = time.perf_counter()
    return fin - inicio


def medir_tiempo_paralelo(funciones: List[Callable]) -> float:
    """
    Mide el tiempo de ejecución paralela de varias tareas independientes,
    cada una en su propio hilo (p = len(funciones)).
    El tiempo es desde que empieza el primer hilo hasta que acaba el último.

    t(n, p) = t_a(n, p) + t_c(n, p) + t_o(n, p) - t_s(n, p)
      donde t_a = computación, t_c = comunicación, t_o = overhead, t_s = solapamiento.
    """
    hilos = [threading.Thread(target=f, daemon=True) for f in funciones]
    inicio = time.perf_counter()
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    fin = time.perf_counter()
    return fin - inicio


def calcular_speedup(t_secuencial: float, t_paralelo: float) -> float:
    """
    Speed-up S(n, p) = t(n) / t(n, p)

    Mide la ganancia de velocidad del programa paralelo.
    - S < p: hay overhead
    - S = p: speed-up lineal ideal
    - S > p: speed-up superlineal (raro, por mejor gestión de memoria)

    El speed-up será menor que el número de procesadores en la práctica.
    """
    if t_paralelo <= 0:
        return 0.0
    return t_secuencial / t_paralelo


def calcular_eficiencia(speedup: float, procesadores: int) -> float:
    """
    Eficiencia E(n, p) = S(n, p) / p

    Da idea de la porción de tiempo que los procesadores dedican a trabajo útil.
    Valor entre 0 y 1.
    - Para tamaño de problema fijo, se aleja de 1 al aumentar p.
    - Para p fijo, aumenta con el tamaño del problema.
    """
    if procesadores <= 0:
        return 0.0
    return speedup / procesadores


def calcular_overhead(t_secuencial: float, t_paralelo: float, procesadores: int) -> float:
    """
    Overhead t₀(n, p) = p·t(n, p) - t(n)

    Representa el trabajo adicional realizado por todo el sistema.
    Incluye:
      - Sincronización
      - Puesta en marcha de procesos
      - Sobrecarga de red de comunicación
      - Código secuencial no paralelizable
      - Desbalanceo de carga
    """
    return procesadores * t_paralelo - t_secuencial


def calcular_solapamiento(t_computacion: float, t_comunicacion: float,
                          t_real: float) -> float:
    """
    Solapamiento t_s(n, p) = t_a(n, p) + t_c(n, p) - t_real(n, p)

    Reduce el tiempo real al superponer computación y comunicación.
    """
    return max(0.0, t_computacion + t_comunicacion - t_real)


def analizar_granularidad(num_tareas: int, num_procesadores: int,
                          datos_por_tarea: int) -> Dict[str, Any]:
    """
    Analiza la granularidad del sistema (físico + algoritmo).

    - Grano fino: pocos datos o poca computación entre comunicaciones.
    - Grano grueso: muchos datos o mucha computación entre comunicaciones.

    Interesa programación paralela cuando el paralelismo es de grano grueso.
    """
    ratio_tareas_proc = num_tareas / max(1, num_procesadores)
    ratio_datos_tarea = datos_por_tarea

    if ratio_tareas_proc > 10 or ratio_datos_tarea < 10:
        granularidad = 'fina'
        recomendacion = 'Aumentar el grano: agrupar tareas para balancear carga y reducir comunicaciones.'
    elif ratio_tareas_proc > 2:
        granularidad = 'media'
        recomendacion = 'Granularidad aceptable. Considerar agrupación si hay mucho overhead.'
    else:
        granularidad = 'gruesa'
        recomendacion = 'Granularidad óptima para memoria compartida o paso de mensajes.'

    return {
        'num_tareas': num_tareas,
        'num_procesadores': num_procesadores,
        'datos_por_tarea': datos_por_tarea,
        'ratio_tareas_procesador': round(ratio_tareas_proc, 2),
        'granularidad': granularidad,
        'recomendacion': recomendacion,
        'nota': (
            'En la fase de Agrupación (metodología Foster) se aumenta el grano. '
            'Más granularidad en el orden: paso de mensajes > memoria compartida > GPU.'
        ),
    }


def calcular_isoeficiencia(tipo_conexion: str = 'memoria_compartida') -> Dict[str, Any]:
    """
    Función de Isoeficiencia: cómo debe crecer n en función de p
    para mantener la eficiencia constante.

    Del documento:
      - Memoria compartida/hipercubo: n ∝ p log p
      - Malla con comunicaciones directas: n ∝ p^(3/2)
      - Anillo sin comunicaciones directas: n ∝ p²

    La que tenga menor orden escala mejor.
    """
    funciones = {
        'memoria_compartida': {
            'formula': 'n ∝ p log p',
            'orden': 'p log p',
            'escalabilidad': 'Buena',
        },
        'hipercubo': {
            'formula': 'n ∝ p log p',
            'orden': 'p log p',
            'escalabilidad': 'Buena',
        },
        'malla': {
            'formula': 'n ∝ p^(3/2)',
            'orden': 'p^1.5',
            'escalabilidad': 'Media',
        },
        'anillo': {
            'formula': 'n ∝ p²',
            'orden': 'p²',
            'escalabilidad': 'Baja (peor)',
        },
    }
    return funciones.get(tipo_conexion, funciones['memoria_compartida'])


def metodologia_foster() -> Dict[str, str]:
    """
    Pasos de la metodología de diseño de algoritmos paralelos (Foster):
      1. Particionado: descomponer en muchas tareas pequeñas.
      2. Comunicación: determinar patrones de comunicación y sincronización.
      3. Agrupación: agrupar tareas para balancear trabajo y reducir comunicaciones.
      4. Mapeo: asignación de tareas al sistema computacional.
    """
    return {
        'particionado': 'Descomponer el reporte en sub-tareas: conteo de productos, suma de ventas, detección de stock bajo.',
        'comunicacion': 'Las sub-tareas comparten el diccionario de datos; se comunican vía callback al hilo principal.',
        'agrupacion': 'Agrupar las sub-tareas en 2 hilos (dashboard y caja) para reducir overhead de creación.',
        'mapeo': 'Asignar el hilo trabajador a un núcleo del CPU; el hilo principal mantiene la UI responsiva.',
    }


def ejecutar_benchmark_paralelo(db, callback_resultado) -> MetricasParalelas:
    """
    Ejecuta un benchmark comparando la versión secuencial vs paralela
    del reporte de dashboard.

    Demuestra:
      - Speed-up
      - Eficiencia
      - Overhead
      - Granularidad
    """
    metricas = MetricasParalelas()

    # 1. Versión secuencial
    def trabajo_secuencial():
        data = db.dashboard()
        cash = db.cash_summary_today()
        return data, cash

    t_sec = medir_tiempo_secuencial(trabajo_secuencial)
    metricas.tiempo_secuencial = t_sec

    # 2. Versión paralela: cada consulta en su propio hilo (conexión SQLite propia)
    t_par = medir_tiempo_paralelo([db.dashboard, db.cash_summary_today])
    metricas.tiempo_paralelo = t_par
    metricas.procesadores = 2  # un hilo por consulta

    # 3. Métricas
    metricas.speedup = calcular_speedup(t_sec, t_par)
    metricas.eficiencia = calcular_eficiencia(metricas.speedup, metricas.procesadores)
    metricas.overhead = calcular_overhead(t_sec, t_par, metricas.procesadores)

    # 4. Granularidad
    data = db.dashboard()
    num_tareas = 3  # productos, ventas, stock bajo
    gran = analizar_granularidad(num_tareas, metricas.procesadores, data.get('products', 0))
    metricas.granularidad = gran['granularidad']

    # 5. Notas
    metricas.notas = [
        f"Speed-up S(n,p) = t(n)/t(n,p) = {t_sec:.6f}/{t_par:.6f} = {metricas.speedup:.3f}",
        f"Eficiencia E(n,p) = S/p = {metricas.speedup:.3f}/{metricas.procesadores} = {metricas.eficiencia:.3f}",
        f"Overhead t₀(n,p) = p·t(n,p) - t(n) = {metricas.overhead:.6f} s",
        f"Granularidad: {gran['granularidad']} — {gran['recomendacion']}",
        "El speed-up será menor que p en la práctica por overhead de sincronización.",
        "Para tamaño de problema fijo, la eficiencia se aleja de 1 al aumentar p.",
    ]

    if callback_resultado:
        callback_resultado(metricas)

    return metricas


def comparar_isoeficiencia() -> Dict[str, Any]:
    """Compara las funciones de isoeficiencia de distintas topologías."""
    topologias = ['memoria_compartida', 'hipercubo', 'malla', 'anillo']
    resultado = {}
    for t in topologias:
        resultado[t] = calcular_isoeficiencia(t)

    # Ejemplo numérico del documento: mantener prestaciones de p1 a p2
    ejemplo = {
        'p1': 4, 'p2': 16,
        'factor_aumento': 4,
        'crecimiento_n': {
            'p log p': f"{16 * 4} / {4 * 2} = {16*4/(4*2):.1f}x",
            'p^(3/2)': f"{16**1.5:.1f} / {4**1.5:.1f} = {16**1.5/4**1.5:.1f}x",
            'p²': f"{16**2} / {4**2} = {16**2/4**2:.1f}x",
        },
        'conclusion': 'Todos escalables, pero los de menor orden (p log p) escalan mejor.',
    }
    return {'topologias': resultado, 'ejemplo_numerico': ejemplo}