# Mi Tienda – Sistema de Gestión de Abarrotes (T2)

Aplicación de escritorio en **Python + Tkinter + SQLite** para ventas, almacén y caja de una tienda de abarrotes.

Cumple los requisitos de la **Tarea 2** del curso de algoritmos: estructuras de datos, búsqueda/ordenamiento, complejidad, voraz, divide y vencerás, recursividad, programación dinámica, algoritmos probabilistas y paralelismo.

---

## 1. Herramientas utilizadas

| Herramienta | Uso |
|-------------|-----|
| **Python 3.11+** | Lenguaje principal |
| **Tkinter** | Interfaz gráfica de escritorio |
| **SQLite** | Persistencia local (transacciones ACID, índices B-tree) |
| **PyInstaller** | Generación del ejecutable `MiTienda.exe` |
| **Git** | Control de versiones (varios commits) |
| **unittest** | Pruebas unitarias de algoritmos |
| **IA (asistencia)** | Estructura inicial, revisión de errores y documentación; código verificado manualmente |

---

## 2. Arquitectura

```
main.py  (UI / eventos Tkinter)
   ↓
db.py    (lógica de negocio + acceso a datos)
   ↓
algorithms.py  (voraz, binaria, recursión, DP, Monte Carlo, hilos)
   ↓
SQLite   (tienda.db en ~/TiendaAbarrotesData/)
```

Separación de capas: la interfaz no conoce SQL; la base no conoce widgets.

---

## 3. Estructuras de datos (Semana 1)

- **Registros**: `sqlite3.Row` → acceso `r['name']`, `r['stock']`.
- **Listas de diccionarios**: carrito `self.cart = [{'product_id', 'name', 'quantity', 'price'}, ...]`.
- **Cadenas**: f-strings (`f"S/ {v:,.2f}"`), `.strip()`, `.upper()`, número de venta `V{YYYYMMDD}-{n:04d}`.

---

## 4. Algoritmos implementados y complejidad

| Algoritmo | Función | Complejidad | Ubicación |
|-----------|---------|-------------|-----------|
| Fuerza bruta / LIKE | `list_products` | O(n log n) por ORDER BY | `db.py` |
| Búsqueda por PK | `get_product` | O(log n) árbol B | `db.py` |
| Búsqueda lineal carrito | `add_selected_to_cart` | O(k) | `main.py` |
| **Voraz (cambio)** | `desglosar_vuelto` | O(1) ≈ 11 denominaciones | `algorithms.py` |
| **Merge sort** | `merge_sort_by_code` | O(n log n) | `algorithms.py` |
| **Búsqueda binaria** | `binary_search_by_code` | O(log n) | `algorithms.py` |
| **Recursión total** | `recursive_cart_total` | O(k) | `algorithms.py` |
| **Recursión grupos** | `recursive_group_by_category` | O(n) | `algorithms.py` |
| **DP mochila 0/1** | `optimal_restock` | O(n · W) | `algorithms.py` |
| **Monte Carlo** | `monte_carlo_demand_simulation` | O(s · n) | `algorithms.py` |
| **Hilo paralelo** | `generar_reporte_background` | O(n) en segundo plano | `algorithms.py` |
| Transacción venta | `create_sale` | O(k log n) | `db.py` |

---

## 5. Cómo ejecutar

### Desde código fuente
```bash
cd tienda_abarrotes
python main.py
```

### Ejecutable Windows
Doble clic en `build_windows.bat` → genera `dist\MiTienda.exe`.

### Pruebas unitarias
```bash
cd tienda_abarrotes
python -m unittest tests.test_algorithms -v
```

### Datos de demostración
Botón **Cargar datos demo** en el menú lateral.

---

## 6. Módulo “Algoritmos” en la UI

Desde el menú lateral → **🧠 Algoritmos**:

1. **Voraz**: desglose de cualquier monto en billetes/monedas.
2. **Programación dinámica**: reposición óptima con presupuesto.
3. **Monte Carlo**: probabilidad de quiebre de stock a 30 días.
4. **Recursividad**: agrupación de productos por categoría.

En **Ventas** también hay:
- Vista previa del desglose voraz del vuelto.
- Botón **Buscar por código (binaria)** O(log n).

---

## 7. Control de versiones

Repositorio Git inicializado con commits lógicos:

1. Estructura base (main + db + SQLite)
2. Algoritmos del curso (algorithms.py)
3. Integración UI + desglose de vuelto
4. Pruebas unitarias
5. README y documentación T2

---

## 8. Conclusiones

- El sistema resuelve la gestión manual de ventas, stock y caja con transacciones atómicas (si falla la luz a mitad de una venta, no queda estado inconsistente).
- Se aplicaron de forma concreta las estrategias del sílabo: voraz, divide y vencerás, recursión, programación dinámica y Monte Carlo.
- La complejidad de cada función clave está documentada en notación O grande.
- La arquitectura en capas facilita mantenimiento y pruebas.
- El producto es desplegable como `.exe` independiente.

## 9. Recomendaciones / trabajo futuro

- Paginación y búsqueda por prefijo (`LIKE 'x%'`) para escalar a miles de productos.
- Mantener total del carrito acumulado (O(1) en lugar de O(k) en cada refresh).
- Persistencia de la caché ordenada en disco.
- Más pruebas de integración y cobertura de UI.

---

## 10. Checklist de evidencias T2

- [x] Software funcional (ventas, stock, caja)
- [x] Persistencia SQLite + separación de capas
- [x] Programación dinámica (mochila)
- [x] Algoritmos probabilistas (Monte Carlo)
- [x] Algoritmos paralelos (hilo de reporte)
- [x] Estrategias Unidad I (voraz, recursión, divide y vencerás, ordenamiento propio)
- [x] Análisis de complejidad (comentarios O grande)
- [x] Control de versiones (Git)
- [x] Informe (este README + PDF técnico)
- [x] Pruebas unitarias (`tests/`)

---

## Complejidad espacial y algoritmos paralelos

- `complejidad_espacial.py`: mide la memoria estática O(1) y dinámica O(n + k) (carrito e inventario) y describe la jerarquía de memoria.
- `algoritmos_paralelos.py`: speed-up, eficiencia, overhead, granularidad e isoeficiencia; el benchmark compara el reporte del panel en secuencial vs 2 hilos.
- Ambos se ejecutan desde la pestaña **Algoritmos** (secciones 5 y 6).
- Pruebas: `python -m unittest tests.test_complejidad_paralelo`
