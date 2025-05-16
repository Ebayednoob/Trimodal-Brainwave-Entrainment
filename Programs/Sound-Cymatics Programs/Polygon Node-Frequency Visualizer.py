import tkinter as tk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np
from sympy import primerange
import threading
import time

class CymaticsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Advanced Polygon Cymatics Visualizer")
        
        # Set minimum window size to prevent cutoff
        self.root.minsize(1400, 900)
        
        # Default parameters
        self.node_radius = 1.5
        self.phi = (1 + np.sqrt(5)) / 2
        self.zoom_level = 1.0
        self.zoom_factor = 1.2
        self.base_xlim = (-3, 3)
        self.base_ylim = (-3, 3)
        self.show_legend = True
        self.autoscale_active = False
        self.autoscale_thread = None
        self.min_freq = 1
        self.max_freq = 1000
        self.current_freq = 432
        self.step_size = 1
        self.num_nodes = 5
        self.base_freq_enabled = True
        self.node_frequencies = [432] * 12  # Max for dodecagon
        self.speed_of_sound = 343
        self.node_freq_sliders = []
        self.node_freq_entries = []
        
        # Create main container
        self.main_frame = tk.Frame(root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Left side - Graph
        self.graph_frame = tk.Frame(self.main_frame)
        self.graph_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Right side - Controls with scrollbar
        self.control_container = tk.Frame(self.main_frame, width=550)  # 10% wider
        self.control_container.pack(side=tk.RIGHT, fill=tk.Y)
        self.control_container.pack_propagate(False)
        
        # Create canvas and scrollbar for controls
        self.control_canvas = tk.Canvas(self.control_container, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self.control_container, orient="vertical", command=self.control_canvas.yview)
        self.scrollable_frame = tk.Frame(self.control_canvas, padx=15)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.control_canvas.configure(
                scrollregion=self.control_canvas.bbox("all")
            )
        )
        
        self.scrollable_frame_id = self.control_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.control_canvas.bind("<Configure>", self._on_canvas_configure)
        self.control_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.control_canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind mouse wheel for scrolling
        self.scrollable_frame.bind("<Enter>", self._bind_mousewheel)
        self.scrollable_frame.bind("<Leave>", self._unbind_mousewheel)
        
        # Create the graph
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.graph_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Add matplotlib toolbar
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.graph_frame)
        self.toolbar.update()
        self.canvas.get_tk_widget().pack()
        
        # Create UI controls
        self.create_ui()
        self.setup_zoom()
        self.generate_plot()

    def _bind_mousewheel(self, event):
        self.control_canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.control_canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.control_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def _on_canvas_configure(self, event):
        # Set the scrollable_frame width to match the canvas width minus scrollbar
        canvas_width = event.width
        self.control_canvas.itemconfig(self.scrollable_frame_id, width=canvas_width)

    def create_ui(self):
        # Consistent padding values
        padx = 8
        pady = 6
        
        # Base frequency controls
        self.freq_frame = tk.LabelFrame(self.scrollable_frame, text="Frequency Controls")
        self.freq_frame.pack(fill=tk.X, pady=pady, padx=padx)
        
        self.base_freq_var = tk.BooleanVar(value=True)
        self.base_freq_toggle = tk.Checkbutton(self.freq_frame, text="Enable Base Frequency", 
                                             variable=self.base_freq_var, command=self.toggle_base_frequency)
        self.base_freq_toggle.pack(anchor=tk.W, padx=padx)
        
        tk.Label(self.freq_frame, text="Base Frequency (Hz):").pack(anchor=tk.W, padx=padx)
        self.freq_entry = tk.Entry(self.freq_frame)
        self.freq_entry.insert(0, "432")
        self.freq_entry.pack(fill=tk.X, padx=padx, pady=pady)
        
        self.freq_slider_frame = tk.Frame(self.freq_frame)
        self.freq_slider_frame.pack(fill=tk.X, padx=padx, pady=pady)
        
        self.freq_slider = tk.Scale(self.freq_slider_frame, from_=1, to=25000, orient="horizontal", 
                                   command=lambda v: self.freq_entry.delete(0, tk.END) or 
                                   self.freq_entry.insert(0, str(int(float(v)))))
        self.freq_slider.set(432)
        self.freq_slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.freq_apply_button = tk.Button(self.freq_slider_frame, text="Apply", command=self.apply_base_frequency)
        self.freq_apply_button.pack(side=tk.LEFT, padx=padx)

        # Node frequency controls frame
        self.node_freq_control_frame = tk.Frame(self.scrollable_frame)
        self.node_freq_control_frame.pack_forget()  # Start hidden

        # Node controls frame
        self.node_frame = tk.LabelFrame(self.scrollable_frame, text="Node Controls")
        self.node_frame.pack(fill=tk.X, pady=pady, padx=padx)
        
        tk.Label(self.node_frame, text="Node Distance:").pack(side=tk.LEFT, padx=padx)
        self.node_entry = tk.Entry(self.node_frame, width=10)
        self.node_entry.insert(0, str(self.node_radius))
        self.node_entry.pack(side=tk.LEFT, padx=padx)
        
        self.node_button = tk.Button(self.node_frame, text="Apply", command=self.apply_node_distance)
        self.node_button.pack(side=tk.LEFT, padx=padx)

        # Node count control
        self.node_count_frame = tk.Frame(self.node_frame)
        self.node_count_frame.pack(fill=tk.X, pady=pady, padx=padx)
        
        tk.Label(self.node_count_frame, text="Number of Nodes:").pack(side=tk.LEFT, padx=padx)
        self.node_count_var = tk.IntVar(value=self.num_nodes)
        self.node_count_menu = ttk.Combobox(self.node_count_frame, textvariable=self.node_count_var, 
                                          values=list(range(3, 13)), width=4)
        self.node_count_menu.pack(side=tk.LEFT, padx=padx)
        self.node_count_menu.bind("<<ComboboxSelected>>", self.update_node_count)

        # Legend toggle
        self.legend_frame = tk.Frame(self.node_frame)
        self.legend_frame.pack(fill=tk.X, pady=pady, padx=padx)
        
        self.legend_toggle = tk.Button(self.legend_frame, text="Toggle Legend", command=self.toggle_legend)
        self.legend_toggle.pack(padx=padx)

        # Autoscale controls frame
        self.autoscale_frame = tk.LabelFrame(self.scrollable_frame, text="Autoscale Controls")
        self.autoscale_frame.pack(fill=tk.X, pady=pady, padx=padx)

        top_btn_frame = tk.Frame(self.autoscale_frame)
        top_btn_frame.pack(fill=tk.X, padx=padx, pady=(0, pady))
        
        tk.Label(top_btn_frame, text="Autoscale:").pack(side=tk.LEFT, padx=padx)
        self.play_button = tk.Button(top_btn_frame, text="▶", command=self.start_autoscale)
        self.play_button.pack(side=tk.LEFT, padx=2)
        self.pause_button = tk.Button(top_btn_frame, text="⏸", command=self.pause_autoscale)
        self.pause_button.pack(side=tk.LEFT, padx=2)
        self.stop_button = tk.Button(top_btn_frame, text="⏹", command=self.stop_autoscale)
        self.stop_button.pack(side=tk.LEFT, padx=2)
        self.reset_button = tk.Button(top_btn_frame, text="↻", command=self.reset_autoscale)
        self.reset_button.pack(side=tk.LEFT, padx=2)

        self.range_frame = tk.Frame(self.autoscale_frame)
        self.range_frame.pack(fill=tk.X, padx=padx, pady=(0, pady))
        
        tk.Label(self.range_frame, text="Min Freq:").pack(side=tk.LEFT, padx=padx)
        self.min_freq_entry = tk.Entry(self.range_frame, width=8)
        self.min_freq_entry.insert(0, "1")
        self.min_freq_entry.pack(side=tk.LEFT, padx=padx)
        
        tk.Label(self.range_frame, text="Max Freq:").pack(side=tk.LEFT, padx=padx)
        self.max_freq_entry = tk.Entry(self.range_frame, width=8)
        self.max_freq_entry.insert(0, "1000")
        self.max_freq_entry.pack(side=tk.LEFT, padx=padx)
        
        tk.Label(self.range_frame, text="Step:").pack(side=tk.LEFT, padx=padx)
        self.step_entry = tk.Entry(self.range_frame, width=8)
        self.step_entry.insert(0, "1")
        self.step_entry.pack(side=tk.LEFT, padx=padx)

        # Zoom controls frame
        self.zoom_frame = tk.LabelFrame(self.scrollable_frame, text="Zoom Controls")
        self.zoom_frame.pack(fill=tk.X, pady=pady, padx=padx)
        
        self.zoom_in_button = tk.Button(self.zoom_frame, text="Zoom In", command=lambda: self.adjust_zoom(1/self.zoom_factor))
        self.zoom_in_button.pack(side=tk.LEFT, padx=padx)
        
        self.zoom_out_button = tk.Button(self.zoom_frame, text="Zoom Out", command=lambda: self.adjust_zoom(self.zoom_factor))
        self.zoom_out_button.pack(side=tk.LEFT, padx=padx)
        
        self.reset_zoom_button = tk.Button(self.zoom_frame, text="Reset Zoom", command=self.reset_zoom)
        self.reset_zoom_button.pack(side=tk.LEFT, padx=padx)

        # Algorithm selection
        self.alg_frame = tk.LabelFrame(self.scrollable_frame, text="Algorithm Settings")
        self.alg_frame.pack(fill=tk.X, pady=pady, padx=padx)
        tk.Label(self.alg_frame, text="Algorithm:").pack(side=tk.LEFT, padx=padx)
        self.alg_options = [
            "Phi Ratio",
            "Fibonacci Scaling", 
            "Logarithmic Spirals",
            "Prime Number Sequences"
        ]
        self.alg_var = tk.StringVar(value=self.alg_options[0])
        self.alg_menu = ttk.Combobox(self.alg_frame, textvariable=self.alg_var, values=self.alg_options, width=16)
        self.alg_menu.pack(side=tk.LEFT, padx=padx)

        # Wave type selection
        self.wave_frame = tk.Frame(self.alg_frame)
        self.wave_frame.pack(fill=tk.X, pady=pady, padx=padx)
        tk.Label(self.wave_frame, text="Wave Type:").pack(side=tk.LEFT, padx=padx)
        self.wave_type_options = ["Mechanical Wave", "3rd & 5th Order Harmonics"]
        self.wave_type_var = tk.StringVar(value=self.wave_type_options[0])
        self.wave_type_menu = ttk.Combobox(self.wave_frame, textvariable=self.wave_type_var, 
                                         values=self.wave_type_options, width=16)
        self.wave_type_menu.pack(side=tk.LEFT, padx=padx)

        # Plot button
        self.plot_button = tk.Button(self.scrollable_frame, text="Generate Plot", command=self.generate_plot)
        self.plot_button.pack(fill=tk.X, pady=10, padx=padx)

        # Explanation label
        self.explanation = tk.Label(self.scrollable_frame, text="", wraplength=450, justify="left")
        self.explanation.pack(fill=tk.X, pady=10, padx=padx)

    def setup_zoom(self):
        self.pan_active = False
        self.zoom_active = False
        self.xpress = None
        
        # Connect events
        self.canvas.mpl_connect('scroll_event', self.on_scroll)
        self.canvas.mpl_connect('button_press_event', self.on_press)
        self.canvas.mpl_connect('button_release_event', self.on_release)

    def on_scroll(self, event):
        if event.inaxes != self.ax:
            return
        
        # Get current limits
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        
        # Get mouse position in data coordinates
        xdata = event.xdata
        ydata = event.ydata
        
        # Zoom factor
        if event.button == 'up':
            scale_factor = 1/self.zoom_factor
        elif event.button == 'down':
            scale_factor = self.zoom_factor
        else:
            return
        
        # Apply zoom
        new_width = (xlim[1] - xlim[0]) * scale_factor
        new_height = (ylim[1] - ylim[0]) * scale_factor
        
        self.ax.set_xlim([xdata - new_width/2, xdata + new_width/2])
        self.ax.set_ylim([ydata - new_height/2, ydata + new_height/2])
        self.canvas.draw_idle()

    def on_press(self, event):
        if event.inaxes != self.ax:
            return
        if event.button == 2:  # Middle mouse button
            self.pan_active = True
            self.xpress = event.xdata
            self.ypress = event.ydata

    def on_release(self, event):
        if self.pan_active:
            dx = event.xdata - self.xpress
            dy = event.ydata - self.ypress
            
            xlim = self.ax.get_xlim()
            ylim = self.ax.get_ylim()
            
            self.ax.set_xlim([xlim[0] - dx, xlim[1] - dx])
            self.ax.set_ylim([ylim[0] - dy, ylim[1] - dy])
            self.canvas.draw_idle()
        
        self.pan_active = False
        self.xpress = None

    def adjust_zoom(self, factor):
        # Get current center
        xlim = self.ax.get_xlim()
        ylim = self.ax.get_ylim()
        x_center = (xlim[0] + xlim[1]) / 2
        y_center = (ylim[0] + ylim[1]) / 2
        
        # Calculate new width and height
        new_width = (xlim[1] - xlim[0]) * factor
        new_height = (ylim[1] - ylim[0]) * factor
        
        # Apply new limits
        self.ax.set_xlim([x_center - new_width/2, x_center + new_width/2])
        self.ax.set_ylim([y_center - new_height/2, y_center + new_height/2])
        self.canvas.draw_idle()

    def reset_zoom(self):
        self.ax.set_xlim(self.base_xlim)
        self.ax.set_ylim(self.base_ylim)
        self.canvas.draw_idle()

    def apply_node_distance(self):
        try:
            new_radius = float(self.node_entry.get())
            if new_radius > 0:
                self.node_radius = new_radius
                self.generate_plot()
        except ValueError:
            pass

    def polygon_points(self, radius, num_nodes, center=(0, 0)):
        points = []
        for i in range(num_nodes):
            angle = 2 * np.pi * i / num_nodes - np.pi / 2
            x = center[0] + radius * np.cos(angle)
            y = center[1] + radius * np.sin(angle)
            points.append((x, y))
        return points

    def draw_wavefronts(self, center, wavelength, color='blue', label=None):
        circle = plt.Circle(center, wavelength, color=color, fill=False, 
                          linestyle='--', label=label)
        self.ax.add_artist(circle)

    def generate_plot(self):
        self.ax.clear()
        
        # Update title based on number of nodes
        shape_names = {
            3: "Triangle",
            4: "Square",
            5: "Pentagon",
            6: "Hexagon",
            7: "Heptagon",
            8: "Octagon",
            9: "Nonagon",
            10: "Decagon",
            11: "Hendecagon",
            12: "Dodecagon"
        }
        shape_name = shape_names.get(self.num_nodes, f"{self.num_nodes}-gon")
        
        points = self.polygon_points(self.node_radius, self.num_nodes)

        # Draw polygon
        for i in range(self.num_nodes):
            next_i = (i + 1) % self.num_nodes
            self.ax.plot([points[i][0], points[next_i][0]], 
                        [points[i][1], points[next_i][1]], 
                        color='black', linewidth=1)
            self.ax.plot(points[i][0], points[i][1], 'ro')
            
            # Draw wavefronts for each node if base frequency is disabled
            if not self.base_freq_enabled:
                try:
                    node_freq = self.node_frequencies[i]
                    wavelength = self.speed_of_sound / node_freq
                    self.draw_wavefronts(points[i], wavelength, 
                                       color=plt.cm.tab10(i % 10),
                                       label=f'Node {i+1}: {node_freq}Hz')
                except ValueError:
                    pass

        # Draw base frequency wavefronts if enabled
        if self.base_freq_enabled:
            try:
                base_freq = float(self.freq_entry.get())
                wavelength = self.speed_of_sound / base_freq
                self.ax.set_title(f'{shape_name} Cymatics @ {base_freq:.1f} Hz\nAlgorithm: {self.alg_var.get()}')
                
                algorithm = self.alg_var.get()
                wave_type = self.wave_type_var.get()
                
                if wave_type == "3rd & 5th Order Harmonics":
                    for order, color in zip([3, 5], ['blue', 'green']):
                        harmonic_wavelength = wavelength / order
                        for pt in points:
                            self.draw_wavefronts(pt, harmonic_wavelength, color=color,
                                               label=f'{order}rd order (λ/{order})')
                else:
                    if algorithm == "Phi Ratio":
                        multipliers = [1, self.phi, 1/self.phi]
                        colors = ['blue', 'green', 'orange']
                        labels = ['λ', 'Φλ', '1/Φλ']
                        for mult, color, label in zip(multipliers, colors, labels):
                            for pt in points:
                                self.draw_wavefronts(pt, wavelength * mult, 
                                                   color=color, label=label)
                    elif algorithm == "Fibonacci Scaling":
                        fibs = [1, 2, 3, 5]
                        for i, f in enumerate(fibs):
                            scale = (self.phi ** (i+1)) / 2
                            for pt in points:
                                self.draw_wavefronts(pt, wavelength * scale, 
                                                   color=plt.cm.tab10(i % 10),
                                                   label=f'Fib {f} (φ^{i+1}/2)')
                    elif algorithm == "Logarithmic Spirals":
                        scales = [0.5, 1.0, 1.5]
                        for s, color in zip(scales, ['blue', 'green', 'orange']):
                            log_scale = np.exp(s) / np.exp(1)
                            for pt in points:
                                self.draw_wavefronts(pt, wavelength * log_scale, 
                                                   color=color,
                                                   label=f'Log scale {s:.1f}')
                    elif algorithm == "Prime Number Sequences":
                        primes = list(primerange(1, 8))
                        for p, color in zip(primes, ['blue', 'green', 'orange', 'red']):
                            for pt in points:
                                self.draw_wavefronts(pt, wavelength * (p/2), 
                                                   color=color,
                                                   label=f'Prime {p} (λ×{p}/2)')
            except ValueError:
                pass
        else:
            self.ax.set_title(f'{shape_name} Cymatics\nAlgorithm: {self.alg_var.get()}')

        # Compute inter-node distance
        d = np.linalg.norm(np.array(points[0]) - np.array(points[1]))

        # Update explanation text
        algorithm = self.alg_var.get()
        wave_type = self.wave_type_var.get()
        
        if not self.base_freq_enabled:
            freq_text = "\n".join([f"Node {i+1}: {self.node_frequencies[i]} Hz" 
                                 for i in range(self.num_nodes)])
            explanation_text = (
                f"Showing {shape_name} with {self.num_nodes} nodes\n"
                f"Individual node frequencies:\n{freq_text}\n"
                f"Node distance: {d:.3f} m\n"
                f"Zoom: Use mouse wheel or buttons to zoom in/out"
            )
        elif wave_type == "3rd & 5th Order Harmonics":
            explanation_text = (
                f"Showing {shape_name} with {self.num_nodes} nodes\n"
                f"3rd and 5th order harmonics of {base_freq:.1f} Hz\n"
                f"3rd harmonic: {base_freq*3:.1f} Hz (λ/3 = {wavelength/3:.3f} m)\n"
                f"5th harmonic: {base_freq*5:.1f} Hz (λ/5 = {wavelength/5:.3f} m)\n"
                f"Node distance: {d:.3f} m\n"
                f"Zoom: Use mouse wheel or buttons to zoom in/out"
            )
        else:
            if algorithm == "Phi Ratio":
                explanation_text = (
                    f"Showing {shape_name} with {self.num_nodes} nodes\n"
                    f"Base frequency: {base_freq:.1f} Hz\n"
                    f"Golden ratio (φ) scaling:\n"
                    f"λ = {wavelength:.3f} m, Φλ ≈ {wavelength * self.phi:.3f} m\n"
                    f"Node distance: {d:.3f} m\n"
                    f"Zoom: Use mouse wheel or buttons to zoom in/out"
                )
            elif algorithm == "Fibonacci Scaling":
                explanation_text = (
                    f"Showing {shape_name} with {self.num_nodes} nodes\n"
                    f"Base frequency: {base_freq:.1f} Hz\n"
                    f"Fibonacci/golden ratio scaling:\n"
                    f"Using φ^n scaling factors (φ ≈ 1.618)\n"
                    f"Base wavelength: {wavelength:.3f} m\n"
                    f"Node distance: {d:.3f} m\n"
                    f"Zoom: Use mouse wheel or buttons to zoom in/out"
                )
            elif algorithm == "Logarithmic Spirals":
                explanation_text = (
                    f"Showing {shape_name} with {self.num_nodes} nodes\n"
                    f"Base frequency: {base_freq:.1f} Hz\n"
                    f"Logarithmic scaling:\n"
                    f"Using e^k scaling factors (normalized)\n"
                    f"Base wavelength: {wavelength:.3f} m\n"
                    f"Node distance: {d:.3f} m\n"
                    f"Zoom: Use mouse wheel or buttons to zoom in/out"
                )
            elif algorithm == "Prime Number Sequences":
                explanation_text = (
                    f"Showing {shape_name} with {self.num_nodes} nodes\n"
                    f"Base frequency: {base_freq:.1f} Hz\n"
                    f"Prime number scaling:\n"
                    f"Using first few primes as multipliers\n"
                    f"Base wavelength: {wavelength:.3f} m\n"
                    f"Node distance: {d:.3f} m\n"
                    f"Zoom: Use mouse wheel or buttons to zoom in/out"
                )
            
        self.explanation.config(text=explanation_text)

        self.ax.set_aspect('equal')
        if self.show_legend:
            self.ax.legend(loc='upper right')
        self.ax.set_xlim(self.base_xlim)
        self.ax.set_ylim(self.base_ylim)
        self.ax.axis('off')

        self.canvas.draw()

    def apply_base_frequency(self):
        try:
            frequency = float(self.freq_entry.get())
            self.freq_slider.set(frequency)
            if not self.base_freq_enabled:
                for i in range(self.num_nodes):
                    self.node_frequencies[i] = frequency
                    if i < len(self.node_freq_entries):
                        self.node_freq_entries[i].delete(0, tk.END)
                        self.node_freq_entries[i].insert(0, str(frequency))
                    if i < len(self.node_freq_sliders):
                        self.node_freq_sliders[i].set(frequency)
            self.generate_plot()
        except ValueError:
            pass

    def create_node_frequency_controls(self):
        # Clear existing controls
        for widget in self.node_freq_control_frame.winfo_children():
            widget.destroy()
        
        self.node_freq_sliders = []
        self.node_freq_entries = []
            
        if not self.base_freq_enabled:
            tk.Label(self.node_freq_control_frame, text="Node Frequencies:").pack(anchor=tk.W)
            
            # Create controls for current number of nodes
            for i in range(self.num_nodes):
                frame = tk.Frame(self.node_freq_control_frame)
                frame.pack(fill=tk.X, pady=2)
                
                tk.Label(frame, text=f"Node {i+1}:").pack(side=tk.LEFT)
                
                entry = tk.Entry(frame, width=8)
                entry.insert(0, str(self.node_frequencies[i]))
                entry.pack(side=tk.LEFT, padx=5)
                entry.bind("<KeyRelease>", lambda e, idx=i: self.update_node_freq_entry(idx, e.widget.get()))
                self.node_freq_entries.append(entry)
                
                # Scale for finer control
                scale = tk.Scale(frame, from_=1, to=25000, orient="horizontal", 
                                command=lambda v, idx=i: self.update_node_freq_slider(idx, v))
                scale.set(self.node_frequencies[i])
                scale.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self.node_freq_sliders.append(scale)
                
                # Apply button for each node
                apply_btn = tk.Button(frame, text="✓", command=lambda idx=i: self.apply_node_frequency(idx))
                apply_btn.pack(side=tk.LEFT, padx=2)

    def update_node_freq_entry(self, node_idx, value):
        try:
            freq = float(value)
            self.node_frequencies[node_idx] = freq
            if node_idx < len(self.node_freq_sliders):
                self.node_freq_sliders[node_idx].set(freq)
            self.generate_plot()
        except ValueError:
            pass

    def update_node_freq_slider(self, node_idx, value):
        self.node_frequencies[node_idx] = float(value)
        if node_idx < len(self.node_freq_entries):
            self.node_freq_entries[node_idx].delete(0, tk.END)
            self.node_freq_entries[node_idx].insert(0, str(int(float(value))))
        self.generate_plot()

    def apply_node_frequency(self, node_idx):
        try:
            freq = float(self.node_freq_entries[node_idx].get())
            self.node_frequencies[node_idx] = freq
            if node_idx < len(self.node_freq_sliders):
                self.node_freq_sliders[node_idx].set(freq)
            self.generate_plot()
        except ValueError:
            pass

    def toggle_base_frequency(self):
        self.base_freq_enabled = self.base_freq_var.get()
        
        if self.base_freq_enabled:
            # Hide node frequency controls
            self.node_freq_control_frame.pack_forget()
            
            # Show base frequency controls
            self.freq_frame.pack(pady=5, fill=tk.X)
            self.freq_slider_frame.pack(fill=tk.X)
            
            # Reset all node frequencies to current base frequency
            try:
                base_freq = float(self.freq_entry.get())
                for i in range(len(self.node_frequencies)):
                    self.node_frequencies[i] = base_freq
            except ValueError:
                pass
        else:
            # Show node frequency controls
            self.create_node_frequency_controls()
            self.node_freq_control_frame.pack(pady=5, fill=tk.X)
            
            # Hide base frequency slider (keep entry visible)
            self.freq_slider_frame.pack_forget()
        
        self.generate_plot()

    def update_node_count(self, event=None):
        self.num_nodes = self.node_count_var.get()
        # When reducing node count, preserve frequencies for remaining nodes
        # When increasing, set new nodes to current base frequency
        try:
            base_freq = float(self.freq_entry.get())
            for i in range(len(self.node_frequencies)):
                if i >= self.num_nodes:
                    self.node_frequencies[i] = base_freq
        except ValueError:
            pass
        self.create_node_frequency_controls()
        self.generate_plot()

    def toggle_legend(self):
        self.show_legend = not self.show_legend
        self.generate_plot()

    def start_autoscale(self):
        if self.autoscale_active:
            return
            
        try:
            self.min_freq = float(self.min_freq_entry.get())
            self.max_freq = float(self.max_freq_entry.get())
            self.step_size = float(self.step_entry.get())
            self.current_freq = self.min_freq
        except ValueError:
            return
            
        self.autoscale_active = True
        self.autoscale_thread = threading.Thread(target=self.run_autoscale, daemon=True)
        self.autoscale_thread.start()

    def pause_autoscale(self):
        self.autoscale_active = False

    def stop_autoscale(self):
        self.autoscale_active = False
        self.current_freq = self.min_freq
        self.update_frequency(self.current_freq)

    def reset_autoscale(self):
        self.autoscale_active = False
        self.current_freq = self.min_freq
        self.update_frequency(self.current_freq)
        self.reset_zoom()

    def run_autoscale(self):
        direction = 1  # 1 for increasing, -1 for decreasing
        while self.autoscale_active:
            self.current_freq += self.step_size * direction
            
            if self.current_freq >= self.max_freq:
                direction = -1
                self.current_freq = self.max_freq
            elif self.current_freq <= self.min_freq:
                direction = 1
                self.current_freq = self.min_freq
                
            self.update_frequency(self.current_freq)
            time.sleep(0.05)

    def update_frequency(self, freq):
        self.freq_entry.delete(0, tk.END)
        self.freq_entry.insert(0, str(freq))
        self.freq_slider.set(freq)
        if not self.base_freq_enabled:
            for i in range(self.num_nodes):
                self.node_frequencies[i] = freq
                if i < len(self.node_freq_entries):
                    self.node_freq_entries[i].delete(0, tk.END)
                    self.node_freq_entries[i].insert(0, str(freq))
                if i < len(self.node_freq_sliders):
                    self.node_freq_sliders[i].set(freq)
        self.generate_plot()

if __name__ == "__main__":
    root = tk.Tk()
    app = CymaticsApp(root)
    root.mainloop()