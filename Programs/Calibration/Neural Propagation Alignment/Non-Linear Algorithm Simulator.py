import tkinter as tk
from tkinter import ttk
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Ellipse # Import Ellipse
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# --- Activation Functions ---
def relu(x):
    """Rectified Linear Unit."""
    return np.maximum(0, x)

def sigmoid(x):
    """Sigmoid activation function."""
    return 1 / (1 + np.exp(-x))

def tanh(x):
    """Hyperbolic Tangent activation function."""
    return np.tanh(x)

def swish(x, beta=1.0):
    """Swish activation function."""
    return x * sigmoid(beta * x)

def gelu(x):
    """Gaussian Error Linear Unit (approximation)."""
    return 0.5 * x * (1 + np.tanh(np.sqrt(2 / np.pi) * (x + 0.044715 * np.power(x, 3))))

ACTIVATION_FUNCTIONS = {
    "ReLU": relu,
    "Sigmoid": sigmoid,
    "Tanh": tanh,
    "Swish": swish,
    "GELU": gelu,
}

class SignalProcessorApp:
    def __init__(self, root):
        """
        Initialize the application.
        Sets up the main window, variables, UI components, and initial plots.
        """
        self.root = root
        self.root.title("Signal Processor GUI")
        self.root.geometry("1250x800") 

        # --- Style ---
        style = ttk.Style()
        style.theme_use('clam')

        # --- Variables ---
        self.waveform_type = tk.StringVar(value="Sine")
        self.amplitude = tk.DoubleVar(value=1.0)
        self.frequency = tk.DoubleVar(value=5.0) # Hz
        self.duration = tk.DoubleVar(value=200.0) # ms
        self.phase_angle = tk.DoubleVar(value=0.0) # Degrees
        self.duty_cycle = tk.DoubleVar(value=0.5) # For square wave
        self.selected_algorithm = tk.StringVar(value="ReLU")
        self.num_points = 500

        # --- Main Frames ---
        plot_area_frame = ttk.Frame(self.root, padding="5")
        plot_area_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        row1_frame = ttk.Frame(plot_area_frame)
        row1_frame.pack(side=tk.TOP, fill=tk.X, expand=False, pady=2)

        row2_frame = ttk.Frame(plot_area_frame)
        row2_frame.pack(side=tk.TOP, fill=tk.X, expand=False, pady=2)
        
        controls_frame = ttk.Labelframe(self.root, text="Signal Generator Controls", padding="10")
        controls_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(10,5))

        algo_frame = ttk.Labelframe(self.root, text="Modification Algorithm", padding="10")
        algo_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        # --- Plot Setup ---
        main_signal_plot_width = 7 * 1.1
        main_signal_plot_height = 2.8 * 1.1
        phase_plot_size = 2.2 * 1.1 
        fft_polar_plot_width = main_signal_plot_width * 0.8

        main_plot_figsize = (main_signal_plot_width, main_signal_plot_height)
        phase_plot_figsize = (phase_plot_size, phase_plot_size)
        fft_polar_plot_figsize = (fft_polar_plot_width, main_signal_plot_height)

        # --- Row 1 Plots ---
        self.fig_input = plt.Figure(figsize=main_plot_figsize)
        self.ax_input = self.fig_input.add_subplot(111)
        self.ax_input.set_title("Input Signal")
        self.ax_input.set_xlabel("Time (s)")
        self.ax_input.set_ylabel("Amplitude (V)")
        self.ax_input.grid(True)
        self.canvas_input = FigureCanvasTkAgg(self.fig_input, master=row1_frame)
        self.canvas_input_widget = self.canvas_input.get_tk_widget()
        self.canvas_input_widget.pack(side=tk.LEFT, fill=tk.NONE, expand=False, padx=5)

        self.fig_input_phase = plt.Figure(figsize=phase_plot_figsize)
        # For Ellipse, we don't strictly need polar projection if we manually position,
        # but polar makes axis labels (0, 90, 180, 270) easier.
        self.ax_input_phase = self.fig_input_phase.add_subplot(111, projection='polar')
        self.ax_input_phase.set_title("Input Phase", fontsize=10)
        self.ax_input_phase.set_rticks([]) 
        self.ax_input_phase.set_thetagrids(np.arange(0, 360, 90)) # Ensure 0, 90, 180, 270 are shown
        self.ax_input_phase.set_xticklabels(['0°', '90°', '180°', '270°'])
        self.ax_input_phase.set_rlim(0, 0.6) # Adjust radial limit to fit ellipse
        self.canvas_input_phase = FigureCanvasTkAgg(self.fig_input_phase, master=row1_frame)
        self.canvas_input_phase_widget = self.canvas_input_phase.get_tk_widget()
        self.canvas_input_phase_widget.pack(side=tk.LEFT, fill=tk.NONE, expand=False, padx=5)

        # --- Row 2 Plots ---
        self.fig_output = plt.Figure(figsize=main_plot_figsize)
        self.ax_output = self.fig_output.add_subplot(111)
        self.ax_output.set_title("Output Signal (Post-Modification)")
        self.ax_output.set_xlabel("Time (s)")
        self.ax_output.set_ylabel("Transformed Value")
        self.ax_output.grid(True)
        self.canvas_output = FigureCanvasTkAgg(self.fig_output, master=row2_frame)
        self.canvas_output_widget = self.canvas_output.get_tk_widget()
        self.canvas_output_widget.pack(side=tk.LEFT, fill=tk.NONE, expand=False, padx=5)

        self.fig_output_phase = plt.Figure(figsize=phase_plot_figsize)
        self.ax_output_phase = self.fig_output_phase.add_subplot(111, projection='polar')
        self.ax_output_phase.set_title("Output Phase (Ref.)", fontsize=10)
        self.ax_output_phase.set_rticks([])
        self.ax_output_phase.set_thetagrids(np.arange(0, 360, 90))
        self.ax_output_phase.set_xticklabels(['0°', '90°', '180°', '270°'])
        self.ax_output_phase.set_rlim(0, 0.6) # Adjust radial limit
        self.canvas_output_phase = FigureCanvasTkAgg(self.fig_output_phase, master=row2_frame)
        self.canvas_output_phase_widget = self.canvas_output_phase.get_tk_widget()
        self.canvas_output_phase_widget.pack(side=tk.LEFT, fill=tk.NONE, expand=False, padx=5)

        self.fig_fft_polar = plt.Figure(figsize=fft_polar_plot_figsize)
        self.ax_fft_polar = self.fig_fft_polar.add_subplot(111, projection='polar')
        self.ax_fft_polar.set_title("FFT Polar Plot", fontsize=11)
        self.canvas_fft_polar = FigureCanvasTkAgg(self.fig_fft_polar, master=row2_frame)
        self.canvas_fft_polar_widget = self.canvas_fft_polar.get_tk_widget()
        self.canvas_fft_polar_widget.pack(side=tk.LEFT, fill=tk.NONE, expand=False, padx=5)

        self.fig_input.tight_layout(pad=0.5)
        self.fig_input_phase.tight_layout(pad=0.3)
        self.fig_output.tight_layout(pad=0.5)
        self.fig_output_phase.tight_layout(pad=0.3)
        self.fig_fft_polar.tight_layout(pad=0.5)

        # --- Control Panel Widgets ---
        controls_frame.columnconfigure(1, weight=1)
        controls_frame.columnconfigure(3, weight=1)
        controls_frame.columnconfigure(5, weight=1)
        # controls_frame.columnconfigure(7, weight=1) # Removed as not strictly needed with current layout

        ttk.Label(controls_frame, text="Waveform:").grid(row=0, column=0, padx=5, pady=3, sticky="w")
        waveform_menu = ttk.Combobox(controls_frame, textvariable=self.waveform_type,
                                     values=["Sine", "Square", "Sawtooth"], state="readonly", width=10)
        waveform_menu.grid(row=0, column=1, padx=5, pady=3, sticky="ew")
        waveform_menu.bind("<<ComboboxSelected>>", self.toggle_duty_cycle)

        self.duty_cycle_label = ttk.Label(controls_frame, text="Duty Cycle:")
        self.duty_cycle_label.grid(row=0, column=2, padx=5, pady=3, sticky="w")
        self.duty_cycle_scale = ttk.Scale(controls_frame, from_=0.0, to=1.0, variable=self.duty_cycle,
                                     orient=tk.HORIZONTAL, command=lambda s: self.duty_cycle.set(round(float(s),2)))
        self.duty_cycle_scale.grid(row=0, column=3, padx=5, pady=3, sticky="ew")
        self.duty_cycle_entry = ttk.Entry(controls_frame, textvariable=self.duty_cycle, width=5)
        self.duty_cycle_entry.grid(row=0, column=4, padx=(0,10), pady=3)
        self.toggle_duty_cycle() 

        ttk.Label(controls_frame, text="Amplitude (V):").grid(row=1, column=0, padx=5, pady=3, sticky="w")
        amplitude_scale = ttk.Scale(controls_frame, from_=0.1, to=10.0, variable=self.amplitude,
                                   orient=tk.HORIZONTAL, command=lambda s: self.amplitude.set(round(float(s),2)))
        amplitude_scale.grid(row=1, column=1, padx=5, pady=3, sticky="ew")
        amplitude_entry = ttk.Entry(controls_frame, textvariable=self.amplitude, width=5)
        amplitude_entry.grid(row=1, column=2, padx=(0,10), pady=3)

        ttk.Label(controls_frame, text="Frequency (Hz):").grid(row=1, column=3, padx=5, pady=3, sticky="w")
        frequency_scale = ttk.Scale(controls_frame, from_=1.0, to=100.0, variable=self.frequency,
                                   orient=tk.HORIZONTAL, command=lambda s: self.frequency.set(round(float(s),1)))
        frequency_scale.grid(row=1, column=4, padx=5, pady=3, sticky="ew")
        frequency_entry = ttk.Entry(controls_frame, textvariable=self.frequency, width=5)
        frequency_entry.grid(row=1, column=5, padx=(0,10), pady=3)

        ttk.Label(controls_frame, text="Duration (ms):").grid(row=2, column=0, padx=5, pady=3, sticky="w")
        duration_scale = ttk.Scale(controls_frame, from_=10.0, to=1000.0, variable=self.duration,
                                  orient=tk.HORIZONTAL, command=lambda s: self.duration.set(round(float(s),0)))
        duration_scale.grid(row=2, column=1, padx=5, pady=3, sticky="ew")
        duration_entry = ttk.Entry(controls_frame, textvariable=self.duration, width=5)
        duration_entry.grid(row=2, column=2, padx=(0,10), pady=3)

        ttk.Label(controls_frame, text="Phase (deg):").grid(row=2, column=3, padx=5, pady=3, sticky="w")
        phase_scale = ttk.Scale(controls_frame, from_=0.0, to=360.0, variable=self.phase_angle,
                                  orient=tk.HORIZONTAL, command=lambda s: self.phase_angle.set(round(float(s),0)))
        phase_scale.grid(row=2, column=4, padx=5, pady=3, sticky="ew")
        phase_entry = ttk.Entry(controls_frame, textvariable=self.phase_angle, width=5)
        phase_entry.grid(row=2, column=5, padx=(0,10), pady=3)

        # --- Algorithm Selection Widgets ---
        ttk.Label(algo_frame, text="Select Algorithm:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        algo_menu = ttk.Combobox(algo_frame, textvariable=self.selected_algorithm,
                                 values=list(ACTIVATION_FUNCTIONS.keys()), state="readonly", width=15)
        algo_menu.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        
        update_button = ttk.Button(algo_frame, text="Generate & Update Signals", command=self.update_plots)
        update_button.grid(row=0, column=2, padx=20, pady=10, sticky="e")
        
        algo_frame.columnconfigure(1, weight=1)
        algo_frame.columnconfigure(2, weight=0)

        self.update_plots()

    def toggle_duty_cycle(self, event=None):
        if self.waveform_type.get() == "Square":
            self.duty_cycle_label.config(state=tk.NORMAL)
            self.duty_cycle_scale.config(state=tk.NORMAL)
            self.duty_cycle_entry.config(state=tk.NORMAL)
        else:
            self.duty_cycle_label.config(state=tk.DISABLED)
            self.duty_cycle_scale.config(state=tk.DISABLED)
            self.duty_cycle_entry.config(state=tk.DISABLED)

    def generate_input_signal(self):
        amp = self.amplitude.get()
        freq = self.frequency.get()
        dur_s = self.duration.get() / 1000.0
        phase_deg = self.phase_angle.get()
        phase_rad = np.deg2rad(phase_deg)
        duty = self.duty_cycle.get()
        wave_type = self.waveform_type.get()
        t_orig = np.linspace(0, dur_s, self.num_points, endpoint=False)
        signal = np.zeros_like(t_orig)
        if freq <= 0: return t_orig, signal 
        period = 1.0 / freq
        time_shift = (phase_deg / 360.0) * period
        if wave_type == "Sine":
            signal = amp * np.sin(2 * np.pi * freq * t_orig + phase_rad)
        elif wave_type == "Square":
            time_in_period_shifted = (t_orig - time_shift) % period
            signal = np.where(time_in_period_shifted < duty * period, amp, -amp)
        elif wave_type == "Sawtooth":
            signal = amp * ( ((t_orig - time_shift) % period) / period * 2 - 1)
        return t_orig, signal

    def apply_modification(self, input_signal):
        algo_name = self.selected_algorithm.get()
        if algo_name in ACTIVATION_FUNCTIONS:
            return ACTIVATION_FUNCTIONS[algo_name](input_signal)
        return input_signal

    def calculate_fft_polar_data(self, t, y_input):
        if len(y_input) < 2 or len(t) < 2: return np.array([]), np.array([])
        dt = t[1] - t[0] if len(t) > 1 else 1.0
        if dt <= 0:
            if len(t) > 1 and t[-1] > t[0]: dt = (t[-1] - t[0]) / (len(t) -1)
            else: return np.array([]), np.array([])
        N = len(y_input)
        yf_complex = np.fft.fft(y_input)
        magnitudes = np.abs(yf_complex[:N//2]) / N 
        angles = np.angle(yf_complex[:N//2])
        if N > 0: magnitudes[0] = np.abs(yf_complex[0])/N
        return magnitudes, angles

    def update_plots(self):
        t, y_input = self.generate_input_signal()
        y_output = self.apply_modification(y_input)
        fft_magnitudes, fft_angles = self.calculate_fft_polar_data(t, y_input)
        current_input_phase_deg = self.phase_angle.get() # Degrees for Ellipse angle

        # Update Input Plot
        self.ax_input.clear()
        self.ax_input.plot(t, y_input, color='dodgerblue')
        self.ax_input.set_title("Input Signal")
        self.ax_input.set_xlabel("Time (s)")
        self.ax_input.set_ylabel("Amplitude (V)")
        self.ax_input.grid(True)
        if y_input.any():
             y_margin = (np.max(y_input) - np.min(y_input)) * 0.1
             if y_margin == 0: y_margin = np.abs(np.max(y_input) * 0.1) if np.max(y_input) != 0 else 0.1
             if y_margin == 0: y_margin = 0.1
             self.ax_input.set_ylim(np.min(y_input) - y_margin, np.max(y_input) + y_margin)
        else: self.ax_input.set_ylim(-1, 1)
        self.ax_input.set_xlim(0, self.duration.get() / 1000.0)
        self.fig_input.tight_layout(pad=0.5)
        self.canvas_input.draw()

        # Update Input Phase Reference Plot with Ellipse
        self.ax_input_phase.clear()
        # Ellipse parameters: center (0,0 for polar), width, height, angle (degrees)
        # Width and height are in data coordinates. For polar, this means radial units.
        # We set rlim to 0.6, so ellipse width 1.0 would fill diameter. Let's use smaller.
        ellipse_width = 0.8 # Major axis length in radial units
        ellipse_height = 0.25 # Minor axis length in radial units
        # The Ellipse center in polar is (angle, radius), but for drawing the patch,
        # it's better to use Cartesian equivalent (0,0) and rotate.
        # However, for polar axes, patches are added directly.
        # The angle of the ellipse is the phase angle.
        # Note: Ellipse angle is counterclockwise from positive x-axis.
        # Polar plot's 0 angle is to the right.
        input_ellipse = Ellipse(xy=(0,0), width=ellipse_width, height=ellipse_height, 
                                angle=current_input_phase_deg, facecolor='dodgerblue', alpha=0.6)
        self.ax_input_phase.add_patch(input_ellipse)
        self.ax_input_phase.set_rticks([])
        self.ax_input_phase.set_thetagrids(np.arange(0, 360, 90))
        self.ax_input_phase.set_xticklabels(['0°', '90°', '180°', '270°'], fontsize=8)
        self.ax_input_phase.set_title("Input Phase", fontsize=10)
        self.ax_input_phase.set_rlim(0, 0.5) # Adjusted rlim to make ellipse visible
        self.fig_input_phase.tight_layout(pad=0.3)
        self.canvas_input_phase.draw()

        # Update Output Plot
        self.ax_output.clear()
        self.ax_output.plot(t, y_output, color='orangered')
        self.ax_output.set_title(f"Output Signal ({self.selected_algorithm.get()})")
        self.ax_output.set_xlabel("Time (s)")
        self.ax_output.set_ylabel("Transformed Value")
        self.ax_output.grid(True)
        if y_output.any():
            y_margin = (np.max(y_output) - np.min(y_output)) * 0.1
            if y_margin == 0: y_margin = np.abs(np.max(y_output) * 0.1) if np.max(y_output) != 0 else 0.1
            if y_margin == 0: y_margin = 0.1
            self.ax_output.set_ylim(np.min(y_output) - y_margin, np.max(y_output) + y_margin)
        else: self.ax_output.set_ylim(-1, 1)
        self.ax_output.set_xlim(0, self.duration.get() / 1000.0)
        self.fig_output.tight_layout(pad=0.5)
        self.canvas_output.draw()
        
        # Update Output Phase Reference Plot with Ellipse (Placeholder)
        self.ax_output_phase.clear()
        # Placeholder: static ellipse or could be linked to some output characteristic
        output_ellipse_angle_deg = 0 # Example: static angle
        output_ellipse = Ellipse(xy=(0,0), width=ellipse_width, height=ellipse_height,
                                 angle=output_ellipse_angle_deg, facecolor='orangered', alpha=0.6, linestyle='--')
        self.ax_output_phase.add_patch(output_ellipse)
        self.ax_output_phase.set_rticks([])
        self.ax_output_phase.set_thetagrids(np.arange(0, 360, 90))
        self.ax_output_phase.set_xticklabels(['0°', '90°', '180°', '270°'], fontsize=8)
        self.ax_output_phase.set_title("Output Phase (Ref.)", fontsize=10)
        self.ax_output_phase.set_rlim(0, 0.5) # Adjusted rlim
        self.fig_output_phase.tight_layout(pad=0.3)
        self.canvas_output_phase.draw()

        # Update FFT Polar Plot
        self.ax_fft_polar.clear()
        if len(fft_magnitudes) > 0 and len(fft_angles) > 0:
            for i in range(len(fft_magnitudes)):
                self.ax_fft_polar.plot([fft_angles[i], fft_angles[i]], [0, fft_magnitudes[i]], marker='o', markersize=3, linestyle='-', color='green', alpha=0.7)
            if fft_magnitudes.any():
                 self.ax_fft_polar.set_rmax(np.max(fft_magnitudes) * 1.1)
            else: self.ax_fft_polar.set_rmax(1)
            self.ax_fft_polar.set_rticks(np.linspace(0, self.ax_fft_polar.get_rmax(), 4))
        else:
            self.ax_fft_polar.set_rmax(1)
            self.ax_fft_polar.set_rticks([0, 0.25, 0.5, 0.75, 1])
        self.ax_fft_polar.set_title("FFT Polar Plot", fontsize=11)
        self.ax_fft_polar.grid(True, linestyle=':', alpha=0.7)
        self.fig_fft_polar.tight_layout(pad=0.5)
        self.canvas_fft_polar.draw()

if __name__ == "__main__":
    main_window = tk.Tk()
    app = SignalProcessorApp(main_window)
    main_window.mainloop()
