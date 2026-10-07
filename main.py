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
from algorithms import formatear_desglose, generar_reporte_background
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
            ('💵  Caja', self.show_cash),
            ('🧠  Algoritmos', self.show_algorithms),
        ]:
            b = tk.Button(
                sidebar, text=text, command=cmd, bg='#172033', fg='#dbe6f5',
                activebackground='#243653', activeforeground='white', bd=0,
                anchor='w', font=('Segoe UI', 11), padx=20, pady=13, cursor='hand2'
            )
            b.pack(fill='x')
        tk.Frame(sidebar, bg='#2b3b55', height=1).pack(fill='x', padx=18, pady=18)
        tk.Button(
            sidebar, text='Cargar datos demo', command=self.seed_demo,
            bg='#243653', fg='white', activebackground='#314664',
            activeforeground='white', bd=0, font=('Segoe UI', 9), padx=12, pady=8
        ).pack(fill='x', padx=16)
        tk.Label(
            sidebar, text='Base local SQLite\nDatos guardados en tu PC',
            bg='#172033', fg='#8090a8', font=('Segoe UI', 8), justify='left'
        ).pack(side='bottom', anchor='w', padx=18, pady=18)
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
        pan = ttk.Panedwindow(self.content, orient='horizontal')
        pan.pack(fill='both', expand=True)
        left = ttk.Frame(pan, style='Card.TFrame', padding=14)
        right = ttk.Frame(pan, style='Card.TFrame', padding=14)
        pan.add(left, weight=3)
        pan.add(right, weight=2)

        searchrow = ttk.Frame(left, style='Card.TFrame')
        searchrow.pack(fill='x')
        ttk.Label(searchrow, text='Buscar:', background='white').pack(side='left')
        self.sale_search = tk.StringVar()
        e = ttk.Entry(searchrow, textvariable=self.sale_search)
        e.pack(side='left', fill='x', expand=True, padx=8)
        e.bind('<KeyRelease>', lambda _: self.refresh_sale_products())
        ttk.Button(searchrow, text='Actualizar',
                   command=self.refresh_sale_products).pack(side='left')
        ttk.Button(searchrow, text='Buscar por código (binaria)',
                   command=self.binary_search_dialog).pack(side='left', padx=(6, 0))

        cols = ('codigo', 'producto', 'stock', 'precio')
        self.sale_tree = ttk.Treeview(left, columns=cols, show='headings', height=16)
        for c, t, w in [
            ('codigo', 'Código', 90), ('producto', 'Producto', 260),
            ('stock', 'Stock', 75), ('precio', 'Precio', 90)
        ]:
            self.sale_tree.heading(c, text=t)
            self.sale_tree.column(c, width=w, anchor='center' if c != 'producto' else 'w')
        self.sale_tree.pack(fill='both', expand=True, pady=12)
        self.sale_tree.bind('<Double-1>', lambda _: self.add_selected_to_cart())

        addrow = ttk.Frame(left, style='Card.TFrame')
        addrow.pack(fill='x')
        ttk.Label(addrow, text='Cantidad:', background='white').pack(side='left')
        self.sale_qty = tk.DoubleVar(value=1)
        ttk.Entry(addrow, textvariable=self.sale_qty, width=8).pack(side='left', padx=8)
        ttk.Button(addrow, text='Agregar al carrito', style='Primary.TButton',
                   command=self.add_selected_to_cart).pack(side='left')

        ttk.Label(right, text='Carrito', background='white',
                  font=('Segoe UI', 14, 'bold')).pack(anchor='w')

        # --- Zona inferior fija (siempre visible) ---
        bottom = ttk.Frame(right, style='Card.TFrame')
        bottom.pack(side='bottom', fill='x')

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
        ttk.Button(right, text='Quitar seleccionado',
                   command=self.remove_cart).pack(anchor='e')

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
        w.geometry('420x620')
        w.resizable(False, False)
        w.transient(self)
        w.configure(bg='white')
        w.grab_set()

        # Contenedor principal
        outer = tk.Frame(w, bg='white', padx=24, pady=18)
        outer.pack(fill='both', expand=True)

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
        items_frame = tk.Frame(outer, bg='white')
        items_frame.pack(fill='x')
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

        # --- Botones ---
        btns = tk.Frame(outer, bg='white')
        btns.pack(fill='x', pady=(16, 0))

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

        # Centrar la ventana
        w.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - w.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - w.winfo_height()) // 2
        w.geometry(f'+{x}+{y}')

    # ------------------------------------------------------------------
    # WAREHOUSE
    # ------------------------------------------------------------------
    def show_warehouse(self):
        self.clear()
        self.header('Almacén', 'Administra productos, precios y existencias.')
        top = ttk.Frame(self.content)
        top.pack(fill='x')
        self.wh_search = tk.StringVar()
        ttk.Entry(top, textvariable=self.wh_search).pack(side='left', fill='x', expand=True)
        self.wh_search.trace_add('write', lambda *_: self.refresh_products())
        ttk.Button(top, text='Nuevo producto', style='Primary.TButton',
                   command=self.product_form).pack(side='left', padx=(10, 0))
        ttk.Button(top, text='Entrada / salida',
                   command=self.stock_dialog).pack(side='left', padx=(8, 0))
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
        actions = ttk.Frame(self.content)
        actions.pack(fill='x', pady=(10, 0))
        ttk.Button(actions, text='Editar', command=self.edit_product).pack(side='left')
        ttk.Button(actions, text='Eliminar',
                   command=self.delete_product).pack(side='left', padx=8)
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
        w.geometry('480x520')
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
        w.geometry('420x330')
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
        w.geometry('420x300')
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

    # ------------------------------------------------------------------
    # ALGORITMOS DEL CURSO (demostración T2)
    # ------------------------------------------------------------------
    def show_algorithms(self):
        self.clear()
        self.header(
            'Algoritmos del curso',
            'Voraz · Divide y vencerás · Recursividad · Programación dinámica · Monte Carlo · Paralelismo'
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
        canvas.bind('<Configure>', lambda e: canvas.itemconfigure(win, width=e.width))
        canvas.bind('<Enter>', lambda e: canvas.bind_all(
            '<MouseWheel>', lambda ev: canvas.yview_scroll(int(-ev.delta / 120), 'units')))
        canvas.bind('<Leave>', lambda e: canvas.unbind_all('<MouseWheel>'))

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
                                   wraplength=900, justify='left')
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
                                   wraplength=900, justify='left')
        self.mc_result.pack(anchor='w', pady=(0, 16))

        # --- Recursión / categorías ---
        ttk.Label(body, text='4. Recursividad – Agrupar por categoría',
                  background='white', font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Button(body, text='Agrupar productos recursivamente',
                   command=self._run_recursion).pack(anchor='w', pady=(4, 6))
        self.rec_result = ttk.Label(body, text='', background='white', foreground='#276749',
                                    wraplength=900, justify='left')
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
                                    wraplength=900, justify='left')
        self.esp_result.pack(anchor='w', pady=(0, 16))

        # --- Algoritmos paralelos ---
        ttk.Label(body, text='6. Algoritmos paralelos – Speed-up, eficiencia y overhead',
                  background='white', font=('Segoe UI', 12, 'bold')).pack(anchor='w')
        ttk.Label(
            body,
            text='Compara el reporte del panel en versión secuencial vs 2 hilos. S = t(n)/t(n,p), E = S/p.',
            background='white', foreground='#607089'
        ).pack(anchor='w', pady=(2, 6))
        ttk.Button(body, text='Ejecutar benchmark paralelo',
                   command=self._run_paralelo).pack(anchor='w', pady=(0, 6))
        self.par_result = ttk.Label(body, text='', background='white', foreground='#276749',
                                    wraplength=900, justify='left')
        self.par_result.pack(anchor='w')

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

    def seed_demo(self):
        if self.db.seed_demo():
            messagebox.showinfo('Datos demo', 'Se cargaron productos de ejemplo.')
            self.show_dashboard()
        else:
            messagebox.showinfo('Datos demo', 'Ya existen productos. No se realizaron cambios.')


if __name__ == '__main__':
    app = StoreApp()
    app.mainloop()
