import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import random
import math
from pylsl import StreamInfo, StreamOutlet

# --- Configuration ---
STREAM_NAME = 'SimulatedEEG_GUI_Hemispheric_Ctrl'
STREAM_TYPE = 'EEG'
BASE_CHANNEL_NAMES = ["Delta", "Theta", "Alpha", "Beta", "Gamma"]
CHANNEL_COUNT = len(BASE_CHANNEL_NAMES) * 2
SAMPLE_RATE = 20
CHANNEL_FORMAT = 'float32'
UNIQUE_ID = 'my_simulated_eeg_gui_hemi_ctrl_12345'

# Initial Default Values for Controls
DEFAULT_FREQUENCIES = {
    "Delta": 0.5, "Theta": 1.5, "Alpha": 2.5, "Beta": 4.0, "Gamma": 1.0,
}
FREQ_SLIDER_RANGES = {
    "Delta": (0.1, 3.0), "Theta": (1.0, 7.0), "Alpha": (2.0, 12.0),
    "Beta": (3.0, 30.0), "Gamma": (0.1, 2.0), # Gamma is amplitude scale
}

# Hemispheric Oscillation Cycle Settings (in milliseconds)
DEFAULT_SLOW_OSC_PERIOD_MS = 300.0
DEFAULT_FAST_OSC_PERIOD_MS = 35.0

SLOW_OSC_RANGE_MS = (100.0, 500.0)
FAST_OSC_RANGE_MS = (20.0, 100.0)

# --- Theme Definitions ---
THEMES = {
    "Light": {
        "bg": "#F0F0F0", "fg": "#000000", "input_bg": "#FFFFFF",
        "button_bg": "#E0E0E0", "button_fg": "#000000",
        "log_bg": "#FFFFFF", "log_fg": "#000000",
        "accent": "#0078D7", "frame_bg": "#F5F5F5",
        "brain_outline": "#555555", 
        "brain_base_fill": "#D0D0D0", # Light grey for inactive band parts
        "band_colors_active": { 
            "Delta": "#00008B",  # DarkBlue
            "Theta": "#4682B4",  # SteelBlue
            "Alpha": "#20B2AA",  # LightSeaGreen
            "Beta":  "#FFD700",  # Gold
            "Gamma": "#FF4500"   # OrangeRed
        },
        "band_label_color": "#000000" 
    },
    "Matrix": { # This is our Dark Theme
        "bg": "#000000", "fg": "#00FF00", "input_bg": "#0D0D0D",
        "button_bg": "#003300", "button_fg": "#00FF00",
        "log_bg": "#050505", "log_fg": "#33FF33",
        "accent": "#00CC00", "frame_bg": "#0A0A0A",
        "brain_outline": "#000000", 
        "brain_base_fill": "#000000", # Make bands black
        "band_colors_active": { 
            "Delta": "#006400",  
            "Theta": "#228B22",  
            "Alpha": "#32CD32",  
            "Beta":  "#7FFF00",  
            "Gamma": "#ADFF2F"   
        },
        "band_label_color": "#90EE90" 
    }
}

# --- Signal Generator Classes ---
class BaseSignalGenerator:
    def __init__(self, initial_frequency, band_name, speed_category):
        self.frequency = initial_frequency
        self.band_name = band_name
        self.speed_category = speed_category

    def generate(self, t):
        raise NotImplementedError

    def set_frequency(self, freq):
        self.frequency = freq

class DeltaSignal(BaseSignalGenerator):
    def generate(self, t):
        return 0.5 + 0.5 * math.sin(2 * math.pi * self.frequency * t)

class ThetaSignal(BaseSignalGenerator):
    def generate(self, t):
        return 0.5 + 0.5 * math.sin(2 * math.pi * self.frequency * t)

class AlphaSignal(BaseSignalGenerator):
    def generate(self, t):
        default_freq = DEFAULT_FREQUENCIES.get(self.band_name, self.frequency if self.frequency > 0 else 1)
        return 0.6 + 0.4 * math.sin(2 * math.pi * self.frequency * t) + random.uniform(-0.05, 0.05) * (self.frequency / default_freq if default_freq > 0 else 1)

class BetaSignal(BaseSignalGenerator):
    def generate(self, t):
        return 0.4 + 0.3 * math.sin(2 * math.pi * self.frequency * t) + \
               0.1 * math.sin(2 * math.pi * self.frequency * 2 * t)

class GammaSignal(BaseSignalGenerator):
    def generate(self, t):
        return random.uniform(0.1, 0.5) * self.frequency

SIGNAL_GENERATOR_CLASSES = {
    "Delta": DeltaSignal, "Theta": ThetaSignal, "Alpha": AlphaSignal,
    "Beta": BetaSignal, "Gamma": GammaSignal
}
SLOW_BANDS = ["Delta", "Theta", "Alpha"]

class SimulatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LSL EEG Simulator Control Panel")
        self.root.geometry("750x950") 

        self.is_simulating = False
        self.simulation_thread = None
        self.lsl_outlet = None
        self.start_time = 0

        self.signal_objects = []
        for band_name in BASE_CHANNEL_NAMES:
            cls = SIGNAL_GENERATOR_CLASSES[band_name]
            initial_val = DEFAULT_FREQUENCIES[band_name]
            speed_cat = "slow" if band_name in SLOW_BANDS else "fast"
            self.signal_objects.append(cls(initial_val, band_name, speed_cat))

        self.slow_osc_period_ms_var = tk.DoubleVar(value=DEFAULT_SLOW_OSC_PERIOD_MS)
        self.fast_osc_period_ms_var = tk.DoubleVar(value=DEFAULT_FAST_OSC_PERIOD_MS)
        self.band_control_vars = {} 
        
        self.dark_theme_enabled_var = tk.BooleanVar(value=False) # Default to Light theme
        self.active_theme_colors = THEMES["Light"] # Initialize with default theme colors

        self.style = ttk.Style()
        self.apply_theme() # Apply theme BEFORE UI setup
        
        self.band_shapes = {'left': {}, 'right': {}}
        self.setup_ui() # UI elements will use the initially applied theme

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log_message(f"Simulator GUI initialized with { 'Dark' if self.dark_theme_enabled_var.get() else 'Light' } theme.")
        
        if len(self.signal_objects) != len(BASE_CHANNEL_NAMES):
            error_msg = "Mismatch in signal objects and base channel names."
            self.log_message(f"ERROR: {error_msg}")
            messagebox.showerror("Configuration Error", error_msg)
            if hasattr(self, 'toggle_button'):
                self.toggle_button.config(state=tk.DISABLED)

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _rgb_to_hex(self, rgb_color):
        return f'#{rgb_color[0]:02x}{rgb_color[1]:02x}{rgb_color[2]:02x}'

    def _interpolate_color(self, value, inactive_hex, active_hex):
        value = max(0, min(1, value)) 
        inactive_rgb = self._hex_to_rgb(inactive_hex)
        active_rgb = self._hex_to_rgb(active_hex)
        inter_rgb = [int(inactive_rgb[i] + (active_rgb[i] - inactive_rgb[i]) * value) for i in range(3)]
        return self._rgb_to_hex(tuple(inter_rgb))

    def _get_band_heatmap_color(self, band_name, activity_value):
        inactive_color = self.active_theme_colors["brain_base_fill"]
        active_color = self.active_theme_colors["band_colors_active"].get(band_name, "#808080") # Default to grey
        return self._interpolate_color(activity_value, inactive_color, active_color)

    def setup_ui(self):
        self.main_app_frame = ttk.Frame(self.root, style='App.TFrame')
        self.main_app_frame.pack(expand=True, fill=tk.BOTH)
        
        top_bar_frame = ttk.Frame(self.main_app_frame, padding=(10,5), style='Controls.TFrame')
        top_bar_frame.pack(fill=tk.X, side=tk.TOP)
        self.title_label = ttk.Label(top_bar_frame, text="LSL EEG Simulator", font=("Helvetica", 16, "bold"), style='Header.TLabel')
        self.title_label.pack(side=tk.LEFT, padx=(0, 20))
        self.status_var = tk.StringVar(value="Status: Not Simulating")
        self.status_label = ttk.Label(top_bar_frame, textvariable=self.status_var, font=("Helvetica", 10), style='Status.TLabel')
        self.status_label.pack(side=tk.LEFT, expand=True, fill=tk.X)
        
        self.theme_checkbox = ttk.Checkbutton(top_bar_frame, text="Dark Theme", variable=self.dark_theme_enabled_var, command=self.toggle_theme, style='Controls.TCheckbutton')
        self.theme_checkbox.pack(side=tk.RIGHT, padx=10)

        controls_area_frame = ttk.Frame(self.main_app_frame, padding=10, style='App.TFrame')
        controls_area_frame.pack(fill=tk.X, side=tk.TOP, pady=5)

        self.toggle_button = ttk.Button(controls_area_frame, text="Start Simulation", command=self.toggle_simulation, style='Large.TButton')
        self.toggle_button.pack(pady=(5, 15), ipady=5)

        global_settings_frame = ttk.LabelFrame(controls_area_frame, text="Global Settings", padding=10, style='Controls.TLabelframe')
        global_settings_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(global_settings_frame, text="Slow Hemi. Osc. Period (ms):", style='Controls.TLabel').grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.slow_osc_scale = ttk.Scale(global_settings_frame, from_=SLOW_OSC_RANGE_MS[0], to=SLOW_OSC_RANGE_MS[1], variable=self.slow_osc_period_ms_var, orient=tk.HORIZONTAL, length=200, style='Controls.TScale', command=lambda v: self.update_osc_period_display('slow'))
        self.slow_osc_scale.grid(row=0, column=1, sticky=tk.EW, padx=5)
        self.slow_osc_display_label = ttk.Label(global_settings_frame, text=f"{self.slow_osc_period_ms_var.get():.0f}ms", style='Controls.TLabel')
        self.slow_osc_display_label.grid(row=0, column=2, padx=5)

        ttk.Label(global_settings_frame, text="Fast Hemi. Osc. Period (ms):", style='Controls.TLabel').grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.fast_osc_scale = ttk.Scale(global_settings_frame, from_=FAST_OSC_RANGE_MS[0], to=FAST_OSC_RANGE_MS[1], variable=self.fast_osc_period_ms_var, orient=tk.HORIZONTAL, length=200, style='Controls.TScale', command=lambda v: self.update_osc_period_display('fast'))
        self.fast_osc_scale.grid(row=1, column=1, sticky=tk.EW, padx=5)
        self.fast_osc_display_label = ttk.Label(global_settings_frame, text=f"{self.fast_osc_period_ms_var.get():.0f}ms", style='Controls.TLabel')
        self.fast_osc_display_label.grid(row=1, column=2, padx=5)
        global_settings_frame.columnconfigure(1, weight=1)

        bands_frame = ttk.LabelFrame(controls_area_frame, text="Brainwave Band Controls", padding=10, style='Controls.TLabelframe')
        bands_frame.pack(fill=tk.X, expand=False, pady=10) 

        for i, band_name in enumerate(BASE_CHANNEL_NAMES):
            band_label_text = f"{band_name} Freq (Hz):" if band_name != "Gamma" else f"{band_name} Amp Scale:"
            ttk.Label(bands_frame, text=band_label_text, style='Controls.TLabel').grid(row=i, column=0, sticky=tk.W, padx=5, pady=8)
            var = tk.DoubleVar(value=DEFAULT_FREQUENCIES[band_name])
            self.band_control_vars[band_name] = var
            min_val, max_val = FREQ_SLIDER_RANGES[band_name]
            display_label = ttk.Label(bands_frame, text=f"{var.get():.1f}", width=5, style='Controls.TLabel')
            display_label.grid(row=i, column=2, padx=5, pady=2)
            scale = ttk.Scale(bands_frame, from_=min_val, to=max_val, variable=var, orient=tk.HORIZONTAL, length=300, style='Controls.TScale', command=lambda v, bn=band_name, lbl=display_label: self.update_band_param(v, bn, lbl))
            scale.grid(row=i, column=1, sticky=tk.EW, padx=5, pady=2)
            self.update_band_param(var.get(), band_name, display_label)
        bands_frame.columnconfigure(1, weight=1) 

        brain_viz_frame = ttk.LabelFrame(self.main_app_frame, text="Brain Activity Visualizer", padding=10, style='Controls.TLabelframe')
        brain_viz_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.brain_canvas = tk.Canvas(brain_viz_frame, bg=self.active_theme_colors["bg"], highlightthickness=0)
        self.brain_canvas.pack(fill=tk.BOTH, expand=True)
        self.brain_canvas.bind("<Configure>", self._draw_brain_initial) 
        
        log_outer_frame = ttk.Frame(self.main_app_frame, style='App.TFrame', height=150) 
        log_outer_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=(0,10)) 
        log_outer_frame.pack_propagate(False) 

        log_frame = ttk.LabelFrame(log_outer_frame, text="Log", padding=(5,5,5,5), style='Controls.TLabelframe')
        log_frame.pack(expand=True, fill=tk.BOTH)
        self.log_text_area = scrolledtext.ScrolledText(log_frame, height=5, wrap=tk.WORD, state=tk.DISABLED) 
        self.log_text_area.pack(expand=True, fill=tk.BOTH, padx=2, pady=2)
        self.log_text_area.config(background=self.active_theme_colors["log_bg"], foreground=self.active_theme_colors["log_fg"], insertbackground=self.active_theme_colors["fg"], selectbackground=self.active_theme_colors["accent"], selectforeground=self.active_theme_colors["log_bg"])

    def _draw_brain_initial(self, event=None):
        self.brain_canvas.delete("all") 
        width = self.brain_canvas.winfo_width()
        height = self.brain_canvas.winfo_height()
        
        if width < 100 or height < 150: return

        padding = 20; top_padding_for_labels = 30
        canvas_drawable_height = height - top_padding_for_labels
        hemi_width = (width - 3 * padding) / 2
        hemi_height = canvas_drawable_height - 2 * padding
        
        outline_color = self.active_theme_colors["brain_outline"]
        base_fill = self.active_theme_colors["brain_base_fill"]

        y0_ovals = padding + top_padding_for_labels
        x0_l_oval = padding; x1_l_oval = padding + hemi_width
        y1_ovals = y0_ovals + hemi_height
        self.brain_canvas.create_oval(x0_l_oval, y0_ovals, x1_l_oval, y1_ovals, outline=outline_color, width=1, dash=(2,2))
        x0_r_oval = padding + hemi_width + padding; x1_r_oval = x0_r_oval + hemi_width
        self.brain_canvas.create_oval(x0_r_oval, y0_ovals, x1_r_oval, y1_ovals, outline=outline_color, width=1, dash=(2,2))

        self.brain_canvas.create_text(x0_l_oval + hemi_width/2, y0_ovals -10, text="Left Hemisphere", fill=self.active_theme_colors["fg"], anchor="s", font=("Helvetica", 10))
        self.brain_canvas.create_text(x0_r_oval + hemi_width/2, y0_ovals -10, text="Right Hemisphere", fill=self.active_theme_colors["fg"], anchor="s", font=("Helvetica", 10))

        num_bands = len(BASE_CHANNEL_NAMES)
        band_rect_height = (hemi_height - (num_bands -1) * 5) / num_bands 
        band_rect_width = hemi_width * 0.6
        band_label_color = self.active_theme_colors["band_label_color"]

        for i, band_name in enumerate(BASE_CHANNEL_NAMES):
            y_offset = y0_ovals + i * (band_rect_height + 5)
            lx0 = x0_l_oval + (hemi_width - band_rect_width) / 2; ly0 = y_offset
            lx1 = lx0 + band_rect_width; ly1 = ly0 + band_rect_height
            self.band_shapes['left'][band_name] = self.brain_canvas.create_rectangle(lx0, ly0, lx1, ly1, outline=outline_color, fill=base_fill, width=1)
            self.brain_canvas.create_text(lx0 - 10, ly0 + band_rect_height/2, text=band_name[0], anchor="e", fill=band_label_color, font=("Helvetica", 8, "bold"))
            rx0 = x0_r_oval + (hemi_width - band_rect_width) / 2; ry0 = y_offset
            rx1 = rx0 + band_rect_width; ry1 = ry0 + band_rect_height
            self.band_shapes['right'][band_name] = self.brain_canvas.create_rectangle(rx0, ry0, rx1, ry1, outline=outline_color, fill=base_fill, width=1)
            self.brain_canvas.create_text(rx1 + 10, ry0 + band_rect_height/2, text=band_name[0], anchor="w", fill=band_label_color, font=("Helvetica", 8, "bold"))

    def update_brain_visualization(self, channel_activities):
        if not self.band_shapes['left'] or not self.band_shapes['right']: return
        for i, band_name in enumerate(BASE_CHANNEL_NAMES):
            left_activity = channel_activities[i * 2]
            right_activity = channel_activities[i * 2 + 1]
            left_color = self._get_band_heatmap_color(band_name, left_activity)
            right_color = self._get_band_heatmap_color(band_name, right_activity)
            if band_name in self.band_shapes['left'] and self.band_shapes['left'][band_name]:
                self.brain_canvas.itemconfig(self.band_shapes['left'][band_name], fill=left_color)
            if band_name in self.band_shapes['right'] and self.band_shapes['right'][band_name]:
                self.brain_canvas.itemconfig(self.band_shapes['right'][band_name], fill=right_color)

    def update_osc_period_display(self, type):
        if type == 'slow': self.slow_osc_display_label.config(text=f"{self.slow_osc_period_ms_var.get():.0f}ms")
        elif type == 'fast': self.fast_osc_display_label.config(text=f"{self.fast_osc_period_ms_var.get():.0f}ms")

    def update_band_param(self, value_str, band_name, display_label):
        val = float(value_str)
        display_label.config(text=f"{val:.1f}")
        for so in self.signal_objects:
            if so.band_name == band_name: so.set_frequency(val); break
    
    def toggle_theme(self):
        self.apply_theme()
        # After applying theme, redraw static canvas elements if canvas exists
        if hasattr(self, 'brain_canvas') and self.brain_canvas.winfo_exists():
            self._draw_brain_initial()
            # Force an update of dynamic elements too, if simulation is running
            if self.is_simulating and hasattr(self, 'last_sample_for_viz') and self.last_sample_for_viz:
                 self.update_brain_visualization(self.last_sample_for_viz)


    def apply_theme(self):
        current_theme_name = "Matrix" if self.dark_theme_enabled_var.get() else "Light"
        self.active_theme_colors = THEMES[current_theme_name]
        
        self.style.theme_use('clam') 
        self.style.configure('.', background=self.active_theme_colors["bg"], foreground=self.active_theme_colors["fg"], fieldbackground=self.active_theme_colors["input_bg"], bordercolor=self.active_theme_colors["accent"])
        self.style.map('.', background=[('active', self.active_theme_colors["accent"]), ('disabled', self.active_theme_colors["bg"])], foreground=[('active', self.active_theme_colors["button_fg"]), ('disabled', self.active_theme_colors["fg"])])
        self.style.configure('TButton', background=self.active_theme_colors["button_bg"], foreground=self.active_theme_colors["button_fg"], padding=5)
        self.style.map('TButton', background=[('active', self.active_theme_colors["accent"])])
        self.style.configure('Large.TButton', font=('Helvetica', 10, 'bold'))
        self.style.configure('TLabel', background=self.active_theme_colors["bg"], foreground=self.active_theme_colors["fg"])
        self.style.configure('Header.TLabel', font=('Helvetica', 16, 'bold'), background=self.active_theme_colors["bg"], foreground=self.active_theme_colors["fg"])
        self.style.configure('Status.TLabel', background=self.active_theme_colors["bg"], foreground=self.active_theme_colors["fg"])
        self.style.configure('Controls.TLabel', background=self.active_theme_colors["bg"], foreground=self.active_theme_colors["fg"]) 
        self.style.configure('App.TFrame', background=self.active_theme_colors["bg"])
        self.style.configure('Controls.TFrame', background=self.active_theme_colors["bg"])
        self.style.configure('TLabelframe', background=self.active_theme_colors["frame_bg"], bordercolor=self.active_theme_colors["accent"])
        self.style.configure('Controls.TLabelframe', background=self.active_theme_colors["frame_bg"], bordercolor=self.active_theme_colors["accent"])
        self.style.configure('TLabelframe.Label', background=self.active_theme_colors["frame_bg"], foreground=self.active_theme_colors["fg"]) 
        self.style.configure('Controls.TLabelframe.Label', background=self.active_theme_colors["frame_bg"], foreground=self.active_theme_colors["fg"])
        self.style.configure('Controls.TCheckbutton', background=self.active_theme_colors["bg"], foreground=self.active_theme_colors["fg"])
        self.style.map('Controls.TCheckbutton', 
                       indicatorcolor=[('selected', self.active_theme_colors["accent"]), ('!selected', self.active_theme_colors["input_bg"])],
                       background=[('active', self.active_theme_colors["bg"])])


        try:
            default_scale_layout = self.style.layout('Horizontal.TScale')
            if default_scale_layout: self.style.layout('Horizontal.Controls.TScale', default_scale_layout)
            else:
                self.log_message("Warning: Could not retrieve default layout for Horizontal.TScale. Using fallback for Controls.TScale.")
                self.style.layout('Horizontal.Controls.TScale', [('Scale.trough', {'sticky': 'nswe', 'children': [('Scale.slider', {'side': 'left', 'sticky': ''})]})])
        except tk.TclError as e:
            self.log_message(f"TclError defining layout for Horizontal.Controls.TScale: {e}. Using fallback.")
            self.style.layout('Horizontal.Controls.TScale', [('Scale.trough', {'sticky': 'nswe', 'children': [('Scale.slider', {'side': 'left', 'sticky': ''})]})])
        self.style.configure('Horizontal.Controls.TScale', background=self.active_theme_colors["bg"], troughcolor=self.active_theme_colors["input_bg"])
        
        self.root.configure(bg=self.active_theme_colors["bg"])

        # Update already created widgets if they exist
        if hasattr(self, 'main_app_frame') and self.main_app_frame: 
            self.main_app_frame.configure(style='App.TFrame') # Re-apply style
            def _walk_widgets(widget):
                children = widget.winfo_children()
                for child in children:
                    yield child
                    yield from _walk_widgets(child)
            for widget in _walk_widgets(self.main_app_frame):
                try:
                    # Attempt to re-apply styles or direct configurations
                    if isinstance(widget, ttk.Label): widget.configure(style=widget.cget('style')) # Refresh
                    elif isinstance(widget, ttk.Button): widget.configure(style=widget.cget('style'))
                    elif isinstance(widget, ttk.Frame): widget.configure(style=widget.cget('style'))
                    elif isinstance(widget, ttk.LabelFrame): widget.configure(style=widget.cget('style'))
                    elif isinstance(widget, ttk.Scale): widget.configure(style=widget.cget('style'))
                    elif isinstance(widget, ttk.Checkbutton): widget.configure(style=widget.cget('style'))
                    
                    if widget_class := widget.winfo_class(): # Check if it's a Tk widget
                        if widget_class == 'Canvas' and widget == self.brain_canvas:
                            widget.configure(bg=self.active_theme_colors["bg"])
                        elif widget_class == 'Text' and widget == self.log_text_area: # ScrolledText is a Text widget
                             widget.config(background=self.active_theme_colors["log_bg"], foreground=self.active_theme_colors["log_fg"], insertbackground=self.active_theme_colors["fg"], selectbackground=self.active_theme_colors["accent"], selectforeground=self.active_theme_colors["log_bg"])
                except tk.TclError:
                    pass # Some widgets might not have a style or might be standard Tk

        # Redraw brain with new theme colors if canvas exists
        if hasattr(self, 'brain_canvas') and self.brain_canvas.winfo_exists():
            self.brain_canvas.configure(bg=self.active_theme_colors["bg"]) # Update canvas background
            self._draw_brain_initial() # Redraw static elements
            # If simulation is running, update dynamic elements with the last known sample
            if self.is_simulating and hasattr(self, 'last_sample_for_viz') and self.last_sample_for_viz:
                 self.update_brain_visualization(self.last_sample_for_viz)


    def log_message(self, message):
        def _log():
            if hasattr(self, 'log_text_area') and self.log_text_area:
                self.log_text_area.config(state=tk.NORMAL)
                self.log_text_area.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
                self.log_text_area.see(tk.END)
                self.log_text_area.config(state=tk.DISABLED)
            else:
                if hasattr(self, 'root') and self.root.winfo_exists(): self.root.after(100, _log) 
        if hasattr(self, 'root') and self.root.winfo_exists(): _log()
        print(message) 

    def toggle_simulation(self):
        if not self.is_simulating: self.start_simulation()
        else: self.stop_simulation()

    def start_simulation(self):
        self.log_message("Starting simulation...")
        try:
            info = StreamInfo(STREAM_NAME, STREAM_TYPE, CHANNEL_COUNT, SAMPLE_RATE, CHANNEL_FORMAT, UNIQUE_ID)
            chans_desc = info.desc().append_child("channels")
            lsl_channel_labels = [f"{side}-{band}" for band in BASE_CHANNEL_NAMES for side in ("L", "R")]
            for full_label in lsl_channel_labels:
                ch = chans_desc.append_child("channel")
                ch.append_child_value("label", full_label); ch.append_child_value("unit", "relative_power")
                parts = full_label.split('-'); hemisphere = "Left" if parts[0] == "L" else "Right"; base_band = parts[1]
                ch.append_child_value("type", f"EEG_Band_{base_band}"); ch.append_child_value("hemisphere", hemisphere)
            self.lsl_outlet = StreamOutlet(info)
            self.log_message(f"LSL Stream '{STREAM_NAME}' created with {CHANNEL_COUNT} channels.")
            self.is_simulating = True; self.toggle_button.config(text="Stop Simulation")
            self.status_var.set(f"Status: Simulating ({STREAM_NAME})"); self.start_time = time.time()
            self.simulation_thread = threading.Thread(target=self.simulation_loop, daemon=True); self.simulation_thread.start()
            self.log_message("Simulation thread started.")
        except Exception as e:
            self.log_message(f"Error starting simulation: {e}"); messagebox.showerror("Simulation Error", f"Could not start LSL stream: {e}")
            self.status_var.set("Status: Error"); 
            if self.lsl_outlet: self.lsl_outlet = None 
            self.is_simulating = False

    def simulation_loop(self):
        self.last_sample_for_viz = [0.0] * CHANNEL_COUNT # Store last sample for theme change updates
        try:
            while self.is_simulating and self.lsl_outlet:
                current_sim_time = time.time() - self.start_time
                sample_to_send = [] 
                current_slow_osc_period_s = self.slow_osc_period_ms_var.get() / 1000.0
                current_fast_osc_period_s = self.fast_osc_period_ms_var.get() / 1000.0
                if current_slow_osc_period_s <= 0: current_slow_osc_period_s = 0.001 
                if current_fast_osc_period_s <= 0: current_fast_osc_period_s = 0.001
                
                visualization_activities = [0.0] * CHANNEL_COUNT 

                for i, signal_obj in enumerate(self.signal_objects): 
                    base_activity = signal_obj.generate(current_sim_time)
                    chosen_osc_period_s = current_slow_osc_period_s if signal_obj.speed_category == "slow" else current_fast_osc_period_s
                    hemisphere_mod_angle = (2 * math.pi * current_sim_time) / chosen_osc_period_s
                    hemisphere_modulator = math.sin(hemisphere_mod_angle)
                    left_weight = 0.5 + 0.5 * hemisphere_modulator; right_weight = 0.5 - 0.5 * hemisphere_modulator
                    left_val = max(0.0, min(1.0, base_activity * left_weight))
                    right_val = max(0.0, min(1.0, base_activity * right_weight))
                    sample_to_send.extend([left_val, right_val])
                    visualization_activities[i * 2] = left_val
                    visualization_activities[i * 2 + 1] = right_val
                
                self.last_sample_for_viz = list(visualization_activities) # Update stored sample
                self.lsl_outlet.push_sample(sample_to_send)
                
                if hasattr(self, 'root') and self.root.winfo_exists():
                    self.root.after(0, self.update_brain_visualization, visualization_activities)
                
                time.sleep(1.0 / SAMPLE_RATE)
        except Exception as e:
            if self.is_simulating and hasattr(self, 'root') and self.root.winfo_exists(): 
                self.root.after(0, self.log_message, f"Error in simulation loop: {e}")
        finally: 
            if hasattr(self, 'root') and self.root.winfo_exists():
                self.root.after(0, self.log_message, "Simulation loop ended.")
            else: print("Simulation loop ended (root window closed).")

    def stop_simulation(self):
        self.log_message("Stopping simulation...")
        self.is_simulating = False
        if self.simulation_thread and self.simulation_thread.is_alive():
            self.log_message("Waiting for simulation thread to join..."); self.simulation_thread.join(timeout=2.0) 
            self.log_message("Simulation thread joined." if not self.simulation_thread.is_alive() else "Warning: Sim thread did not join.")
        if self.lsl_outlet: self.log_message(f"LSL outlet for '{STREAM_NAME}' will be closed."); self.lsl_outlet = None 
        if hasattr(self, 'toggle_button'):
            self.toggle_button.config(text="Start Simulation"); self.status_var.set("Status: Not Simulating")
        self.log_message("Simulation stopped.")

    def on_closing(self):
        self.log_message("Application closing...")
        if self.is_simulating: self.stop_simulation()
        if hasattr(self, 'root') and self.root.winfo_exists(): self.root.destroy()

if __name__ == "__main__":
    gui_root = tk.Tk()
    app = SimulatorGUI(gui_root)
    gui_root.mainloop()
