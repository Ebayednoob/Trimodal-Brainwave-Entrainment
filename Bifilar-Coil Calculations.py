import tkinter as tk
from tkinter import ttk, messagebox
import math
import numpy as np

class CoilCalculator:
    def __init__(self, root):
        self.root = root
        self.root.title("Bifilar Coil Analyzer")
        self.root.geometry("1100x600")
        self.zoom_level = 1.0  # Add zoom control

        # Constants
        self.MU0 = 4e-7 * math.pi  # H/m (permeability of free space)
        self.EPSILON0 = 8.854e-12  # F/m (vacuum permittivity)
        self.awg_data = {
            16: {"resist": 0.01317, "dia": 1.29e-3},
            18: {"resist": 0.02095, "dia": 1.02e-3},
            20: {"resist": 0.03364, "dia": 0.812e-3}
        }

        self.create_widgets()
        self.canvas_setup()

    def canvas_setup(self):
        self.canvas = tk.Canvas(self.viz_frame, width=400, height=400, bg="white")
        self.canvas.pack(pady=10)
        self.scale_factor = 1
        self.center_x = 200
        self.center_y = 200

    def create_widgets(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left Panel (Input/Results)
        left_panel = ttk.Frame(main_frame)
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=10, pady=10)

        # Input Frame
        input_frame = ttk.LabelFrame(left_panel, text="Parameters")
        input_frame.pack(fill=tk.X, pady=5)

        parameters = [
            ("Windings:", "turns"),
            ("Voltage (V):", "voltage"),
            ("Duty Cycle (%):", "duty"),
            ("Frequency (Hz):", "freq")
        ]
        
        for text, name in parameters:
            row = ttk.Frame(input_frame)
            ttk.Label(row, text=text).pack(side=tk.LEFT)
            entry = ttk.Entry(row, width=10)
            entry.pack(side=tk.RIGHT)
            setattr(self, name, entry)
            row.pack(fill=tk.X, pady=2)

        ttk.Label(input_frame, text="AWG:").pack(anchor=tk.W)
        self.awg = ttk.Combobox(input_frame, values=[16, 18, 20], state="readonly")
        self.awg.pack(fill=tk.X)
        self.awg.current(0)

        # Buttons
        btn_frame = ttk.Frame(input_frame)
        ttk.Button(btn_frame, text="Calculate", command=self.calculate).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Clear", command=self.clear).pack(side=tk.LEFT, padx=5)
        btn_frame.pack(pady=10)

        # Results Frame
        result_frame = ttk.LabelFrame(left_panel, text="Analysis Results")
        result_frame.pack(fill=tk.BOTH, expand=True)

        self.results = []
        labels = [
            "Wire Length:", "DC Resistance:", 
            "Max Current:", "Pulsed Current:",
            "Magnetic Field:", "Pulse Interval:",
            "Inductance:", "Capacitance:",
            "Resonant Frequency:"
        ]
        
        for text in labels:
            row = ttk.Frame(result_frame)
            ttk.Label(row, text=text).pack(side=tk.LEFT)
            result_label = ttk.Label(row, text="", width=15)
            result_label.pack(side=tk.RIGHT)
            self.results.append(result_label)
            row.pack(fill=tk.X, pady=2)

        # Visualization Frame
        self.viz_frame = ttk.LabelFrame(main_frame, text="Coil Visualization")
        self.viz_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Add zoom controls
        zoom_frame = ttk.Frame(self.viz_frame)
        zoom_frame.pack(pady=5)
        ttk.Button(zoom_frame, text="+", command=lambda: self.adjust_zoom(1.2)).pack(side=tk.LEFT)
        ttk.Button(zoom_frame, text="-", command=lambda: self.adjust_zoom(0.8)).pack(side=tk.LEFT)
        ttk.Button(zoom_frame, text="Reset", command=lambda: self.reset_zoom()).pack(side=tk.LEFT)

    def clear(self):
        # Clear input fields
        self.turns.delete(0, tk.END)
        self.voltage.delete(0, tk.END)
        self.duty.delete(0, tk.END)
        self.freq.delete(0, tk.END)
        
        # Clear results
        for label in self.results:
            label.config(text="")
        
        # Clear canvas
        self.canvas.delete("all")

    def calculate_resonance(self, L, C):
        if L <= 0 or C <= 0:
            return 0
        try:
            return 1 / (2 * math.pi * math.sqrt(L * C))
        except:
            return 0

    def calculate(self):
        try:
            # Get input values
            turns = int(self.turns.get())
            awg = int(self.awg.get())
            voltage = float(self.voltage.get())
            duty = float(self.duty.get()) / 100
            freq = float(self.freq.get())
            
            # Get wire properties
            wire = self.awg_data[awg]
            wire_dia = wire['dia']
            resistivity = wire['resist']
            
            # Geometry calculations
            inner_radius = wire_dia * 2
            wire_spacing = wire_dia * 1.1  # Spacing between turns
            avg_radius = inner_radius + (turns * wire_spacing) / 2
            wire_length = 2 * 2 * math.pi * avg_radius * turns  # Total for both wires
            
            # Electrical calculations
            resistance = wire_length * resistivity
            current = voltage / resistance if resistance > 0 else 0
            avg_current = current * duty
            
            # Magnetic field calculation
            B_center = (self.MU0 * turns * avg_current) / (2 * avg_radius)
            
            # Inductance calculation (Wheeler's approximation)
            outer_radius = inner_radius + turns * wire_spacing
            L = (self.MU0 * turns**2 * avg_radius**2) / (2 * avg_radius + 2.8*(outer_radius - inner_radius))
            
            # Capacitance calculation (parallel wire)
            wire_separation = wire_dia * 1.2
            a = wire_dia/2  # Wire radius
            d = wire_separation
            C = 0
            if d > 2*a:
                C_per_meter = (math.pi * self.EPSILON0) / math.acosh(d/(2*a))
                C = C_per_meter * (2 * math.pi * avg_radius * turns)
            
            # Resonant frequency
            f_res = self.calculate_resonance(L, C)
            
            # Update results
            results = [
                f"{wire_length:.2f} m", f"{resistance:.2f} Ω",
                f"{current:.2f} A", f"{avg_current:.2f} A RMS",
                f"{B_center*1e6:.2f} µT", f"{1/freq:.2e} s",
                f"{L*1e6:.2f} µH" if L < 1 else f"{L:.2f} H",
                f"{C*1e12:.2f} pF" if C < 1e-9 else f"{C*1e9:.2f} nF",
                f"{f_res/1e6:.2f} MHz" if f_res > 1e6 else f"{f_res/1e3:.2f} kHz"
            ]
            
            for label, result in zip(self.results, results):
                label.config(text=result)
            
            # Draw coil visualization
            self.draw_coil(turns, wire_dia, inner_radius, wire_spacing)
            
        except Exception as e:
            messagebox.showerror("Input Error", f"Invalid input values:\n{str(e)}")

    def adjust_zoom(self, factor):
        self.zoom_level *= factor
        self.calculate()  # Redraw with new zoom

    def reset_zoom(self):
        self.zoom_level = 1.0
        self.calculate()

    def draw_coil(self, turns, wire_dia, inner_radius, wire_spacing):
        self.canvas.delete("all")
        max_radius = inner_radius + turns * wire_spacing

        # Enhanced scaling logic
        base_scale = 0.18 if max_radius > 0 else 1  # 400/2200 ~ 0.18 for 400px canvas
        self.scale_factor = base_scale * self.zoom_level * 1000  # Scale up for metric units

        # Add automatic padding
        padding = 20 * (1/self.scale_factor)

        # For bifilar, separation is slightly more than wire diameter
        wire_separation = wire_dia * 1.2

        points1, points2 = [], []
        theta_step = 0.2  # Smoother rendering

        for theta in np.arange(0, 2 * math.pi * turns, theta_step):
            r = inner_radius + wire_spacing * theta / (2 * math.pi)

            # Calculate normal vector
            dx = -r * math.sin(theta) + (wire_spacing/(2*math.pi)) * math.cos(theta)
            dy = r * math.cos(theta) + (wire_spacing/(2*math.pi)) * math.sin(theta)
            norm = math.hypot(dx, dy) if (dx or dy) else 1

            # Calculate offset points with padding
            offset = (wire_separation/2 + padding)
            x = r * math.cos(theta)
            y = r * math.sin(theta)

            points1.append((
                self.center_x + (x + (dx/norm) * offset) * self.scale_factor,
                self.center_y + (y + (dy/norm) * offset) * self.scale_factor
            ))

            points2.append((
                self.center_x + (x - (dx/norm) * offset) * self.scale_factor,
                self.center_y + (y - (dy/norm) * offset) * self.scale_factor
            ))

        # Draw with thicker lines
        self.draw_spiral(points1, "blue", width=3)
        self.draw_spiral(points2, "red", width=3)

    def draw_spiral(self, points, color, width=2):
        for i in range(1, len(points)):
            self.canvas.create_line(*points[i-1], *points[i],
                                   fill=color, width=width, smooth=True)

    def generate_theta(self, turns):
        max_theta = 2 * math.pi * turns
        step = 0.1  # Radian step size
        theta = 0
        while theta <= max_theta:
            yield theta
            theta += step

if __name__ == "__main__":
    root = tk.Tk()
    app = CoilCalculator(root)
    root.mainloop()
