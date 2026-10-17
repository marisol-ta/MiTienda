"""
Interfaz gráfica (capa de presentación) – Tkinter.
main.py → db.py → SQLite

Incluye accesos a:
  - Desglose voraz de vuelto
  - Búsqueda binaria por código
  - Reposición óptima (programación dinámica)
  - Simulación Monte Carlo de demanda
  - Reporte en hilo paralelo
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from datetime import datetime
from db import Database
from algorithms import formatear_desglose, generar_reporte_background, backtracking_cambio
import complejidad_espacial
import algoritmos_paralelos

APP_TITLE = "Mi Tienda - Ventas, Almacén y Caja (T2)"


class StoreApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.title(APP_TITLE)
        self.geometry("1220x760")
        self.minsize(1050, 650)
        self.configure(bg="#eef2f7")
        self.cart = []          # lista de diccionarios (estructura de datos semana 1)
        self.purchase_cart = []  # ítems de la compra en curso (módulo Compras)
        self.selected_product_id = None
        self._style()
        self._layout()
        self.show_dashboard()

    def _style(self):
        st = ttk.Style(self)
        try:
            st.theme_use('clam')
        except Exception:
            pass
        st.configure('TFrame', background='#eef2f7')
        st.configure('Card.TFrame', background='white')
        st.configure('Title.TLabel', background='#eef2f7', foreground='#172033',
                     font=('Segoe UI', 21, 'bold'))
        st.configure('Sub.TLabel', background='#eef2f7', foreground='#607089',
                     font=('Segoe UI', 10))
        st.configure('CardTitle.TLabel', background='white', foreground='#607089',
                     font=('Segoe UI', 10))
        st.configure('CardValue.TLabel', background='white', foreground='#152238',
                     font=('Segoe UI', 20, 'bold'))
        st.configure('TLabel', font=('Segoe UI', 10))
        st.configure('Card.TCheckbutton', background='white')
        st.configure('Card.TRadiobutton', background='white')
        st.configure('TButton', font=('Segoe UI', 10), padding=(11, 8))
        st.configure('Primary.TButton', font=('Segoe UI', 10, 'bold'), padding=(12, 9))
        st.map('Primary.TButton', background=[('active', '#1769aa')])
        st.configure('Treeview', rowheight=30, font=('Segoe UI', 9))
        st.configure('Treeview.Heading', font=('Segoe UI', 9, 'bold'))

    def _layout(self):
        sidebar = tk.Frame(self, bg='#172033', width=210)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)
        tk.Label(sidebar, text='🛒  MI TIENDA', bg='#172033', fg='white',
                 font=('Segoe UI', 16, 'bold')).pack(padx=18, pady=(24, 28), anchor='w')
        for text, cmd in [
            ('📊  Inicio', self.show_dashboard),
            ('🧾  Ventas', self.show_sales),
            ('📦  Almacén', self.show_warehouse),
            ('🚚  Compras', self.show_purchases),
            ('↩️  Devoluciones', self.show_returns),
            ('💵  Caja', self.show_cash),
            ('🧠  Algoritmos', self.show_algorithms),
        ]:
            b = tk.Button(
                sidebar, text=text, command=cmd, bg='#172033', fg='#dbe6f5',
                activebackground='#243653', activeforeground='white', bd=0,
                anchor='w', font=('Segoe UI', 11), padx=20, pady=10, cursor='hand2'
            )
            b.pack(fill='x')
        # Pie fijo: se empaqueta primero para que nunca quede tapado
        tk.Label(
            sidebar, text='Base local SQLite\nDatos guardados en tu PC',
            bg='#172033', fg='#8090a8', font=('Segoe UI', 8), justify='left'
        ).pack(side='bottom', anchor='w', padx=18, pady=(8, 14))
        tk.Frame(sidebar, bg='#2b3b55', height=1).pack(fill='x', padx=18, pady=12)
        for txt, cmd in [('Cargar datos demo', self.seed_demo),
                         ('Cargar 15 productos', self.seed_catalog)]:
            tk.Button(
                sidebar, text=txt, command=cmd,
                bg='#243653', fg='white', activebackground='#314664',
                activeforeground='white', bd=0, font=('Segoe UI', 9), padx=12, pady=7
            ).pack(fill='x', padx=16, pady=(0, 6))
        self.content = ttk.Frame(self, padding=24)
        self.content.pack(side='left', fill='both', expand=True)

    def clear(self):
        for w in self.content.winfo_children():
            w.destroy()

    def header(self, title, subtitle):
        ttk.Label(self.content, text=title, style='Title.TLabel').pack(anchor='w')
        ttk.Label(self.content, text=subtitle, style='Sub.TLabel').pack(
            anchor='w', pady=(2, 18)
        )

    def money(self, v):
        return f"S/ {float(v):,.2f}"

    # ------------------------------------------------------------------
    # AYUDAS DE DISEÑO (para que los botones siempre queden visibles)
    # ------------------------------------------------------------------
    def _two_panes(self, left_min=420, right_min=340, lw=3, rw=2):
        """Dos paneles lado a lado con ancho mínimo garantizado."""
        wrap = ttk.Frame(self.content)
        wrap.pack(fill='both', expand=True)
        wrap.rowconfigure(0, weight=1)
        wrap.columnconfigure(0, weight=lw, minsize=left_min)
        wrap.columnconfigure(1, weight=rw, minsize=right_min)
        left = ttk.Frame(wrap, style='Card.TFrame', padding=14)
        right = ttk.Frame(wrap, style='Card.TFrame', padding=14)
        left.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
        right.grid(row=0, column=1, sticky='nsew', padx=(8, 0))
        return left, right

    def _fit_dialog(self, w, min_w=0, min_h=0):
        """
        Ajusta una ventana secundaria a su contenido: nunca más chica que lo
        que necesitan sus botones/campos, centrada y limitada a la pantalla.
        """
        w.update_idletasks()
        sw, sh = w.winfo_screenwidth(), w.winfo_screenheight()
        width = min(max(w.winfo_reqwidth(), min_w), sw - 60)
        height = min(max(w.winfo_reqheight(), min_h), sh - 100)
        w.minsize(min(w.winfo_reqwidth(), width), min(w.winfo_reqheight(), height))
        x = self.winfo_rootx() + max(0, (self.winfo_width() - width) // 2)
        y = self.winfo_rooty() + max(0, (self.winfo_height() - height) // 3)
        x = max(0, min(x, sw - width - 10))
        y = max(0, min(y, sh - height - 60))
        w.geometry(f'{width}x{height}+{x}+{y}')

    # ------------------------------------------------------------------
    # DASHBOARD
    # ------------------------------------------------------------------
    def show_dashboard(self):
        self.clear()
        self.header('Panel principal', f"Resumen del día · {datetime.now().strftime('%d/%m/%Y')}")
        data = self.db.dashboard()
        cash = self.db.cash_summary_today()
        cards = ttk.Frame(self.content)
        cards.pack(fill='x')
        vals = [
            ('Ventas de hoy', self.money(data['sales_total'])),
            ('N.º de ventas', str(data['sales_count'])),
            ('Productos', str(data['products'])),
            ('Stock bajo', str(data['low'])),
            ('Saldo caja', self.money(cash['balance'])),
        ]
        for i, (t, v) in enumerate(vals):
            c = ttk.Frame(cards, style='Card.TFrame', padding=16)
            c.grid(row=0, column=i, padx=(0, 10), sticky='nsew')
            cards.columnconfigure(i, weight=1)
            ttk.Label(c, text=t, style='CardTitle.TLabel').pack(anchor='w')
            ttk.Label(c, text=v, style='CardValue.TLabel').pack(anchor='w', pady=(6, 0))

        body = ttk.Frame(self.content, style='Card.TFrame', padding=20)
        body.pack(fill='both', expand=True, pady=(20, 0))
        ttk.Label(body, text='Accesos rápidos', background='white',
                  font=('Segoe UI', 14, 'bold')).pack(anchor='w', pady=(0, 14))
        row = ttk.Frame(body, style='Card.TFrame')
        row.pack(anchor='w')
        ttk.Button(row, text='Nueva venta', style='Primary.TButton',
                   command=self.show_sales).pack(side='left', padx=(0, 10))
        ttk.Button(row, text='Registrar producto',
                   command=self.show_warehouse).pack(side='left', padx=(0, 10))
        ttk.Button(row, text='Movimiento de caja',
                   command=self.show_cash).pack(side='left', padx=(0, 10))
        ttk.Button(row, text='Algoritmos del curso',
                   command=self.show_algorithms).pack(side='left')
        ttk.Separator(body).pack(fill='x', pady=24)
        ttk.Label(body, text='Inventario', background='white',
                  font=('Segoe UI', 13, 'bold')).pack(anchor='w')
        ttk.Label(
            body,
            text=f"Valor estimado del inventario a costo: {self.money(data['stock_value'])}",
            background='white'
        ).pack(anchor='w', pady=(6, 0))
        if data['low']:
            ttk.Label(
                body,
                text=f"⚠ Hay {data['low']} producto(s) con stock mínimo o menor.",
                background='white', foreground='#b45309', font=('Segoe UI', 10, 'bold')
            ).pack(anchor='w', pady=(10, 0))

        # Demostración de paralelismo: reporte en hilo
        self.report_label = ttk.Label(
            body, text='Generando reporte en segundo plano…',
            background='white', foreground='#607089'
        )
        self.report_label.pack(anchor='w', pady=(16, 0))

        def on_report(resumen):
            self.report_label.config(
                text=f"Reporte paralelo · {resumen['timestamp']} · "
                     f"{resumen['productos']} productos · "
                     f"{resumen['ventas_hoy']} ventas · "
                     f"Stock bajo: {resumen['stock_bajo']}"
            )

        generar_reporte_background(on_report, data)

    # ------------------------------------------------------------------
    # SALES
    # ------------------------------------------------------------------
    def show_sales(self):
        self.clear()
        self.header('Ventas', 'Busca productos, agrégalos al carrito y registra el cobro.')
        left, right = self._two_panes(400, 340)

        searchrow = ttk.Frame(left, style='Card.TFrame')
        searchrow.pack(fill='x')
        ttk.Label(searchrow, text='Buscar:', background='white').pack(side='left')
        self.sale_search = tk.StringVar()
        e = ttk.Entry(searchrow, textvariable=self.sale_search)
        e.pack(side='left', fill='x', expand=True, padx=8)
        e.bind('<KeyRelease>', lambda _: self.refresh_sale_products())
        ttk.Button(searchrow, text='Actualizar',
                   command=self.refresh_sale_products).pack(side='left')
        ttk.Button(left, text='Buscar por código (binaria)',
                   command=self.binary_search_dialog).pack(anchor='w', pady=(8, 0))

        # --- Zona inferior fija del panel izquierdo (siempre visible) ---
        # Se empaqueta ANTES de la tabla para que, al achicar o agrandar la
        # ventana, sea la tabla la que ceda espacio y no estos botones.
        left_bottom = ttk.Frame(left, style='Card.TFrame')
        left_bottom.pack(side='bottom', fill='x')

        addrow = ttk.Frame(left_bottom, style='Card.TFrame')
        addrow.pack(fill='x')
        ttk.Label(addrow, text='Cantidad:', background='white').pack(side='left')
        self.sale_qty = tk.DoubleVar(value=1)
        ttk.Entry(addrow, textvariable=self.sale_qty, width=8).pack(side='left', padx=8)
        ttk.Button(addrow, text='Agregar al carrito', style='Primary.TButton',
                   command=self.add_selected_to_cart).pack(side='left')

        ttk.Button(left_bottom, text='Historial / Anular venta',
                   style='Primary.TButton',
                   command=self.sales_history_dialog).pack(fill='x', pady=(8, 0))

        cols = ('codigo', 'producto', 'stock', 'precio')
        self.sale_tree = ttk.Treeview(left, columns=cols, show='headings', height=8)
        for c, t, w in [
            ('codigo', 'Código', 90), ('producto', 'Producto', 260),
            ('stock', 'Stock', 75), ('precio', 'Precio', 90)
        ]:
            self.sale_tree.heading(c, text=t)
            self.sale_tree.column(c, width=w, anchor='center' if c != 'producto' else 'w')
        self.sale_tree.pack(fill='both', expand=True, pady=12)
        self.sale_tree.bind('<Double-1>', lambda _: self.add_selected_to_cart())

        ttk.Label(right, text='Carrito', background='white',
                  font=('Segoe UI', 14, 'bold')).pack(anchor='w')

        # --- Zona inferior fija (siempre visible) ---
        bottom = ttk.Frame(right, style='Card.TFrame')
        bottom.pack(side='bottom', fill='x')

        ttk.Button(bottom, text='Quitar seleccionado',
                   command=self.remove_cart).pack(anchor='e')
        ttk.Button(
            bottom, text='REGISTRAR VENTA', style='Primary.TButton',
            command=self.complete_sale
        ).pack(fill='x', pady=(8, 0))

        pay = ttk.Frame(bottom, style='Card.TFrame')
        pay.pack(fill='x', pady=(8, 0))
        pay.columnconfigure(1, weight=1)
        ttk.Label(pay, text='Pago:', background='white').grid(row=0, column=0, sticky='w', pady=3)
        self.pay_method = tk.StringVar(value='EFECTIVO')
        cb = ttk.Combobox(
            pay, textvariable=self.pay_method,
            values=['EFECTIVO', 'YAPE/PLIN', 'TARJETA', 'TRANSFERENCIA'],
            state='readonly'
        )
        cb.grid(row=0, column=1, sticky='ew', padx=(8, 0))
        cb.bind('<<ComboboxSelected>>', lambda _: self.payment_changed())
        ttk.Label(pay, text='Recibido:', background='white').grid(
            row=1, column=0, sticky='w', pady=3
        )
        self.received = tk.StringVar()
        ttk.Entry(pay, textvariable=self.received).grid(
            row=1, column=1, sticky='ew', padx=(8, 0)
        )
        self.received.trace_add('write', lambda *_: self.update_change())
        self.change_label = ttk.Label(
            pay, text='Vuelto: S/ 0.00', background='white',
            font=('Segoe UI', 11, 'bold')
        )
        self.change_label.grid(row=2, column=0, columnspan=2, sticky='e', pady=3)
        self.breakdown_label = ttk.Label(
            pay, text='', background='white', foreground='#276749',
            font=('Segoe UI', 8)
        )
        self.breakdown_label.grid(row=3, column=0, columnspan=2, sticky='e')

        self.total_label = ttk.Label(
            bottom, text='TOTAL: S/ 0.00', background='white',
            font=('Segoe UI', 18, 'bold')
        )
        self.total_label.pack(anchor='e', pady=(4, 0))
        ttk.Separator(bottom).pack(fill='x', pady=6)

        # --- Zona superior: lista del carrito ---
        cols = ('producto', 'cant', 'precio', 'total')
        self.cart_tree = ttk.Treeview(right, columns=cols, show='headings', height=8)
        for c, t, w in [
            ('producto', 'Producto', 190), ('cant', 'Cant.', 65),
            ('precio', 'P.Unit.', 75), ('total', 'Total', 80)
        ]:
            self.cart_tree.heading(c, text=t)
            self.cart_tree.column(c, width=w, anchor='center' if c != 'producto' else 'w')
        self.cart_tree.pack(fill='both', expand=True, pady=(6, 4))

        self.refresh_sale_products()
        self.refresh_cart()

    def refresh_sale_products(self):
        if not hasattr(self, 'sale_tree'):
            return
        for x in self.sale_tree.get_children():
            self.sale_tree.delete(x)
        for r in self.db.list_products(
            self.sale_search.get() if hasattr(self, 'sale_search') else ''
        ):
            self.sale_tree.insert(
                '', 'end', iid=str(r['id']),
                values=(r['code'], r['name'], f"{r['stock']:g}", self.money(r['sale_price']))
            )

    def binary_search_dialog(self):
        """Demuestra búsqueda binaria O(log n) por código."""
        codigo = simpledialog.askstring(
            'Búsqueda binaria', 'Ingresa el código del producto:', parent=self
        )
        if not codigo:
            return
        resultado = self.db.get_product_by_code_binary(codigo)
        if resultado:
            messagebox.showinfo(
                'Encontrado (O(log n))',
                f"Código: {resultado['code']}\n"
                f"Nombre: {resultado['name']}\n"
                f"Stock: {resultado['stock']}\n"
                f"Precio: {self.money(resultado['sale_price'])}"
            )
            # Seleccionar en el árbol si está visible
            try:
                self.sale_tree.selection_set(str(resultado['id']))
                self.sale_tree.see(str(resultado['id']))
            except Exception:
                pass
        else:
            messagebox.showwarning('No encontrado', f'No existe el código "{codigo}".')

    def add_selected_to_cart(self):
        """
        Búsqueda lineal en el carrito: O(k).
        Complejidad documentada en db.py / algorithms.py.
        """
        sel = self.sale_tree.selection()
        if not sel:
            return messagebox.showwarning('Venta', 'Selecciona un producto.')
        pid = int(sel[0])
        p = self.db.get_product(pid)
        try:
            qty = float(self.sale_qty.get())
        except Exception:
            return messagebox.showerror('Cantidad', 'Ingresa una cantidad válida.')
        if qty <= 0:
            return messagebox.showerror('Cantidad', 'La cantidad debe ser mayor que 0.')
        current = sum(i['quantity'] for i in self.cart if i['product_id'] == pid)
        if current + qty > float(p['stock']):
            return messagebox.showerror('Stock', f"Stock disponible: {p['stock']}")
        # Búsqueda lineal O(k)
        found = next((i for i in self.cart if i['product_id'] == pid), None)
        if found:
            found['quantity'] += qty
        else:
            self.cart.append({
                'product_id': pid,
                'name': p['name'],
                'quantity': qty,
                'price': float(p['sale_price']),
            })
        self.refresh_cart()

    def refresh_cart(self):
        if not hasattr(self, 'cart_tree'):
            return
        for x in self.cart_tree.get_children():
            self.cart_tree.delete(x)
        total = 0
        for i, item in enumerate(self.cart):
            lt = item['quantity'] * item['price']
            total += lt
            self.cart_tree.insert(
                '', 'end', iid=str(i),
                values=(item['name'], f"{item['quantity']:g}",
                        self.money(item['price']), self.money(lt))
            )
        self.total_label.config(text=f"TOTAL: {self.money(total)}")
        self.update_change()

    def remove_cart(self):
        sel = self.cart_tree.selection()
        if sel:
            self.cart.pop(int(sel[0]))
            self.refresh_cart()

    def payment_changed(self):
        total = sum(i['quantity'] * i['price'] for i in self.cart)
        if self.pay_method.get() != 'EFECTIVO':
            self.received.set(f"{total:.2f}")
        self.update_change()

    def update_change(self):
        if not hasattr(self, 'change_label'):
            return
        total = sum(i['quantity'] * i['price'] for i in self.cart)
        try:
            rec = float(self.received.get() or 0)
        except Exception:
            rec = 0
        ch = max(0, rec - total) if self.pay_method.get() == 'EFECTIVO' else 0
        self.change_label.config(text=f"Vuelto: {self.money(ch)}")
        # Vista previa del desglose voraz
        if hasattr(self, 'breakdown_label') and ch > 0:
            from algorithms import desglosar_vuelto, formatear_desglose
            self.breakdown_label.config(
                text=f"Desglose: {formatear_desglose(desglosar_vuelto(ch))}"
            )
        elif hasattr(self, 'breakdown_label'):
            self.breakdown_label.config(text='')

    def complete_sale(self):
        """Registra la venta y abre la boleta formal."""
        # Guardar copia del carrito antes de vaciarlo (para la boleta)
        cart_copia = [dict(item) for item in self.cart]
        metodo = self.pay_method.get()
        try:
            result = self.db.create_sale(
                self.cart, metodo, self.received.get() or 0
            )
        except Exception as e:
            return messagebox.showerror('No se pudo registrar', str(e))

        # Limpiar carrito y refrescar
        self.cart = []
        self.purchase_cart = []
        self.received.set('')
        self.refresh_sale_products()
        self.refresh_cart()

        # Abrir boleta formal
        self.show_boleta(result, cart_copia, metodo)

    def show_boleta(self, result, cart_items, payment_method):
        """
        Ventana de boleta de venta.
        Se abre automáticamente al registrar la venta.
        """
        w = tk.Toplevel(self)
        w.title(f"Boleta de venta — {result['number']}")
        w.transient(self)
        w.configure(bg='white')
        w.grab_set()

        # Contenedor principal
        outer = tk.Frame(w, bg='white', padx=24, pady=18)
        outer.pack(fill='both', expand=True)
        # Botones: zona fija abajo (siempre visible, aunque haya muchos ítems)
        btns = tk.Frame(outer, bg='white')
        btns.pack(side='bottom', fill='x', pady=(16, 0))

        # --- Encabezado ---
        tk.Label(
            outer, text='MI TIENDA', font=('Segoe UI', 16, 'bold'),
            bg='white', fg='#172033'
        ).pack()
        tk.Label(
            outer, text='Boleta de Venta', font=('Segoe UI', 11),
            bg='white', fg='#607089'
        ).pack()
        tk.Label(
            outer, text='─' * 42, bg='white', fg='#cbd5e0'
        ).pack(pady=(8, 4))

        # Datos de la venta
        info = tk.Frame(outer, bg='white')
        info.pack(fill='x')
        tk.Label(info, text=f"N.º: {result['number']}", font=('Segoe UI', 10, 'bold'),
                 bg='white', anchor='w').pack(fill='x')
        tk.Label(info, text=f"Fecha: {result['date']}", font=('Segoe UI', 9),
                 bg='white', fg='#4a5568', anchor='w').pack(fill='x')
        tk.Label(info, text=f"Pago: {payment_method}", font=('Segoe UI', 9),
                 bg='white', fg='#4a5568', anchor='w').pack(fill='x')
        tk.Label(
            outer, text='─' * 42, bg='white', fg='#cbd5e0'
        ).pack(pady=(6, 4))

        # --- Detalle de ítems ---
        tk.Label(
            outer, text='DETALLE', font=('Segoe UI', 9, 'bold'),
            bg='white', fg='#607089', anchor='w'
        ).pack(fill='x')

        # Cabecera de columnas
        header = tk.Frame(outer, bg='white')
        header.pack(fill='x', pady=(2, 2))
        tk.Label(header, text='Producto', font=('Segoe UI', 8, 'bold'),
                 bg='white', width=22, anchor='w').pack(side='left')
        tk.Label(header, text='Cant', font=('Segoe UI', 8, 'bold'),
                 bg='white', width=5, anchor='e').pack(side='left')
        tk.Label(header, text='P.Unit', font=('Segoe UI', 8, 'bold'),
                 bg='white', width=8, anchor='e').pack(side='left')
        tk.Label(header, text='Total', font=('Segoe UI', 8, 'bold'),
                 bg='white', width=9, anchor='e').pack(side='left')

        # Ítems (scroll si hay muchos)
        items_box = tk.Frame(outer, bg='white')
        items_box.pack(fill='x')
        items_canvas = tk.Canvas(items_box, bg='white', highlightthickness=0,
                                 height=min(len(cart_items), 7) * 22 + 6, width=360)
        items_frame = tk.Frame(items_canvas, bg='white')
        items_canvas.create_window((0, 0), window=items_frame, anchor='nw')
        items_frame.bind('<Configure>', lambda e: items_canvas.configure(
            scrollregion=items_canvas.bbox('all')))
        if len(cart_items) > 7:
            sb = ttk.Scrollbar(items_box, orient='vertical', command=items_canvas.yview)
            items_canvas.configure(yscrollcommand=sb.set)
            sb.pack(side='right', fill='y')
        items_canvas.pack(side='left', fill='x', expand=True)
        for item in cart_items:
            qty = float(item['quantity'])
            price = float(item['price'])
            line = round(qty * price, 2)
            row = tk.Frame(items_frame, bg='white')
            row.pack(fill='x', pady=1)
            # Truncar nombre largo
            nombre = item['name'][:22]
            tk.Label(row, text=nombre, font=('Segoe UI', 8),
                     bg='white', width=22, anchor='w').pack(side='left')
            tk.Label(row, text=f"{qty:g}", font=('Segoe UI', 8),
                     bg='white', width=5, anchor='e').pack(side='left')
            tk.Label(row, text=f"{price:.2f}", font=('Segoe UI', 8),
                     bg='white', width=8, anchor='e').pack(side='left')
            tk.Label(row, text=f"{line:.2f}", font=('Segoe UI', 8),
                     bg='white', width=9, anchor='e').pack(side='left')

        tk.Label(
            outer, text='─' * 42, bg='white', fg='#cbd5e0'
        ).pack(pady=(8, 4))

        # --- Totales ---
        totals = tk.Frame(outer, bg='white')
        totals.pack(fill='x')
        tk.Label(
            totals, text=f"TOTAL:  {self.money(result['total'])}",
            font=('Segoe UI', 13, 'bold'), bg='white', fg='#172033',
            anchor='e'
        ).pack(fill='x')

        if payment_method == 'EFECTIVO':
            tk.Label(
                totals, text=f"Recibido:  {self.money(result['received'])}",
                font=('Segoe UI', 9), bg='white', fg='#4a5568', anchor='e'
            ).pack(fill='x')
            tk.Label(
                totals, text=f"Vuelto:  {self.money(result['change'])}",
                font=('Segoe UI', 10, 'bold'), bg='white', fg='#276749',
                anchor='e'
            ).pack(fill='x')
            if result.get('change_text'):
                tk.Label(
                    totals, text=f"Desglose: {result['change_text']}",
                    font=('Segoe UI', 8), bg='white', fg='#607089',
                    anchor='e', wraplength=360, justify='right'
                ).pack(fill='x', pady=(2, 0))

        tk.Label(
            outer, text='─' * 42, bg='white', fg='#cbd5e0'
        ).pack(pady=(10, 4))
        tk.Label(
            outer, text='¡Gracias por su compra!',
            font=('Segoe UI', 9, 'italic'), bg='white', fg='#607089'
        ).pack()

        # --- Botones (el contenedor se creó arriba, fijo al pie) ---
        def imprimir():
            """Envía la boleta a la impresora predeterminada del sistema."""
            try:
                # Construir texto plano de la boleta
                lineas = [
                    '=' * 40,
                    '         MI TIENDA',
                    '       Boleta de Venta',
                    '=' * 40,
                    f"N.º:    {result['number']}",
                    f"Fecha:  {result['date']}",
                    f"Pago:   {payment_method}",
                    '-' * 40,
                    f"{'Producto':<22} {'Cant':>4} {'P.U.':>6} {'Total':>7}",
                    '-' * 40,
                ]
                for item in cart_items:
                    qty = float(item['quantity'])
                    price = float(item['price'])
                    line = round(qty * price, 2)
                    nombre = item['name'][:22]
                    lineas.append(
                        f"{nombre:<22} {qty:>4g} {price:>6.2f} {line:>7.2f}"
                    )
                lineas.append('-' * 40)
                lineas.append(f"{'TOTAL:':>33} {result['total']:>7.2f}")
                if payment_method == 'EFECTIVO':
                    lineas.append(f"{'Recibido:':>33} {result['received']:>7.2f}")
                    lineas.append(f"{'Vuelto:':>33} {result['change']:>7.2f}")
                    if result.get('change_text'):
                        lineas.append(f"Desglose: {result['change_text']}")
                lineas.append('=' * 40)
                lineas.append('     ¡Gracias por su compra!')
                lineas.append('=' * 40)
                texto = '\n'.join(lineas)

                # Guardar temporal y abrir con el visor/impresora del SO
                import tempfile, os, subprocess, sys
                tmp = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.txt', delete=False, encoding='utf-8'
                )
                tmp.write(texto)
                tmp.close()

                if sys.platform.startswith('win'):
                    os.startfile(tmp.name, 'print')
                elif sys.platform == 'darwin':
                    subprocess.run(['lpr', tmp.name], check=False)
                else:
                    # Linux: intentar lpr o abrir el archivo
                    try:
                        subprocess.run(['lpr', tmp.name], check=False)
                    except Exception:
                        subprocess.run(['xdg-open', tmp.name], check=False)

                messagebox.showinfo(
                    'Imprimir', 
                    'Boleta enviada a la impresora.\n'
                    f'(También guardada en:\n{tmp.name})',
                    parent=w
                )
            except Exception as e:
                messagebox.showerror('Imprimir', f'No se pudo imprimir:\n{e}', parent=w)

        tk.Button(
            btns, text='🖨  Imprimir', command=imprimir,
            bg='#1769aa', fg='white', font=('Segoe UI', 10, 'bold'),
            relief='flat', padx=16, pady=8, cursor='hand2'
        ).pack(side='left', expand=True, fill='x', padx=(0, 6))

        tk.Button(
            btns, text='Cerrar', command=w.destroy,
            bg='#e2e8f0', fg='#172033', font=('Segoe UI', 10),
            relief='flat', padx=16, pady=8, cursor='hand2'
        ).pack(side='left', expand=True, fill='x', padx=(6, 0))

        self._fit_dialog(w, 420)

    # ------------------------------------------------------------------
    # WAREHOUSE
    # ------------------------------------------------------------------
    def show_warehouse(self):
        self.clear()
        self.header('Almacén', 'Administra productos, precios y existencias.')
        top = ttk.Frame(self.content)
        top.pack(fill='x')
        self.wh_search = tk.StringVar()
        ttk.Button(top, text='Entrada / salida',
                   command=self.stock_dialog).pack(side='right', padx=(8, 0))
        ttk.Button(top, text='Nuevo producto', style='Primary.TButton',
                   command=self.product_form).pack(side='right', padx=(10, 0))
        ttk.Entry(top, textvariable=self.wh_search).pack(side='left', fill='x', expand=True)
        self.wh_search.trace_add('write', lambda *_: self.refresh_products())
        actions = ttk.Frame(self.content)
        actions.pack(side='bottom', fill='x', pady=(10, 0))
        ttk.Button(actions, text='Editar', command=self.edit_product).pack(side='left')
        ttk.Button(actions, text='Eliminar',
                   command=self.delete_product).pack(side='left', padx=8)
        box = ttk.Frame(self.content, style='Card.TFrame', padding=10)
        box.pack(fill='both', expand=True, pady=(12, 0))
        cols = ('code', 'name', 'cat', 'unit', 'buy', 'sale', 'stock', 'min')
        self.wh_tree = ttk.Treeview(box, columns=cols, show='headings')
        heads = [
            ('code', 'Código', 90), ('name', 'Producto', 250), ('cat', 'Categoría', 120),
            ('unit', 'Unidad', 70), ('buy', 'P. compra', 85), ('sale', 'P. venta', 85),
            ('stock', 'Stock', 70), ('min', 'Mín.', 65)
        ]
        for c, t, w in heads:
            self.wh_tree.heading(c, text=t)
            self.wh_tree.column(c, width=w, anchor='center' if c != 'name' else 'w')
        self.wh_tree.pack(fill='both', expand=True)
        self.wh_tree.bind('<Double-1>', lambda _: self.edit_product())
        self.refresh_products()

    def refresh_products(self):
        if not hasattr(self, 'wh_tree'):
            return
        for x in self.wh_tree.get_children():
            self.wh_tree.delete(x)
        for r in self.db.list_products(self.wh_search.get()):
            self.wh_tree.insert(
                '', 'end', iid=str(r['id']),
                values=(
                    r['code'], r['name'], r['category'], r['unit'],
                    self.money(r['purchase_price']), self.money(r['sale_price']),
                    f"{r['stock']:g}", f"{r['min_stock']:g}"
                ),
                tags=('low',) if r['stock'] <= r['min_stock'] else ()
            )
        self.wh_tree.tag_configure('low', background='#fff3cd')

    def product_form(self, product=None):
        w = tk.Toplevel(self)
        w.title('Producto')
        w.transient(self)
        w.grab_set()
        w.configure(bg='#eef2f7')
        frame = ttk.Frame(w, padding=20)
        frame.pack(fill='both', expand=True)
        fields = [
            ('Código', 'code'), ('Nombre', 'name'), ('Categoría', 'category'),
            ('Unidad', 'unit'), ('Precio de compra', 'purchase_price'),
            ('Precio de venta', 'sale_price'), ('Stock', 'stock'),
            ('Stock mínimo', 'min_stock')
        ]
        vars_ = {}
        for row, (lab, key) in enumerate(fields):
            ttk.Label(frame, text=lab).grid(row=row, column=0, sticky='w', pady=7)
            v = tk.StringVar()
            vars_[key] = v
            ttk.Entry(frame, textvariable=v).grid(
                row=row, column=1, sticky='ew', padx=(12, 0), pady=7
            )
        frame.columnconfigure(1, weight=1)
        if product:
            for k in vars_:
                vars_[k].set(product[k])
        else:
            vars_['unit'].set('UND')
            vars_['purchase_price'].set('0')
            vars_['sale_price'].set('0')
            vars_['stock'].set('0')
            vars_['min_stock'].set('0')

        def save():
            try:
                data = {k: v.get() for k, v in vars_.items()}
                if not data['code'].strip() or not data['name'].strip():
                    raise ValueError('Código y nombre son obligatorios.')
                for k in ['purchase_price', 'sale_price', 'stock', 'min_stock']:
                    if float(data[k]) < 0:
                        raise ValueError('Los valores numéricos no pueden ser negativos.')
                self.db.save_product(data, product['id'] if product else None)
                w.destroy()
                self.refresh_products()
            except sqlite3.IntegrityError:
                messagebox.showerror('Producto', 'El código ya existe.', parent=w)
            except Exception as e:
                messagebox.showerror('Producto', str(e), parent=w)

        ttk.Button(
            frame, text='Guardar producto', style='Primary.TButton', command=save
        ).grid(row=len(fields), column=0, columnspan=2, sticky='ew', pady=(18, 0))
        self._fit_dialog(w, 440)

    def edit_product(self):
        sel = self.wh_tree.selection()
        if not sel:
            return messagebox.showwarning('Almacén', 'Selecciona un producto.')
        self.product_form(self.db.get_product(int(sel[0])))

    def delete_product(self):
        sel = self.wh_tree.selection()
        if not sel:
            return
        if messagebox.askyesno('Eliminar', '¿Deseas retirar este producto del catálogo?'):
            self.db.deactivate_product(int(sel[0]))
            self.refresh_products()

    def stock_dialog(self):
        sel = self.wh_tree.selection()
        if not sel:
            return messagebox.showwarning('Almacén', 'Selecciona un producto.')
        p = self.db.get_product(int(sel[0]))
        w = tk.Toplevel(self)
        w.title('Movimiento de stock')
        w.transient(self)
        w.grab_set()
        f = ttk.Frame(w, padding=20)
        f.pack(fill='both', expand=True)
        ttk.Label(f, text=p['name'], font=('Segoe UI', 14, 'bold')).pack(anchor='w')
        ttk.Label(f, text=f"Stock actual: {p['stock']:g} {p['unit']}").pack(
            anchor='w', pady=(2, 15)
        )
        typ = tk.StringVar(value='ENTRADA')
        ttk.Label(f, text='Tipo').pack(anchor='w')
        ttk.Combobox(f, textvariable=typ, values=['ENTRADA', 'SALIDA'],
                     state='readonly').pack(fill='x', pady=(2, 10))
        qty = tk.StringVar()
        ttk.Label(f, text='Cantidad').pack(anchor='w')
        ttk.Entry(f, textvariable=qty).pack(fill='x', pady=(2, 10))
        note = tk.StringVar()
        ttk.Label(f, text='Motivo / nota').pack(anchor='w')
        ttk.Entry(f, textvariable=note).pack(fill='x', pady=(2, 12))

        def save():
            try:
                self.db.adjust_stock(p['id'], float(qty.get()), typ.get(), note.get())
                w.destroy()
                self.refresh_products()
            except Exception as e:
                messagebox.showerror('Stock', str(e), parent=w)

        ttk.Button(f, text='Registrar movimiento', style='Primary.TButton',
                   command=save).pack(fill='x')
        self._fit_dialog(w, 420)

    # ------------------------------------------------------------------
    # COMPRAS (aumentan el stock)
    # ------------------------------------------------------------------
    def show_purchases(self):
        self.clear()
        self.header('Compras', 'Registra la mercadería que ingresa: aumenta el stock y el egreso de caja.')
        left, right = self._two_panes(400, 340)

        searchrow = ttk.Frame(left, style='Card.TFrame')
        searchrow.pack(fill='x')
        ttk.Label(searchrow, text='Buscar:', background='white').pack(side='left')
        self.pur_search = tk.StringVar()
        e = ttk.Entry(searchrow, textvariable=self.pur_search)
        e.pack(side='left', fill='x', expand=True, padx=8)
        e.bind('<KeyRelease>', lambda _: self.refresh_purchase_products())
        ttk.Button(left, text='Historial de compras',
                   command=self.purchases_history_dialog).pack(anchor='w', pady=(8, 0))

        # Zona inferior fija (se empaqueta antes de la tabla)
        addbox = ttk.Frame(left, style='Card.TFrame')
        addbox.pack(side='bottom', fill='x')
        addrow = ttk.Frame(addbox, style='Card.TFrame')
        addrow.pack(fill='x')
        ttk.Label(addrow, text='Cantidad:', background='white').pack(side='left')
        self.pur_qty = tk.StringVar(value='1')
        ttk.Entry(addrow, textvariable=self.pur_qty, width=8).pack(side='left', padx=8)
        ttk.Label(addrow, text='Costo unit. S/:', background='white').pack(side='left')
        self.pur_cost = tk.StringVar()
        ttk.Entry(addrow, textvariable=self.pur_cost, width=9).pack(side='left', padx=8)
        ttk.Button(addbox, text='Agregar a la compra', style='Primary.TButton',
                   command=self.add_to_purchase).pack(fill='x', pady=(8, 0))

        cols = ('codigo', 'producto', 'stock', 'costo')
        self.pur_tree = ttk.Treeview(left, columns=cols, show='headings', height=8)
        for c, t, w in [
            ('codigo', 'Código', 90), ('producto', 'Producto', 260),
            ('stock', 'Stock', 75), ('costo', 'Últ. costo', 90)
        ]:
            self.pur_tree.heading(c, text=t)
            self.pur_tree.column(c, width=w, anchor='center' if c != 'producto' else 'w')
        self.pur_tree.pack(fill='both', expand=True, pady=12)
        self.pur_tree.bind('<Double-1>', lambda _: self.add_to_purchase())
        self.pur_tree.bind('<<TreeviewSelect>>', lambda _: self._fill_purchase_cost())

        ttk.Label(right, text='Compra', background='white',
                  font=('Segoe UI', 14, 'bold')).pack(anchor='w')

        bottom = ttk.Frame(right, style='Card.TFrame')
        bottom.pack(side='bottom', fill='x')
        ttk.Button(bottom, text='Quitar seleccionado',
                   command=self.remove_purchase_item).pack(anchor='e')
        ttk.Button(bottom, text='REGISTRAR COMPRA', style='Primary.TButton',
                   command=self.complete_purchase).pack(fill='x', pady=(8, 0))
        form = ttk.Frame(bottom, style='Card.TFrame')
        form.pack(fill='x', pady=(8, 0))
        form.columnconfigure(1, weight=1)
        ttk.Label(form, text='Proveedor:', background='white').grid(row=0, column=0, sticky='w', pady=3)
        self.pur_supplier = tk.StringVar()
        ttk.Entry(form, textvariable=self.pur_supplier).grid(row=0, column=1, sticky='ew', padx=(8, 0))
        ttk.Label(form, text='Pago:', background='white').grid(row=1, column=0, sticky='w', pady=3)
        self.pur_method = tk.StringVar(value='EFECTIVO')
        ttk.Combobox(
            form, textvariable=self.pur_method,
            values=['EFECTIVO', 'YAPE/PLIN', 'TARJETA', 'TRANSFERENCIA'], state='readonly'
        ).grid(row=1, column=1, sticky='ew', padx=(8, 0))
        self.pur_cash = tk.BooleanVar(value=True)
        ttk.Checkbutton(form, text='Registrar egreso en caja', variable=self.pur_cash).grid(
            row=2, column=0, columnspan=2, sticky='w', pady=3)
        self.pur_total_label = ttk.Label(bottom, text='TOTAL: S/ 0.00', background='white',
                                         font=('Segoe UI', 18, 'bold'))
        self.pur_total_label.pack(anchor='e', pady=(4, 0))
        ttk.Separator(bottom).pack(fill='x', pady=6)

        cols = ('producto', 'cant', 'costo', 'total')
        self.pur_cart_tree = ttk.Treeview(right, columns=cols, show='headings', height=8)
        for c, t, w in [
            ('producto', 'Producto', 190), ('cant', 'Cant.', 65),
            ('costo', 'Costo', 75), ('total', 'Total', 80)
        ]:
            self.pur_cart_tree.heading(c, text=t)
            self.pur_cart_tree.column(c, width=w, anchor='center' if c != 'producto' else 'w')
        self.pur_cart_tree.pack(fill='both', expand=True, pady=(6, 4))

        self.refresh_purchase_products()
        self.refresh_purchase_cart()

    def refresh_purchase_products(self):
        for x in self.pur_tree.get_children():
            self.pur_tree.delete(x)
        for r in self.db.list_products(self.pur_search.get()):
            self.pur_tree.insert(
                '', 'end', iid=str(r['id']),
                values=(r['code'], r['name'], f"{r['stock']:g}", self.money(r['purchase_price']))
            )

    def _fill_purchase_cost(self):
        sel = self.pur_tree.selection()
        if sel:
            p = self.db.get_product(int(sel[0]))
            self.pur_cost.set(f"{float(p['purchase_price']):.2f}")

    def add_to_purchase(self):
        sel = self.pur_tree.selection()
        if not sel:
            return messagebox.showwarning('Compras', 'Selecciona un producto.')
        try:
            qty = float(self.pur_qty.get())
            cost = float(self.pur_cost.get())
        except ValueError:
            return messagebox.showerror('Compras', 'Ingresa una cantidad y un costo válidos.')
        if qty <= 0:
            return messagebox.showerror('Compras', 'La cantidad debe ser mayor que cero.')
        if cost < 0:
            return messagebox.showerror('Compras', 'El costo no puede ser negativo.')
        p = self.db.get_product(int(sel[0]))
        self.purchase_cart.append(
            {'product_id': p['id'], 'name': p['name'], 'quantity': qty, 'cost': cost}
        )
        self.pur_qty.set('1')
        self.refresh_purchase_cart()

    def refresh_purchase_cart(self):
        for x in self.pur_cart_tree.get_children():
            self.pur_cart_tree.delete(x)
        total = 0
        for i, it in enumerate(self.purchase_cart):
            lt = it['quantity'] * it['cost']
            total += lt
            self.pur_cart_tree.insert(
                '', 'end', iid=str(i),
                values=(it['name'], f"{it['quantity']:g}", self.money(it['cost']), self.money(lt))
            )
        self.pur_total_label.config(text=f"TOTAL: {self.money(total)}")

    def remove_purchase_item(self):
        sel = self.pur_cart_tree.selection()
        if sel:
            self.purchase_cart.pop(int(sel[0]))
            self.refresh_purchase_cart()

    def complete_purchase(self):
        if not self.purchase_cart:
            return messagebox.showwarning('Compras', 'Agrega al menos un producto a la compra.')
        try:
            r = self.db.create_purchase(
                self.purchase_cart, self.pur_supplier.get(), self.pur_method.get(),
                self.pur_cash.get()
            )
        except Exception as e:
            return messagebox.showerror('No se pudo registrar', str(e))
        self.purchase_cart = []
        self.pur_supplier.set('')
        self.refresh_purchase_products()
        self.refresh_purchase_cart()
        messagebox.showinfo(
            'Compra registrada',
            f"{r['number']}\nTotal: {self.money(r['total'])}\nEl stock fue actualizado."
        )

    def purchases_history_dialog(self):
        w = tk.Toplevel(self)
        w.title('Historial de compras')
        w.transient(self)
        f = ttk.Frame(w, padding=16)
        f.pack(fill='both', expand=True)
        ttk.Button(f, text='Cerrar', command=w.destroy).pack(side='bottom', anchor='e', pady=(10, 0))
        cols = ('numero', 'fecha', 'proveedor', 'pago', 'total')
        tree = ttk.Treeview(f, columns=cols, show='headings')
        for c, t, wd in [
            ('numero', 'N.º', 120), ('fecha', 'Fecha / hora', 150),
            ('proveedor', 'Proveedor', 200), ('pago', 'Pago', 110), ('total', 'Total', 100)
        ]:
            tree.heading(c, text=t)
            tree.column(c, width=wd, anchor='center' if c != 'proveedor' else 'w')
        tree.pack(fill='both', expand=True)
        for r in self.db.list_purchases():
            tree.insert('', 'end', values=(
                r['purchase_number'], r['date'], r['supplier'] or '—',
                r['payment_method'], self.money(r['total'])
            ))
        self._fit_dialog(w, 760, 420)

    # ------------------------------------------------------------------
    # HISTORIAL DE VENTAS Y ANULACIÓN
    # ------------------------------------------------------------------
    def sales_history_dialog(self):
        w = tk.Toplevel(self)
        w.title('Historial de ventas')
        w.transient(self)
        f = ttk.Frame(w, padding=16)
        f.pack(fill='both', expand=True)

        bar = ttk.Frame(f)
        bar.pack(side='bottom', fill='x', pady=(10, 0))
        cols = ('numero', 'fecha', 'pago', 'total', 'estado', 'motivo')
        tree = ttk.Treeview(f, columns=cols, show='headings')
        for c, t, wd in [
            ('numero', 'N.º', 130), ('fecha', 'Fecha / hora', 140), ('pago', 'Pago', 110),
            ('total', 'Total', 90), ('estado', 'Estado', 80), ('motivo', 'Motivo de anulación', 230)
        ]:
            tree.heading(c, text=t)
            tree.column(c, width=wd, anchor='center' if c != 'motivo' else 'w')
        tree.tag_configure('anulada', foreground='#9aa5b5')
        tree.pack(fill='both', expand=True)

        def load():
            for x in tree.get_children():
                tree.delete(x)
            for r in self.db.list_sales():
                anulada = r['status'] == 'ANULADA'
                tree.insert(
                    '', 'end', iid=str(r['id']), tags=('anulada',) if anulada else (),
                    values=(r['sale_number'], r['date'], r['payment_method'],
                            self.money(r['total']), r['status'], r['void_reason'] or '')
                )

        def anular():
            sel = tree.selection()
            if not sel:
                return messagebox.showwarning('Anular venta', 'Selecciona una venta.', parent=w)
            sale_id = int(sel[0])
            row = tree.item(sel[0])['values']
            if row[4] == 'ANULADA':
                return messagebox.showinfo('Anular venta', 'Esa venta ya está anulada.', parent=w)
            reason = simpledialog.askstring(
                'Anular venta', f'Motivo de la anulación de {row[0]}:', parent=w)
            if reason is None:
                return
            if not messagebox.askyesno(
                'Confirmar',
                f'¿Anular la venta {row[0]} por {row[3]}?\n'
                'Se devolverá el stock y se registrará un egreso en caja.', parent=w
            ):
                return
            try:
                self.db.void_sale(sale_id, reason)
            except Exception as e:
                return messagebox.showerror('Anular venta', str(e), parent=w)
            load()
            try:
                self.refresh_sale_products()
            except tk.TclError:
                pass  # la pantalla de ventas ya no está abierta
            messagebox.showinfo('Anular venta', 'Venta anulada. El stock fue restituido.', parent=w)

        ttk.Button(bar, text='Anular venta seleccionada', style='Primary.TButton',
                   command=anular).pack(side='left')
        ttk.Button(bar, text='Cerrar', command=w.destroy).pack(side='right')
        load()
        self._fit_dialog(w, 860, 470)

    # ------------------------------------------------------------------
    # DEVOLUCIONES: protocolo de revisión (recibir -> evaluar -> resolver)
    # ------------------------------------------------------------------
    REASON_LABELS = {'VENCIMIENTO': 'Vencimiento', 'MAL_ESTADO': 'Mal estado'}

    def show_returns(self):
        self.clear()
        self.header(
            'Devoluciones',
            'Recibir → Evaluar → Cambio o reembolso. El stock solo cambia al evaluar.'
        )
        left, right = self._two_panes(370, 400, 2, 3)

        # ---------------- Panel izquierdo: recepción ----------------
        ttk.Label(left, text='1. Recibir producto devuelto', background='white',
                  font=('Segoe UI', 13, 'bold')).pack(anchor='w')

        # Zona inferior fija: formulario y botón (se empaquetan antes que la tabla)
        ttk.Button(left, text='Registrar devolución',
                   style='Primary.TButton',
                   command=self._register_return).pack(side='bottom', fill='x', pady=(10, 0))
        form = ttk.Frame(left, style='Card.TFrame')
        form.pack(side='bottom', fill='x', pady=(8, 0))
        form.columnconfigure(1, weight=1)
        self.ret_qty = tk.StringVar(value='1')
        self.ret_reason = tk.StringVar(value='VENCIMIENTO')
        self.ret_expiry = tk.StringVar()
        self.ret_customer = tk.StringVar()
        ttk.Label(form, text='Cantidad:', background='white').grid(row=0, column=0, sticky='w', pady=3)
        ttk.Entry(form, textvariable=self.ret_qty, width=10).grid(row=0, column=1, sticky='w', padx=(8, 0))
        ttk.Label(form, text='Motivo:', background='white').grid(row=1, column=0, sticky='w', pady=3)
        cb = ttk.Combobox(form, textvariable=self.ret_reason, state='readonly',
                          values=list(self.db.RETURN_REASONS))
        cb.grid(row=1, column=1, sticky='ew', padx=(8, 0))
        ttk.Label(form, text='Vencimiento:', background='white').grid(row=2, column=0, sticky='w', pady=3)
        ttk.Entry(form, textvariable=self.ret_expiry).grid(row=2, column=1, sticky='ew', padx=(8, 0))
        ttk.Label(form, text='Formato AAAA-MM-DD', background='white',
                  foreground='#607089', font=('Segoe UI', 8)).grid(row=3, column=1, sticky='w', padx=(8, 0))
        ttk.Label(form, text='Cliente:', background='white').grid(row=4, column=0, sticky='w', pady=3)
        ttk.Entry(form, textvariable=self.ret_customer).grid(row=4, column=1, sticky='ew', padx=(8, 0))
        ttk.Label(form, text='Descripción:', background='white').grid(row=5, column=0, sticky='nw', pady=3)
        self.ret_desc = tk.Text(form, height=3, width=20, font=('Segoe UI', 9), wrap='word')
        self.ret_desc.grid(row=5, column=1, sticky='ew', padx=(8, 0), pady=3)

        sr = ttk.Frame(left, style='Card.TFrame')
        sr.pack(fill='x', pady=(10, 0))
        ttk.Label(sr, text='Buscar producto:', background='white').pack(side='left')
        self.ret_search = tk.StringVar()
        e = ttk.Entry(sr, textvariable=self.ret_search)
        e.pack(side='left', fill='x', expand=True, padx=8)
        e.bind('<KeyRelease>', lambda _: self._refresh_return_products())
        cols = ('codigo', 'producto', 'stock', 'precio')
        self.ret_prod_tree = ttk.Treeview(left, columns=cols, show='headings', height=5)
        for c, t, w_ in [('codigo', 'Código', 60), ('producto', 'Producto', 150),
                         ('stock', 'Stock', 45), ('precio', 'Precio', 65)]:
            self.ret_prod_tree.heading(c, text=t)
            self.ret_prod_tree.column(c, width=w_, anchor='center' if c != 'producto' else 'w')
        self.ret_prod_tree.pack(fill='both', expand=True, pady=(8, 0))

        # ---------------- Panel derecho: lista y evaluación ----------------
        top = ttk.Frame(right, style='Card.TFrame')
        top.pack(fill='x')
        ttk.Label(top, text='2. Evaluación', background='white',
                  font=('Segoe UI', 13, 'bold')).pack(side='left')
        self.ret_filter = tk.StringVar(value='TODAS')
        fcb = ttk.Combobox(top, textvariable=self.ret_filter, state='readonly', width=12,
                           values=['TODAS', 'PENDIENTE', 'APROBADA', 'RECHAZADA'])
        fcb.pack(side='right')
        fcb.bind('<<ComboboxSelected>>', lambda _: self.refresh_returns())

        bar = ttk.Frame(right, style='Card.TFrame')
        bar.pack(side='bottom', fill='x', pady=(10, 0))
        ttk.Button(bar, text='Evaluar devolución', style='Primary.TButton',
                   command=self._evaluate_selected).pack(side='left')
        ttk.Button(bar, text='Ver detalle',
                   command=self._detail_selected).pack(side='left', padx=8)

        cols = ('numero', 'producto', 'cant', 'motivo', 'estado')
        self.ret_tree = ttk.Treeview(right, columns=cols, show='headings', height=8)
        for c, t, w_ in [('numero', 'N.º', 95), ('producto', 'Producto', 105),
                         ('cant', 'Cant.', 40), ('motivo', 'Motivo', 55),
                         ('estado', 'Estado', 80)]:
            self.ret_tree.heading(c, text=t)
            self.ret_tree.column(c, width=w_, anchor='w' if c == 'producto' else 'center')
        self.ret_tree.tag_configure('PENDIENTE', background='#fff3cd')
        self.ret_tree.tag_configure('RECHAZADA', foreground='#9aa5b5')
        self.ret_tree.pack(fill='both', expand=True, pady=(10, 0))
        self.ret_tree.bind('<Double-1>', lambda _: self._evaluate_selected())

        self._refresh_return_products()
        self.refresh_returns()

    def _refresh_return_products(self):
        if not hasattr(self, 'ret_prod_tree'):
            return
        for x in self.ret_prod_tree.get_children():
            self.ret_prod_tree.delete(x)
        for r in self.db.list_products(self.ret_search.get()):
            self.ret_prod_tree.insert('', 'end', iid=str(r['id']), values=(
                r['code'], r['name'], f"{r['stock']:g}", self.money(r['sale_price'])))

    def refresh_returns(self):
        if not hasattr(self, 'ret_tree'):
            return
        for x in self.ret_tree.get_children():
            self.ret_tree.delete(x)
        flt = self.ret_filter.get()
        for r in self.db.list_returns('' if flt == 'TODAS' else flt):
            self.ret_tree.insert('', 'end', iid=str(r['id']), tags=(r['status'],), values=(
                r['return_number'][4:], r['product_name'], f"{r['quantity']:g}",
                'Venc.' if r['reason'] == 'VENCIMIENTO' else 'Daño', r['status']))

    def _register_return(self):
        sel = self.ret_prod_tree.selection()
        if not sel:
            return messagebox.showwarning('Devoluciones', 'Selecciona el producto devuelto.')
        try:
            res = self.db.register_return(
                int(sel[0]), self.ret_qty.get(), self.ret_reason.get(),
                self.ret_expiry.get(), self.ret_desc.get('1.0', 'end'),
                self.ret_customer.get())
        except Exception as e:
            return messagebox.showerror('Devoluciones', str(e))
        self.ret_desc.delete('1.0', 'end')
        self.ret_expiry.set('')
        self.ret_qty.set('1')
        self.refresh_returns()
        messagebox.showinfo(
            'Devolución registrada',
            f"{res['number']} quedó PENDIENTE de evaluación.\n"
            "El stock no se modifica hasta que la evalúes.")

    def _selected_return(self):
        sel = self.ret_tree.selection()
        if not sel:
            messagebox.showwarning('Devoluciones', 'Selecciona una devolución de la lista.')
            return None
        return int(sel[0])

    def _detail_selected(self):
        rid = self._selected_return()
        if rid is None:
            return
        r = self.db.get_return(rid)
        lines = [
            f"{r['return_number']} · {r['date']}",
            f"Producto: {r['product_name']} ({r['product_code']}) × {r['quantity']:g}",
            f"Motivo: {self.REASON_LABELS.get(r['reason'], r['reason'])}"
            + (f" · vence {r['expiry_date']}" if r['expiry_date'] else ''),
            f"Descripción: {r['description'] or '—'}",
            f"Cliente: {r['customer'] or '—'}",
            f"Estado: {r['status']}" + (f" · {r['resolution']}" if r['resolution'] else ''),
        ]
        if r['evaluated_at']:
            lines.append(f"Evaluada: {r['evaluated_at']}")
            lines.append(f"Observaciones: {r['evaluation_notes']}")
            lines.append(f"Crédito {self.money(r['credit_amount'])} · "
                         f"Reemplazo {self.money(r['exchange_total'])} · "
                         f"Diferencia {self.money(r['difference'])}")
            for it in self.db.get_return_items(rid):
                lines.append(f"   → {it['quantity']:g} × {it['product_name']}")
        messagebox.showinfo('Detalle de devolución', '\n'.join(lines))

    def _evaluate_selected(self):
        rid = self._selected_return()
        if rid is None:
            return
        r = self.db.get_return(rid)
        if r['status'] != 'PENDIENTE':
            return messagebox.showinfo(
                'Devoluciones', f"{r['return_number']} ya fue evaluada ({r['status']}).")
        self.evaluate_return_dialog(rid)

    def evaluate_return_dialog(self, return_id):
        r = self.db.get_return(return_id)
        w = tk.Toplevel(self)
        w.title(f"Evaluar devolución {r['return_number']}")
        w.transient(self)
        w.grab_set()
        w.configure(bg='#eef2f7')

        # Zona inferior fija: confirmar / cancelar siempre visibles
        bottom = ttk.Frame(w, padding=(16, 8, 16, 14))
        bottom.pack(side='bottom', fill='x')
        body = ttk.Frame(w, padding=(16, 16, 16, 0))
        body.pack(fill='both', expand=True)
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1, minsize=370)
        body.columnconfigure(1, weight=1, minsize=450)
        colL = ttk.Frame(body, style='Card.TFrame', padding=12)
        colR = ttk.Frame(body, style='Card.TFrame', padding=12)
        colL.grid(row=0, column=0, sticky='nsew', padx=(0, 8))
        colR.grid(row=0, column=1, sticky='nsew', padx=(8, 0))

        # ---- Columna izquierda: datos, checklist, dictamen ----
        venc = f"\nVence: {r['expiry_date']}" if r['expiry_date'] else ''
        ttk.Label(
            colL, background='white', wraplength=340, justify='left',
            text=(f"{r['product_name']} ({r['product_code']})\n"
                  f"Cantidad: {r['quantity']:g} · Crédito: {self.money(r['credit_amount'])}\n"
                  f"Motivo: {self.REASON_LABELS.get(r['reason'], r['reason'])}{venc}\n"
                  f"Descripción: {r['description'] or '—'}"),
        ).pack(anchor='w')
        ttk.Separator(colL).pack(fill='x', pady=8)

        ttk.Label(colL, text='Checklist de revisión', background='white',
                  font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        checks = []
        for txt in ['Revisé empaque y sello del producto',
                    'Verifiqué la fecha de vencimiento / el estado físico',
                    'Confirmé que NO es apto para la venta']:
            v = tk.BooleanVar(value=False)
            checks.append(v)
            ttk.Checkbutton(colL, style='Card.TCheckbutton', text=txt, variable=v).pack(anchor='w', pady=1)
        ttk.Separator(colL).pack(fill='x', pady=8)

        dictamen = tk.StringVar(value='APROBADA')
        resol = tk.StringVar(value='CAMBIO')
        ttk.Label(colL, text='Dictamen', background='white',
                  font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        ttk.Radiobutton(colL, style='Card.TRadiobutton', text='Aprobar (defecto confirmado)', value='APROBADA',
                        variable=dictamen, command=lambda: toggle()).pack(anchor='w')
        ttk.Radiobutton(colL, style='Card.TRadiobutton', text='Rechazar (el producto está bien)', value='RECHAZADA',
                        variable=dictamen, command=lambda: toggle()).pack(anchor='w')
        ttk.Label(colL, text='Resolución', background='white',
                  font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(8, 0))
        rb1 = ttk.Radiobutton(colL, style='Card.TRadiobutton', text='Cambiar por otro producto', value='CAMBIO',
                              variable=resol, command=lambda: toggle())
        rb1.pack(anchor='w')
        rb2 = ttk.Radiobutton(colL, style='Card.TRadiobutton', text='Reembolso en efectivo', value='REEMBOLSO',
                              variable=resol, command=lambda: toggle())
        rb2.pack(anchor='w')
        ttk.Label(colL, text='Observaciones (obligatorio)', background='white',
                  font=('Segoe UI', 10, 'bold')).pack(anchor='w', pady=(8, 2))
        notes = tk.Text(colL, height=3, width=30, font=('Segoe UI', 9), wrap='word')
        notes.pack(fill='both', expand=True)

        # ---- Columna derecha: producto(s) de reemplazo ----
        colR.columnconfigure(0, weight=1)
        colR.rowconfigure(2, weight=1)
        colR.rowconfigure(4, weight=1)
        ttk.Label(colR, text='Producto(s) de reemplazo', background='white',
                  font=('Segoe UI', 11, 'bold')).grid(row=0, column=0, sticky='w')
        opt = ttk.Frame(colR, style='Card.TFrame')
        opt.grid(row=1, column=0, sticky='ew', pady=(4, 4))
        same_cat = tk.BooleanVar(value=True)
        ttk.Checkbutton(opt, style='Card.TCheckbutton', text='Solo misma categoría', variable=same_cat,
                        command=lambda: load_cands()).pack(side='left')
        btn_sug = ttk.Button(opt, text='Sugerir (backtracking)', command=lambda: sugerir())
        btn_sug.pack(side='right')

        cand = ttk.Treeview(colR, columns=('p', 's', 'pr'), show='headings', height=5)
        for c, t, w_ in [('p', 'Disponible', 200), ('s', 'Stock', 50), ('pr', 'Precio', 70)]:
            cand.heading(c, text=t)
            cand.column(c, width=w_, anchor='w' if c == 'p' else 'center')
        cand.grid(row=2, column=0, sticky='nsew')

        addrow = ttk.Frame(colR, style='Card.TFrame')
        addrow.grid(row=3, column=0, sticky='ew', pady=4)
        ttk.Label(addrow, text='Cant.:', background='white').pack(side='left')
        qv = tk.StringVar(value='1')
        ttk.Entry(addrow, textvariable=qv, width=6).pack(side='left', padx=6)
        btn_add = ttk.Button(addrow, text='Agregar al cambio', command=lambda: agregar())
        btn_add.pack(side='left')
        btn_del = ttk.Button(addrow, text='Quitar', command=lambda: quitar())
        btn_del.pack(side='right')

        chosen_tree = ttk.Treeview(colR, columns=('p', 'q', 't'), show='headings', height=4)
        for c, t, w_ in [('p', 'Se entregará', 200), ('q', 'Cant.', 50), ('t', 'Subtotal', 70)]:
            chosen_tree.heading(c, text=t)
            chosen_tree.column(c, width=w_, anchor='w' if c == 'p' else 'center')
        chosen_tree.grid(row=4, column=0, sticky='nsew')
        resumen = ttk.Label(colR, text='', background='white', wraplength=420, justify='left',
                            font=('Segoe UI', 9, 'bold'))
        resumen.grid(row=5, column=0, sticky='ew', pady=(6, 0))

        chosen = {}      # pid -> {'name','price','qty'}
        stock_of = {}

        def load_cands():
            for x in cand.get_children():
                cand.delete(x)
            stock_of.clear()
            for p in self.db.list_products():
                if p['stock'] <= 0:
                    continue
                if same_cat.get() and p['category'] != r['product_category']:
                    continue
                stock_of[p['id']] = float(p['stock'])
                cand.insert('', 'end', iid=str(p['id']), values=(
                    p['name'], f"{p['stock']:g}", self.money(p['sale_price'])))

        def recalc(extra=''):
            for x in chosen_tree.get_children():
                chosen_tree.delete(x)
            total = 0.0
            for pid, it in chosen.items():
                sub = it['qty'] * it['price']
                total += sub
                chosen_tree.insert('', 'end', iid=str(pid), values=(
                    it['name'], f"{it['qty']:g}", self.money(sub)))
            credit = float(r['credit_amount'])
            diff = round(total - credit, 2)
            if resol.get() == 'REEMBOLSO' or not chosen:
                txt = f"Crédito: {self.money(credit)}"
            elif diff > 0:
                txt = (f"Crédito {self.money(credit)} · Reemplazo {self.money(total)}\n"
                       f"El cliente paga la diferencia: {self.money(diff)}")
            elif diff < 0:
                txt = (f"Crédito {self.money(credit)} · Reemplazo {self.money(total)}\n"
                       f"Se devuelve al cliente: {self.money(-diff)}")
            else:
                txt = f"Crédito {self.money(credit)} · Reemplazo {self.money(total)}\nSin diferencia"
            resumen.config(text=txt + (f"\n{extra}" if extra else ''))

        def agregar():
            s_ = cand.selection()
            if not s_:
                return messagebox.showwarning('Cambio', 'Selecciona un producto.', parent=w)
            try:
                q = float(qv.get())
                if q <= 0:
                    raise ValueError
            except ValueError:
                return messagebox.showwarning('Cambio', 'Cantidad inválida.', parent=w)
            pid = int(s_[0])
            p = self.db.get_product(pid)
            ya = chosen.get(pid, {}).get('qty', 0)
            if ya + q > stock_of.get(pid, 0):
                return messagebox.showwarning(
                    'Cambio', f"Stock insuficiente (hay {stock_of.get(pid, 0):g}).", parent=w)
            chosen[pid] = {'name': p['name'], 'price': float(p['sale_price']), 'qty': ya + q}
            recalc()

        def quitar():
            s_ = chosen_tree.selection()
            if s_:
                chosen.pop(int(s_[0]), None)
                recalc()

        def sugerir():
            try:
                res = self.db.sugerir_cambio(return_id, same_cat.get())
            except Exception as e:
                return messagebox.showerror('Cambio', str(e), parent=w)
            if not res['items']:
                chosen.clear()
                recalc()
                return messagebox.showinfo(
                    'Backtracking', 'No hay combinación posible con el stock disponible.\n'
                    'Prueba desmarcando "Solo misma categoría" o elige reembolso.', parent=w)
            chosen.clear()
            for it in res['items']:
                chosen[it['id']] = {'name': it['name'], 'price': it['price'], 'qty': it['qty']}
            recalc(f"Backtracking exploró {res['nodos']} combinaciones.")

        def toggle():
            aprob = dictamen.get() == 'APROBADA'
            cambio = aprob and resol.get() == 'CAMBIO'
            for rb in (rb1, rb2):
                rb.state(['!disabled'] if aprob else ['disabled'])
            for b in (btn_sug, btn_add, btn_del):
                b.state(['!disabled'] if cambio else ['disabled'])
            recalc()

        def confirmar():
            aprob = dictamen.get() == 'APROBADA'
            if aprob and not all(v.get() for v in checks):
                return messagebox.showwarning(
                    'Checklist', 'Completa todo el checklist de revisión antes de aprobar.',
                    parent=w)
            items = ([{'id': pid, 'qty': it['qty']} for pid, it in chosen.items()]
                     if aprob and resol.get() == 'CAMBIO' else [])
            try:
                res = self.db.evaluate_return(
                    return_id, dictamen.get(), notes.get('1.0', 'end'),
                    resol.get() if aprob else '', items)
            except Exception as e:
                return messagebox.showerror('Evaluación', str(e), parent=w)
            if res['status'] == 'RECHAZADA':
                msg = f"{res['number']} rechazada. El stock no se modificó."
            elif res['resolution'] == 'CAMBIO':
                msg = (f"{res['number']} aprobada y cambiada.\n"
                       "Stock actualizado: se descontaron los productos de reemplazo y el "
                       "producto devuelto se registró como merma.")
                if res['difference'] > 0:
                    msg += f"\nCobrar al cliente: {self.money(res['difference'])}"
                elif res['difference'] < 0:
                    msg += f"\nDevolver al cliente: {self.money(-res['difference'])}"
            else:
                msg = (f"{res['number']} aprobada. Reembolso de {self.money(res['credit'])} "
                       "registrado en caja; el producto se registró como merma.")
            w.destroy()
            self.refresh_returns()
            self._refresh_return_products()
            messagebox.showinfo('Evaluación', msg)

        ttk.Button(bottom, text='Confirmar evaluación', style='Primary.TButton',
                   command=confirmar).pack(side='left')
        ttk.Button(bottom, text='Cancelar', command=w.destroy).pack(side='right')
        load_cands()
        toggle()
        self._fit_dialog(w, 900, 560)

    # ------------------------------------------------------------------
    # CASH
    # ------------------------------------------------------------------
    def show_cash(self):
        self.clear()
        self.header('Caja', 'Control de ingresos y egresos del día.')
        summary = self.db.cash_summary_today()
        cards = ttk.Frame(self.content)
        cards.pack(fill='x')
        for i, (t, v) in enumerate([
            ('Ingresos', summary['ingresos']),
            ('Egresos', summary['egresos']),
            ('Saldo del día', summary['balance']),
            ('Efectivo estimado', summary['cash_balance']),
        ]):
            c = ttk.Frame(cards, style='Card.TFrame', padding=14)
            c.grid(row=0, column=i, sticky='nsew', padx=(0, 10))
            cards.columnconfigure(i, weight=1)
            ttk.Label(c, text=t, style='CardTitle.TLabel').pack(anchor='w')
            ttk.Label(c, text=self.money(v), style='CardValue.TLabel').pack(
                anchor='w', pady=4
            )
        bar = ttk.Frame(self.content)
        bar.pack(fill='x', pady=14)
        ttk.Button(bar, text='Registrar ingreso', style='Primary.TButton',
                   command=lambda: self.cash_dialog('INGRESO')).pack(side='left')
        ttk.Button(bar, text='Registrar egreso',
                   command=lambda: self.cash_dialog('EGRESO')).pack(side='left', padx=8)
        ttk.Label(bar, text=f"Ventas registradas hoy: {summary['sales_count']}").pack(
            side='right'
        )
        box = ttk.Frame(self.content, style='Card.TFrame', padding=10)
        box.pack(fill='both', expand=True)
        cols = ('date', 'type', 'concept', 'method', 'amount')
        self.cash_tree = ttk.Treeview(box, columns=cols, show='headings')
        for c, t, w in [
            ('date', 'Fecha / hora', 150), ('type', 'Tipo', 90),
            ('concept', 'Concepto', 330), ('method', 'Medio', 120),
            ('amount', 'Monto', 100)
        ]:
            self.cash_tree.heading(c, text=t)
            self.cash_tree.column(c, width=w, anchor='center' if c != 'concept' else 'w')
        self.cash_tree.pack(fill='both', expand=True)
        for r in self.db.cash_movements_today():
            self.cash_tree.insert(
                '', 'end',
                values=(r['date'], r['type'], r['concept'],
                        r['payment_method'], self.money(r['amount']))
            )

    def cash_dialog(self, typ):
        w = tk.Toplevel(self)
        w.title(f'Registrar {typ.lower()}')
        w.transient(self)
        w.grab_set()
        f = ttk.Frame(w, padding=20)
        f.pack(fill='both', expand=True)
        concept = tk.StringVar()
        amount = tk.StringVar()
        method = tk.StringVar(value='EFECTIVO')
        ttk.Label(f, text='Concepto').pack(anchor='w')
        ttk.Entry(f, textvariable=concept).pack(fill='x', pady=(2, 10))
        ttk.Label(f, text='Monto').pack(anchor='w')
        ttk.Entry(f, textvariable=amount).pack(fill='x', pady=(2, 10))
        ttk.Label(f, text='Medio').pack(anchor='w')
        ttk.Combobox(
            f, textvariable=method,
            values=['EFECTIVO', 'YAPE/PLIN', 'TARJETA', 'TRANSFERENCIA'],
            state='readonly'
        ).pack(fill='x', pady=(2, 15))

        def save():
            try:
                if not concept.get().strip():
                    raise ValueError('Ingresa un concepto.')
                self.db.add_cash_movement(typ, concept.get(), amount.get(), method.get())
                w.destroy()
                self.show_cash()
            except Exception as e:
                messagebox.showerror('Caja', str(e), parent=w)

        ttk.Button(f, text='Guardar', style='Primary.TButton', command=save).pack(fill='x')
        self._fit_dialog(w, 420)

    # ------------------------------------------------------------------
    # ALGORITMOS DEL CURSO (demostración T2)
    # ------------------------------------------------------------------
    def show_algorithms(self):
        self.clear()
        self.header(
            'Algoritmos del curso',
            'Voraz · Divide y vencerás · Recursividad · Prog. dinámica · Monte Carlo · Backtracking · Paralelismo'
        )
        outer = ttk.Frame(self.content, style='Card.TFrame')
        outer.pack(fill='both', expand=True)
        canvas = tk.Canvas(outer, bg='white', highlightthickness=0)
        scroll = ttk.Scrollbar(outer, orient='vertical', command=canvas.yview)
        canvas.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        canvas.pack(side='left', fill='both', expand=True)
        body = ttk.Frame(canvas, style='Card.TFrame', padding=20)
        win = canvas.create_window((0, 0), window=body, anchor='nw')
        body.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        self._wrap_labels = []

        def on_canvas_resize(e):
            canvas.itemconfigure(win, width=e.width)
            for lb in self._wrap_labels:
                lb.config(wraplength=max(260, e.width - 70))
        canvas.bind('<Configure>', on_canvas_resize)
        def _wheel(ev):
            if getattr(ev, 'num', 0) == 4:
                canvas.yview_scroll(-1, 'units')
            elif getattr(ev, 'num', 0) == 5:
                canvas.yview_scroll(1, 'units')
            else:
                canvas.yview_scroll(int(-ev.delta / 120) or (-1 if ev.delta > 0 else 1), 'units')

        def _bind_wheel(_):
            for seq in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
                canvas.bind_all(seq, _wheel)

        def _unbind_wheel(_):
            for seq in ('<MouseWheel>', '<Button-4>', '<Button-5>'):
                canvas.unbind_all(seq)
        canvas.bind('<Enter>', _bind_wheel)
        canvas.bind('<Leave>', _unbind_wheel)

        # --- Voraz ---
        ttk.Label(body, text='1. Algoritmo voraz – Desglose de vuelto',
                  background='white', font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Label(
            body,
            text='Toma siempre la mayor denominación posible (S/ 200, 100, 50… 0.10). Complejidad O(1).',
            background='white', foreground='#607089'
        ).pack(anchor='w', pady=(2, 6))
        row1 = ttk.Frame(body, style='Card.TFrame')
        row1.pack(anchor='w', pady=(0, 14))
        self.vuelto_var = tk.StringVar(value='47.80')
        ttk.Entry(row1, textvariable=self.vuelto_var, width=12).pack(side='left')
        ttk.Button(row1, text='Desglosar', command=self._run_voraz).pack(side='left', padx=8)
        self.voraz_result = ttk.Label(body, text='', background='white', foreground='#276749')
        self.voraz_result.pack(anchor='w', pady=(0, 16))

        # --- DP ---
        ttk.Label(body, text='2. Programación dinámica – Reposición óptima (mochila 0/1)',
                  background='white', font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Label(
            body,
            text='Dado un presupuesto, elige productos de stock bajo que maximicen la ganancia. O(n·W).',
            background='white', foreground='#607089'
        ).pack(anchor='w', pady=(2, 6))
        row2 = ttk.Frame(body, style='Card.TFrame')
        row2.pack(anchor='w', pady=(0, 14))
        self.budget_var = tk.StringVar(value='50')
        ttk.Entry(row2, textvariable=self.budget_var, width=12).pack(side='left')
        ttk.Button(row2, text='Optimizar reposición',
                   command=self._run_dp).pack(side='left', padx=8)
        self.dp_result = ttk.Label(body, text='', background='white', foreground='#276749',
                                   justify='left')
        self.dp_result.pack(anchor='w', pady=(0, 16))

        # --- Monte Carlo ---
        ttk.Label(body, text='3. Algoritmo probabilista – Monte Carlo (demanda)',
                  background='white', font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Label(
            body,
            text='Simula demanda futura y estima probabilidad de quiebre de stock. O(s·n).',
            background='white', foreground='#607089'
        ).pack(anchor='w', pady=(2, 6))
        ttk.Button(body, text='Ejecutar simulación (500 iteraciones)',
                   command=self._run_montecarlo).pack(anchor='w', pady=(0, 6))
        self.mc_result = ttk.Label(body, text='', background='white', foreground='#276749',
                                   justify='left')
        self.mc_result.pack(anchor='w', pady=(0, 16))

        # --- Recursión / categorías ---
        ttk.Label(body, text='4. Recursividad – Agrupar por categoría',
                  background='white', font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Button(body, text='Agrupar productos recursivamente',
                   command=self._run_recursion).pack(anchor='w', pady=(4, 6))
        self.rec_result = ttk.Label(body, text='', background='white', foreground='#276749',
                                    justify='left')
        self.rec_result.pack(anchor='w', pady=(0, 16))

        # --- Complejidad espacial ---
        ttk.Label(body, text='5. Complejidad espacial – Memoria estática vs dinámica',
                  background='white', font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Label(
            body,
            text='Mide la memoria del carrito y del inventario. Estática O(1), dinámica O(n + k).',
            background='white', foreground='#607089'
        ).pack(anchor='w', pady=(2, 6))
        ttk.Button(body, text='Analizar memoria',
                   command=self._run_espacial).pack(anchor='w', pady=(0, 6))
        self.esp_result = ttk.Label(body, text='', background='white', foreground='#276749',
                                    justify='left')
        self.esp_result.pack(anchor='w', pady=(0, 16))

        # --- Backtracking ---
        ttk.Label(body, text='6. Backtracking – Combinación de productos para un cambio',
                  background='white', font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Label(
            body,
            text='Dado un crédito (producto devuelto), prueba combinaciones de productos con stock y '
                 'retrocede cuando se pasa del crédito. Busca el total más cercano sin superarlo. '
                 'Complejidad O((m+1)^n) con poda.',
            background='white', foreground='#607089', wraplength=700, justify='left'
        ).pack(anchor='w', pady=(2, 6))
        self._wrap_labels.append(body.pack_slaves()[-1])
        row6 = ttk.Frame(body, style='Card.TFrame')
        row6.pack(anchor='w', pady=(0, 6))
        self.bt_var = tk.StringVar(value='12.00')
        ttk.Label(row6, text='Crédito S/:', background='white').pack(side='left')
        ttk.Entry(row6, textvariable=self.bt_var, width=10).pack(side='left', padx=8)
        ttk.Button(row6, text='Buscar combinación',
                   command=self._run_backtracking).pack(side='left')
        self.bt_result = ttk.Label(body, text='', background='white', foreground='#276749',
                                   justify='left')
        self.bt_result.pack(anchor='w', pady=(0, 16))

        # --- Algoritmos paralelos ---
        ttk.Label(body, text='7. Algoritmos paralelos – Speed-up, eficiencia y overhead',
                  background='white', font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Label(
            body,
            text='Compara el reporte del panel en versión secuencial vs 2 hilos. S = t(n)/t(n,p), E = S/p.',
            background='white', foreground='#607089'
        ).pack(anchor='w', pady=(2, 6))
        ttk.Button(body, text='Ejecutar benchmark paralelo',
                   command=self._run_paralelo).pack(anchor='w', pady=(0, 6))
        self.par_result = ttk.Label(body, text='', background='white', foreground='#276749',
                                    justify='left')
        self.par_result.pack(anchor='w')
        self._wrap_labels += [self.dp_result, self.mc_result, self.rec_result,
                              self.esp_result, self.par_result, self.bt_result]

    def _run_backtracking(self):
        try:
            credito = float(self.bt_var.get())
            if credito <= 0:
                raise ValueError
        except ValueError:
            return messagebox.showwarning('Backtracking', 'Ingresa un crédito válido (> 0).')
        cands = [dict(p) for p in self.db.list_products() if p['stock'] > 0]
        res = backtracking_cambio(cands, credito)
        if not res['items']:
            self.bt_result.config(text='No hay combinación posible con el stock disponible.')
            return
        lineas = [f"  • {i['qty']} × {i['name']} (S/ {i['price']:.2f})" for i in res['items']]
        self.bt_result.config(text=(
            f"Mejor combinación para S/ {credito:.2f}:\n" + "\n".join(lineas) +
            f"\nTotal S/ {res['total']:.2f} · Diferencia S/ {res['diferencia']:.2f} · "
            f"Nodos explorados: {res['nodos']}"))

    def _run_espacial(self):
        try:
            rep = complejidad_espacial.reporte_completo(self.cart, self.db.list_products())
            est, din = rep['estatica'], rep['dinamica']
            texto = (
                f"Estática: {est['total_bytes']} bytes ({est['total_kb']} KB) — O(1)\n"
                f"Carrito: {din['carrito']['items']} ítem(s), {din['carrito']['kb']} KB — {din['carrito']['complejidad']}\n"
                f"Inventario: {din['inventario']['productos']} producto(s), {din['inventario']['kb']} KB — {din['inventario']['complejidad']}\n"
                f"Caché de búsqueda binaria: {din['cache_busqueda_binaria']['kb']} KB — {din['cache_busqueda_binaria']['complejidad']}\n"
                f"Dinámica total: {din['total_kb']} KB — {din['complejidad_total']}"
            )
            self.esp_result.config(text=texto)
        except Exception as e:
            self.esp_result.config(text=f"Error: {e}")

    def _run_paralelo(self):
        try:
            m = algoritmos_paralelos.ejecutar_benchmark_paralelo(self.db, None)
            self.par_result.config(text="\n".join(m.notas))
        except Exception as e:
            self.par_result.config(text=f"Error: {e}")

    def _run_voraz(self):
        try:
            from algorithms import desglosar_vuelto, formatear_desglose
            monto = float(self.vuelto_var.get())
            d = desglosar_vuelto(monto)
            self.voraz_result.config(text=f"→ {formatear_desglose(d)}")
        except Exception as e:
            self.voraz_result.config(text=f"Error: {e}")

    def _run_dp(self):
        try:
            presupuesto = float(self.budget_var.get())
            res = self.db.sugerir_reposicion(presupuesto)
            if not res['selected']:
                self.dp_result.config(text=res['message'])
                return
            lineas = [f"• {s['name']} (costo {self.money(s['cost'])}, ganancia {self.money(s['profit'])})"
                      for s in res['selected']]
            texto = (
                f"{res['message']}\n"
                f"Costo total: {self.money(res['total_cost'])} | "
                f"Ganancia potencial: {self.money(res['total_profit'])}\n"
                + "\n".join(lineas)
            )
            self.dp_result.config(text=texto)
        except Exception as e:
            self.dp_result.config(text=f"Error: {e}")

    def _run_montecarlo(self):
        try:
            res = self.db.simular_demanda(dias=30, simulaciones=500)
            lineas = [
                f"• {p['name']}: stock={p['stock']:g}, P(quiebre)={p['prob_quiebre']:.1%}, "
                f"demanda media={p['demanda_media']}"
                for p in res['productos'][:8]
            ]
            self.mc_result.config(
                text=res['message'] + "\n" + "\n".join(lineas)
            )
        except Exception as e:
            self.mc_result.config(text=f"Error: {e}")

    def _run_recursion(self):
        try:
            grupos = self.db.agrupar_por_categoria()
            lineas = [f"• {cat}: {len(items)} producto(s)" for cat, items in grupos.items()]
            self.rec_result.config(text="\n".join(lineas) or "Sin productos")
        except Exception as e:
            self.rec_result.config(text=f"Error: {e}")

    def seed_catalog(self):
        n = self.db.seed_catalog_15()
        if n:
            messagebox.showinfo(
                'Catálogo', f'Se agregaron {n} productos (3 por categoría: Bebidas, Lácteos, '
                'Snacks y Dulces, Cuidado Personal, Cereales y Panadería).')
        else:
            messagebox.showinfo('Catálogo', 'Los 15 productos ya estaban cargados.')
        self.show_dashboard()

    def seed_demo(self):
        if self.db.seed_demo():
            messagebox.showinfo('Datos demo', 'Se cargaron productos de ejemplo.')
            self.show_dashboard()
        else:
            messagebox.showinfo('Datos demo', 'Ya existen productos. No se realizaron cambios.')


if __name__ == '__main__':
    app = StoreApp()
    app.mainloop()
