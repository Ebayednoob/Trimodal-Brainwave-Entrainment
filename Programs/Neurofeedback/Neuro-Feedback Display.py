import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, filedialog
from pylsl import StreamInlet, resolve_byprop
import threading
import time
import collections # For deque, to store plot data
import json # For saving/loading data
import os # For directory operations

# --- Matplotlib Imports ---
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Matplotlib not found. Graphs will not be displayed. Please install it: pip install matplotlib")

# --- Configuration ---
STREAM_TYPE_TO_RESOLVE = 'EEG' 
EXPECTED_CHANNELS = 10 
BASE_CHANNEL_NAMES = ["Delta", "Theta", "Alpha", "Beta", "Gamma"] 
DISPLAY_LABELS = []
for band in BASE_CHANNEL_NAMES:
    DISPLAY_LABELS.extend([f"L-{band}", f"R-{band}"])

PLOT_HISTORY_SIZE = 100 
PLAYBACK_UPDATE_INTERVAL_MS = 50 
SESSIONS_DIR = "./eeg_sessions" # Directory to store session files

# Target beat frequencies for entrainment
ENTRAINMENT_TARGET_FREQS = {
    "Delta": 2.0, "Theta": 6.0, "Alpha": 10.0, "Beta": 15.0, "Gamma": 40.0
}
DEFAULT_BASE_FREQUENCY_HZ = 428.0


# --- Theme Definitions ---
THEMES = {
    "Light": {
        "bg": "#F0F0F0", "fg": "#000000", "input_bg": "#FFFFFF",
        "button_bg": "#E0E0E0", "button_fg": "#000000",
        "log_bg": "#FFFFFF", "log_fg": "#000000",
        "accent": "#0078D7", "frame_bg": "#F5F5F5",
        "brain_outline": "#555555", "brain_base_fill": "#D0D0D0", 
        "band_colors_active": {"Delta": "#00008B", "Theta": "#4682B4", "Alpha": "#20B2AA", "Beta":  "#FFD700", "Gamma": "#FF4500"},
        "band_label_color": "#000000",
        "plot_bg": "#FFFFFF", "plot_fg": "#000000", "plot_grid": "#CCCCCC",
        "listbox_bg": "#FFFFFF", "listbox_fg": "#000000", "listbox_select_bg": "#0078D7", "listbox_select_fg": "#FFFFFF"
    },
    "Matrix": { 
        "bg": "#000000", "fg": "#00FF00", "input_bg": "#0D0D0D",
        "button_bg": "#003300", "button_fg": "#00FF00",
        "log_bg": "#050505", "log_fg": "#33FF33",
        "accent": "#00CC00", "frame_bg": "#0A0A0A",
        "brain_outline": "#008000", "brain_base_fill": "#001000", 
        "band_colors_active": {"Delta": "#006400", "Theta": "#228B22", "Alpha": "#32CD32", "Beta":  "#7FFF00", "Gamma": "#ADFF2F"},
        "band_label_color": "#90EE90",
        "plot_bg": "#050505", "plot_fg": "#00FF00", "plot_grid": "#004400",
        "listbox_bg": "#0D0D0D", "listbox_fg": "#00FF00", "listbox_select_bg": "#00CC00", "listbox_select_fg": "#000000"
    }
}

class NeurofeedbackApp:
    def __init__(self, root):
        self.root = root
        self.root.title("10-Channel Neurofeedback Display")
        self.root.geometry("1200x950" if MATPLOTLIB_AVAILABLE else "500x750")

        self.is_streaming = False; self.inlet = None; self.stream_thread = None
        self.recorded_data = []; self.is_recording = False; self.is_playing_back = False
        self.playback_thread = None; self.playback_current_index = 0; self.playback_start_time = 0 
        self.first_sample_timestamp_offset = 0
        self.last_sample_for_viz = [0.0] * EXPECTED_CHANNELS

        self.plot_data = [collections.deque(np.zeros(PLOT_HISTORY_SIZE), maxlen=PLOT_HISTORY_SIZE) for _ in range(EXPECTED_CHANNELS)]
        self.plot_lines = [None] * EXPECTED_CHANNELS
        self.fig = None; self.axes = []; self.canvas_widget = None
        self.plot_outer_frame = None; self.brain_viz_outer_frame = None

        self.dark_theme_enabled_var = tk.BooleanVar(value=False) 
        self.enable_graphs_var = tk.BooleanVar(value=True) 
        self.enable_brain_viz_var = tk.BooleanVar(value=True)
        self.load_from_file_var = tk.BooleanVar(value=False)
        self.base_frequency_var = tk.StringVar(value=str(DEFAULT_BASE_FREQUENCY_HZ))

        self.active_theme_colors = THEMES["Light"]
        self.style = ttk.Style()
        self.apply_theme() 
        
        self.band_shapes = {'left': {}, 'right': {}}
        # StringVars for the "Data Insights" tab
        self.insight_band_l_vars = {band: tk.StringVar(value="N/A") for band in BASE_CHANNEL_NAMES}
        self.insight_band_r_vars = {band: tk.StringVar(value="N/A") for band in BASE_CHANNEL_NAMES}
        self.binaural_suggestion_vars = {band: tk.StringVar(value="-") for band in BASE_CHANNEL_NAMES}

        self.setup_ui() 

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log_message(f"Application started with { 'Dark' if self.dark_theme_enabled_var.get() else 'Light' } theme.")
        if not MATPLOTLIB_AVAILABLE:
            self.log_message("Matplotlib not found. Graphs are disabled. Install: pip install matplotlib")
            self.enable_graphs_var.set(False)
        
        self.update_data_management_button_states()
        self.refresh_session_list() 
        self._update_binaural_suggestions() # Initial suggestions

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#'); return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    def _rgb_to_hex(self, rgb_color):
        return f'#{rgb_color[0]:02x}{rgb_color[1]:02x}{rgb_color[2]:02x}'
    def _interpolate_color(self, value, inactive_hex, active_hex):
        value = max(0, min(1, value)); inactive_rgb = self._hex_to_rgb(inactive_hex); active_rgb = self._hex_to_rgb(active_hex)
        inter_rgb = [int(inactive_rgb[i] + (active_rgb[i] - inactive_rgb[i]) * value) for i in range(3)]; return self._rgb_to_hex(tuple(inter_rgb))
    def _get_band_heatmap_color(self, band_name, activity_value):
        inactive_color = self.active_theme_colors["brain_base_fill"]; active_color = self.active_theme_colors["band_colors_active"].get(band_name, "#808080")
        return self._interpolate_color(activity_value, inactive_color, active_color)

    def setup_ui(self):
        self.main_app_frame = ttk.Frame(self.root, style='App.TFrame')
        self.main_app_frame.pack(expand=True, fill=tk.BOTH)

        top_bar_main = ttk.Frame(self.main_app_frame, padding=(10,5), style='Controls.TFrame')
        top_bar_main.pack(fill=tk.X, side=tk.TOP)
        ttk.Label(top_bar_main, text="Neurofeedback Display", font=("Helvetica", 16, "bold"), style='Header.TLabel').pack(side=tk.LEFT, padx=(0,20))
        self.connection_status_var = tk.StringVar(value="Status: Not Connected")
        ttk.Label(top_bar_main, textvariable=self.connection_status_var, font=("Helvetica", 10), style='Status.TLabel').pack(side=tk.LEFT, expand=True, fill=tk.X)
        self.graphs_checkbox = ttk.Checkbutton(top_bar_main, text="Graphs", variable=self.enable_graphs_var, command=self.toggle_graph_visibility, style='Controls.TCheckbutton')
        if MATPLOTLIB_AVAILABLE: self.graphs_checkbox.pack(side=tk.RIGHT, padx=5)
        self.brain_viz_checkbox = ttk.Checkbutton(top_bar_main, text="Brain Viz", variable=self.enable_brain_viz_var, command=self.toggle_brain_viz_visibility, style='Controls.TCheckbutton')
        self.brain_viz_checkbox.pack(side=tk.RIGHT, padx=5)
        self.theme_checkbox = ttk.Checkbutton(top_bar_main, text="Dark Theme", variable=self.dark_theme_enabled_var, command=self.toggle_theme, style='Controls.TCheckbutton')
        self.theme_checkbox.pack(side=tk.RIGHT, padx=10)

        self.notebook = ttk.Notebook(self.main_app_frame, style='Controls.TNotebook')
        self.notebook.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

        live_playback_tab = ttk.Frame(self.notebook, style='App.TFrame'); self.notebook.add(live_playback_tab, text='Live / Playback'); self._setup_live_playback_tab(live_playback_tab)
        session_browser_tab = ttk.Frame(self.notebook, style='App.TFrame'); self.notebook.add(session_browser_tab, text='Session Browser'); self._setup_session_browser_tab(session_browser_tab)
        insights_tab = ttk.Frame(self.notebook, style='App.TFrame'); self.notebook.add(insights_tab, text='Data Insights & Entrainment'); self._setup_insights_tab(insights_tab)
        
    def _setup_live_playback_tab(self, parent_tab_frame):
        content_frame = ttk.Frame(parent_tab_frame, style='App.TFrame'); content_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        left_panel = ttk.Frame(content_frame, width=380, style='Controls.TFrame'); left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0,10)); left_panel.pack_propagate(False)
        connection_mode_frame = ttk.LabelFrame(left_panel, text="Connection Mode", style='Controls.TLabelframe'); connection_mode_frame.pack(pady=5, padx=5, fill="x")
        self.connect_button = ttk.Button(connection_mode_frame, text="Connect to LSL Stream", command=self.toggle_connection, style='Large.TButton'); self.connect_button.pack(pady=(5,2), fill=tk.X)
        self.load_from_file_checkbox = ttk.Checkbutton(connection_mode_frame, text="Load Data From File (Disables LSL)", variable=self.load_from_file_var, command=self.toggle_file_mode, style='Controls.TCheckbutton'); self.load_from_file_checkbox.pack(pady=(2,5), anchor='w')
        data_management_frame = ttk.LabelFrame(left_panel, text="Data Management", style='Controls.TLabelframe'); data_management_frame.pack(pady=5, padx=5, fill="x")
        record_btn_frame = ttk.Frame(data_management_frame, style='Controls.TFrame'); record_btn_frame.pack(fill=tk.X, pady=2)
        self.record_button = ttk.Button(record_btn_frame, text="Record", command=self.start_recording); self.record_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
        self.stop_record_button = ttk.Button(record_btn_frame, text="Stop Rec.", command=self.stop_recording); self.stop_record_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2,0))
        file_btn_frame = ttk.Frame(data_management_frame, style='Controls.TFrame'); file_btn_frame.pack(fill=tk.X, pady=2)
        self.save_button = ttk.Button(file_btn_frame, text="Save Data", command=self.save_data); self.save_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
        playback_btn_frame = ttk.Frame(data_management_frame, style='Controls.TFrame'); playback_btn_frame.pack(fill=tk.X, pady=2)
        self.playback_button = ttk.Button(playback_btn_frame, text="Playback", command=self.start_playback); self.playback_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
        self.stop_playback_button = ttk.Button(playback_btn_frame, text="Stop Playback", command=self.stop_playback); self.stop_playback_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2,0))
        reset_clear_frame = ttk.Frame(data_management_frame, style='Controls.TFrame'); reset_clear_frame.pack(fill=tk.X, pady=(5,2))
        self.reset_data_button = ttk.Button(reset_clear_frame, text="Reset Data", command=self.reset_data); self.reset_data_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0,2))
        self.clear_graphs_button = ttk.Button(reset_clear_frame, text="Clear Graphs", command=self.clear_graphs); self.clear_graphs_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(2,0))
        data_display_frame = ttk.LabelFrame(left_panel, text="Current Channel Data", style='Controls.TLabelframe'); data_display_frame.pack(pady=5, padx=5, fill="x")
        self.band_value_vars = []
        for i in range(EXPECTED_CHANNELS):
            frame = ttk.Frame(data_display_frame, style='Controls.TFrame'); frame.pack(fill="x", padx=5, pady=1)
            label_text = DISPLAY_LABELS[i] if i < len(DISPLAY_LABELS) else f"Ch {i+1}"
            ttk.Label(frame, text=f"{label_text}:", width=10, anchor="w", style='Controls.TLabel').pack(side=tk.LEFT)
            value_var = tk.StringVar(value="N/A"); ttk.Label(frame, textvariable=value_var, width=8, anchor="e", style='Controls.TLabel').pack(side=tk.RIGHT, padx=(0,5))
            self.band_value_vars.append(value_var)
        log_frame_outer = ttk.LabelFrame(left_panel, text="Log Output", style='Controls.TLabelframe'); log_frame_outer.pack(pady=10, padx=5, expand=True, fill=tk.BOTH)
        self.log_text = scrolledtext.ScrolledText(log_frame_outer, height=6, wrap=tk.WORD, state=tk.DISABLED); self.log_text.pack(expand=True, fill=tk.BOTH, padx=3, pady=3)
        right_panel = ttk.Frame(content_frame, style='App.TFrame'); right_panel.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
        self.brain_viz_outer_frame = ttk.LabelFrame(right_panel, text="Brain Activity Visualizer", style='Controls.TLabelframe')
        self.brain_canvas = tk.Canvas(self.brain_viz_outer_frame, height=200, bg=self.active_theme_colors["bg"], highlightthickness=0)
        if self.enable_brain_viz_var.get(): self.brain_viz_outer_frame.pack(fill=tk.X, padx=5, pady=(0,5), ipady=5); self.brain_canvas.pack(fill=tk.X, expand=False, padx=5, pady=5)
        self.brain_canvas.bind("<Configure>", self._draw_brain_initial)
        self.plot_outer_frame = ttk.LabelFrame(right_panel, text="Channel Graphs", style='Controls.TLabelframe')
        if MATPLOTLIB_AVAILABLE and self.enable_graphs_var.get(): self.plot_outer_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5); self.setup_plots(self.plot_outer_frame)
        elif MATPLOTLIB_AVAILABLE: self.plot_outer_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5); self.plot_outer_frame.pack_forget() 
        else: ttk.Label(right_panel, text="Matplotlib not found. Graphs disabled.", style='Error.TLabel', foreground="red").pack(expand=True, fill=tk.BOTH)

    def _setup_session_browser_tab(self, parent_tab_frame):
        browser_frame = ttk.LabelFrame(parent_tab_frame, text="Saved Sessions", style='Controls.TLabelframe', padding=10); browser_frame.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        list_frame = ttk.Frame(browser_frame, style='Controls.TFrame'); list_frame.pack(expand=True, fill=tk.BOTH, pady=(0,10))
        self.session_listbox = tk.Listbox(list_frame, selectmode=tk.SINGLE, exportselection=False, bg=self.active_theme_colors.get("listbox_bg", "#FFFFFF"), fg=self.active_theme_colors.get("listbox_fg", "#000000"), selectbackground=self.active_theme_colors.get("listbox_select_bg", "#0078D7"), selectforeground=self.active_theme_colors.get("listbox_select_fg", "#FFFFFF"), activestyle='none', relief=tk.FLAT, borderwidth=1) 
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.session_listbox.yview, style='Controls.Vertical.TScrollbar'); self.session_listbox.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y); self.session_listbox.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)
        button_frame = ttk.Frame(browser_frame, style='Controls.TFrame'); button_frame.pack(fill=tk.X)
        self.refresh_sessions_button = ttk.Button(button_frame, text="Refresh List", command=self.refresh_session_list); self.refresh_sessions_button.pack(side=tk.LEFT, padx=(0,5))
        self.load_selected_session_button = ttk.Button(button_frame, text="Load Selected Session", command=self.load_selected_session); self.load_selected_session_button.pack(side=tk.LEFT, padx=(5,0)); self.load_selected_session_button.config(state=tk.DISABLED)
        self.session_listbox.bind('<<ListboxSelect>>', self.on_session_select)

    def _setup_insights_tab(self, parent_tab_frame):
        insights_main_frame = ttk.Frame(parent_tab_frame, style='App.TFrame', padding=10)
        insights_main_frame.pack(expand=True, fill=tk.BOTH)

        # Current Band Powers (L/R)
        powers_frame = ttk.LabelFrame(insights_main_frame, text="Current Band Powers (L/R)", style='Controls.TLabelframe', padding=10)
        powers_frame.pack(fill=tk.X, pady=(0,10), anchor='n') # Anchor to top
        
        header_font = ("Helvetica", 10, "bold")
        ttk.Label(powers_frame, text="Band", style='Controls.TLabel', font=header_font).grid(row=0, column=0, padx=5, pady=2, sticky='w')
        ttk.Label(powers_frame, text="Left Power", style='Controls.TLabel', font=header_font).grid(row=0, column=1, padx=5, pady=2, sticky='w')
        ttk.Label(powers_frame, text="Right Power", style='Controls.TLabel', font=header_font).grid(row=0, column=2, padx=5, pady=2, sticky='w')

        for i, band_name in enumerate(BASE_CHANNEL_NAMES):
            ttk.Label(powers_frame, text=band_name, style='Controls.TLabel').grid(row=i+1, column=0, padx=5, pady=2, sticky='w')
            ttk.Label(powers_frame, textvariable=self.insight_band_l_vars[band_name], style='Controls.TLabel', width=10).grid(row=i+1, column=1, padx=5, pady=2, sticky='w')
            ttk.Label(powers_frame, textvariable=self.insight_band_r_vars[band_name], style='Controls.TLabel', width=10).grid(row=i+1, column=2, padx=5, pady=2, sticky='w')
        
        # Binaural Beat Entrainment Suggestions
        entrainment_frame = ttk.LabelFrame(insights_main_frame, text="Binaural Beat Entrainment", style='Controls.TLabelframe', padding=10)
        entrainment_frame.pack(fill=tk.X, pady=10, anchor='n') # Anchor to top

        # Use grid for all direct children of entrainment_frame
        entrainment_frame.columnconfigure(1, weight=1) # Allow entry to expand if needed

        base_freq_frame = ttk.Frame(entrainment_frame, style='Controls.TFrame')
        base_freq_frame.grid(row=0, column=0, columnspan=3, sticky='ew', pady=(0,10)) # Span columns
        ttk.Label(base_freq_frame, text="Base Frequency (Hz):", style='Controls.TLabel').pack(side=tk.LEFT, padx=(0,5))
        base_freq_entry = ttk.Entry(base_freq_frame, textvariable=self.base_frequency_var, width=10, style='Controls.TEntry')
        base_freq_entry.pack(side=tk.LEFT)
        base_freq_entry.bind("<KeyRelease>", lambda e: self._update_binaural_suggestions()) 

        suggestions_header_font = ("Helvetica", 9, "bold")
        ttk.Label(entrainment_frame, text="Band (Target Beat)", style='Controls.TLabel', font=suggestions_header_font).grid(row=1, column=0, padx=5, pady=2, sticky='w')
        ttk.Label(entrainment_frame, text="Left Ear Freq.", style='Controls.TLabel', font=suggestions_header_font).grid(row=1, column=1, padx=5, pady=2, sticky='w')
        ttk.Label(entrainment_frame, text="Right Ear Freq.", style='Controls.TLabel', font=suggestions_header_font).grid(row=1, column=2, padx=5, pady=2, sticky='w')

        for i, band_name in enumerate(BASE_CHANNEL_NAMES):
            target_hz = ENTRAINMENT_TARGET_FREQS.get(band_name, 0)
            ttk.Label(entrainment_frame, text=f"{band_name} ({target_hz} Hz):", style='Controls.TLabel').grid(row=i+2, column=0, padx=5, pady=2, sticky='w')
            ttk.Label(entrainment_frame, textvariable=self.binaural_suggestion_vars[band_name], style='Controls.TLabel', wraplength=300).grid(row=i+2, column=1, columnspan=2, padx=5, pady=2, sticky='w')


    def _update_binaural_suggestions(self):
        try:
            base_freq = float(self.base_frequency_var.get())
            if base_freq <= 0:
                for band_name in BASE_CHANNEL_NAMES:
                    self.binaural_suggestion_vars[band_name].set("Base freq > 0")
                return
        except ValueError:
            for band_name in BASE_CHANNEL_NAMES:
                self.binaural_suggestion_vars[band_name].set("Invalid base freq")
            return

        for band_name in BASE_CHANNEL_NAMES:
            target_beat_hz = ENTRAINMENT_TARGET_FREQS.get(band_name, 0)
            freq1 = base_freq
            freq2 = base_freq + target_beat_hz
            self.binaural_suggestion_vars[band_name].set(f"L: {freq1:.2f} Hz, R: {freq2:.2f} Hz")


    def _draw_brain_initial(self, event=None):
        if not self.enable_brain_viz_var.get() or not hasattr(self, 'brain_canvas') or not self.brain_canvas.winfo_exists(): return
        self.brain_canvas.delete("all") 
        width = self.brain_canvas.winfo_width(); height = self.brain_canvas.winfo_height()
        if width < 100 or height < 100: return
        padding = 10; top_padding_for_labels = 20; canvas_drawable_height = height - top_padding_for_labels
        hemi_width = (width - 3 * padding) / 2; hemi_height = canvas_drawable_height - padding
        outline_color = self.active_theme_colors["brain_outline"]; base_fill = self.active_theme_colors["brain_base_fill"]
        y0_ovals = padding + top_padding_for_labels; x0_l_oval = padding; x1_l_oval = padding + hemi_width; y1_ovals = y0_ovals + hemi_height
        self.brain_canvas.create_oval(x0_l_oval, y0_ovals, x1_l_oval, y1_ovals, outline=outline_color, width=1, dash=(2,2))
        x0_r_oval = padding + hemi_width + padding; x1_r_oval = x0_r_oval + hemi_width
        self.brain_canvas.create_oval(x0_r_oval, y0_ovals, x1_r_oval, y1_ovals, outline=outline_color, width=1, dash=(2,2))
        self.brain_canvas.create_text(x0_l_oval + hemi_width/2, y0_ovals -5, text="Left", fill=self.active_theme_colors["fg"], anchor="s", font=("Helvetica", 9))
        self.brain_canvas.create_text(x0_r_oval + hemi_width/2, y0_ovals -5, text="Right", fill=self.active_theme_colors["fg"], anchor="s", font=("Helvetica", 9))
        num_bands = len(BASE_CHANNEL_NAMES); band_rect_v_spacing = 3
        band_rect_height = (hemi_height - (num_bands -1) * band_rect_v_spacing) / num_bands 
        band_rect_width = hemi_width * 0.7; band_label_color = self.active_theme_colors["band_label_color"]
        for i, band_name in enumerate(BASE_CHANNEL_NAMES):
            y_offset = y0_ovals + i * (band_rect_height + band_rect_v_spacing)
            lx0 = x0_l_oval + (hemi_width - band_rect_width) / 2; ly0 = y_offset; lx1 = lx0 + band_rect_width; ly1 = ly0 + band_rect_height
            self.band_shapes['left'][band_name] = self.brain_canvas.create_rectangle(lx0, ly0, lx1, ly1, outline=outline_color, fill=base_fill, width=1)
            self.brain_canvas.create_text(lx0 - 5, ly0 + band_rect_height/2, text=band_name[0], anchor="e", fill=band_label_color, font=("Helvetica", 7, "bold"))
            rx0 = x0_r_oval + (hemi_width - band_rect_width) / 2; ry0 = y_offset; rx1 = rx0 + band_rect_width; ry1 = ry0 + band_rect_height
            self.band_shapes['right'][band_name] = self.brain_canvas.create_rectangle(rx0, ry0, rx1, ry1, outline=outline_color, fill=base_fill, width=1)

    def update_brain_visualization(self, channel_activities):
        if not self.enable_brain_viz_var.get() or not self.band_shapes['left'] or not self.band_shapes['right'] or not channel_activities or len(channel_activities) != EXPECTED_CHANNELS: return
        for i, band_name in enumerate(BASE_CHANNEL_NAMES):
            left_activity = channel_activities[i * 2]; right_activity = channel_activities[i * 2 + 1]
            left_color = self._get_band_heatmap_color(band_name, left_activity); right_color = self._get_band_heatmap_color(band_name, right_activity)
            if band_name in self.band_shapes['left'] and self.band_shapes['left'][band_name]: self.brain_canvas.itemconfig(self.band_shapes['left'][band_name], fill=left_color)
            if band_name in self.band_shapes['right'] and self.band_shapes['right'][band_name]: self.brain_canvas.itemconfig(self.band_shapes['right'][band_name], fill=right_color)

    def setup_plots(self, parent_frame):
        if not MATPLOTLIB_AVAILABLE: return
        if self.fig: plt.close(self.fig); 
        if self.canvas_widget: self.canvas_widget.get_tk_widget().destroy()
        self.fig, axs = plt.subplots(EXPECTED_CHANNELS, 1, sharex=True, figsize=(6, 8))
        self.fig.patch.set_facecolor(self.active_theme_colors["plot_bg"])
        if EXPECTED_CHANNELS == 1: axs = [axs]
        self.axes = list(axs); self.plot_lines = [None] * EXPECTED_CHANNELS
        for i in range(EXPECTED_CHANNELS):
            ax = self.axes[i]
            self.plot_lines[i], = ax.plot(np.arange(PLOT_HISTORY_SIZE), list(self.plot_data[i]), '-', color=self.active_theme_colors["accent"])
            ax.set_title(DISPLAY_LABELS[i] if i < len(DISPLAY_LABELS) else f"Ch {i+1}", fontsize=9, color=self.active_theme_colors["plot_fg"])
            ax.set_ylim(0, 1.1); ax.set_ylabel("Power", fontsize=7, color=self.active_theme_colors["plot_fg"])
            ax.set_facecolor(self.active_theme_colors["plot_bg"])
            ax.tick_params(axis='y', labelsize=7, colors=self.active_theme_colors["plot_fg"]); ax.tick_params(axis='x', labelsize=7, colors=self.active_theme_colors["plot_fg"])
            ax.grid(True, linestyle=':', alpha=0.7, color=self.active_theme_colors["plot_grid"])
            for spine in ax.spines.values(): spine.set_edgecolor(self.active_theme_colors["plot_fg"])
            if i == EXPECTED_CHANNELS - 1: ax.set_xlabel("Time Steps", fontsize=8, color=self.active_theme_colors["plot_fg"])
            else: ax.set_xticklabels([])
        self.fig.tight_layout(pad=1.5)
        self.canvas_widget = FigureCanvasTkAgg(self.fig, master=parent_frame)
        self.canvas_widget.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas_widget.draw(); self.log_message("Graphs (re)initialized.")

    def update_plots(self):
        if not MATPLOTLIB_AVAILABLE or not self.enable_graphs_var.get() or not (self.is_streaming or self.is_playing_back) or not self.fig or not self.canvas_widget: return
        for i in range(EXPECTED_CHANNELS):
            if self.plot_lines[i]: self.plot_lines[i].set_ydata(list(self.plot_data[i]))
        try: self.canvas_widget.draw_idle()
        except Exception as e: self.log_message(f"Error drawing canvas: {e}")

    def toggle_graph_visibility(self):
        if not MATPLOTLIB_AVAILABLE: self.enable_graphs_var.set(False); messagebox.showinfo("Graphs Unavailable", "Matplotlib library is not installed."); return
        if self.enable_graphs_var.get():
            if self.plot_outer_frame:
                if not self.plot_outer_frame.winfo_ismapped(): self.plot_outer_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
                if not self.fig: self.setup_plots(self.plot_outer_frame)
                self.update_plots()
        else:
            if self.plot_outer_frame and self.plot_outer_frame.winfo_ismapped(): self.plot_outer_frame.pack_forget()
        self.log_message(f"Graphs {'enabled' if self.enable_graphs_var.get() else 'disabled'}.")

    def toggle_brain_viz_visibility(self):
        if self.enable_brain_viz_var.get():
            if self.brain_viz_outer_frame:
                if not self.brain_viz_outer_frame.winfo_ismapped():
                    self.brain_viz_outer_frame.pack(fill=tk.X, padx=5, pady=(0,5), ipady=5)
                    self.brain_canvas.pack(fill=tk.X, expand=False, padx=5, pady=5) 
                self._draw_brain_initial() 
                if (self.is_streaming or self.is_playing_back) and self.last_sample_for_viz: self.update_brain_visualization(self.last_sample_for_viz)
        else:
            if self.brain_viz_outer_frame and self.brain_viz_outer_frame.winfo_ismapped(): self.brain_viz_outer_frame.pack_forget()
        self.log_message(f"Brain Visualizer {'enabled' if self.enable_brain_viz_var.get() else 'disabled'}.")

    def toggle_theme(self):
        self.apply_theme()
        if self.enable_brain_viz_var.get() and hasattr(self, 'brain_canvas') and self.brain_canvas.winfo_exists():
            self._draw_brain_initial() 
            if (self.is_streaming or self.is_playing_back) and self.last_sample_for_viz: self.update_brain_visualization(self.last_sample_for_viz)
        if MATPLOTLIB_AVAILABLE and self.fig and self.axes and self.enable_graphs_var.get():
            self.fig.patch.set_facecolor(self.active_theme_colors["plot_bg"])
            for i, ax in enumerate(self.axes):
                ax.set_title(DISPLAY_LABELS[i] if i < len(DISPLAY_LABELS) else f"Ch {i+1}", fontsize=9, color=self.active_theme_colors["plot_fg"])
                ax.set_ylabel("Power", fontsize=7, color=self.active_theme_colors["plot_fg"])
                ax.set_facecolor(self.active_theme_colors["plot_bg"]); ax.tick_params(axis='y', colors=self.active_theme_colors["plot_fg"]); ax.tick_params(axis='x', colors=self.active_theme_colors["plot_fg"])
                ax.grid(True, color=self.active_theme_colors["plot_grid"]); 
                for spine in ax.spines.values(): spine.set_edgecolor(self.active_theme_colors["plot_fg"])
                if self.plot_lines[i]: self.plot_lines[i].set_color(self.active_theme_colors["accent"])
                if i == EXPECTED_CHANNELS - 1: ax.set_xlabel("Time Steps", fontsize=8, color=self.active_theme_colors["plot_fg"])
            if self.canvas_widget: self.canvas_widget.draw_idle()

    def _get_all_children_recursive(self, parent_widget):
        children = parent_widget.winfo_children()
        all_descendants = list(children) 
        for child in children:
            all_descendants.extend(self._get_all_children_recursive(child))
        return all_descendants

    def apply_theme(self):
        current_theme_name = "Matrix" if self.dark_theme_enabled_var.get() else "Light"
        self.active_theme_colors = THEMES[current_theme_name]
        tc = self.active_theme_colors
        self.style.theme_use('clam') 
        self.style.configure('.', background=tc["bg"], foreground=tc["fg"], fieldbackground=tc["input_bg"], bordercolor=tc["accent"])
        self.style.map('.', background=[('active', tc["accent"]), ('disabled', tc["bg"])], foreground=[('active', tc["button_fg"]), ('disabled', tc["fg"])])
        self.style.configure('TButton', background=tc["button_bg"], foreground=tc["button_fg"], padding=5)
        self.style.map('TButton', background=[('active', tc["accent"])])
        self.style.configure('Large.TButton', font=('Helvetica', 10, 'bold'))
        self.style.configure('TLabel', background=tc["bg"], foreground=tc["fg"])
        self.style.configure('Header.TLabel', font=('Helvetica', 16, 'bold'), background=tc["bg"], foreground=tc["fg"])
        self.style.configure('Status.TLabel', background=tc["bg"], foreground=tc["fg"])
        self.style.configure('Controls.TLabel', background=tc["bg"], foreground=tc["fg"]) 
        self.style.configure('Error.TLabel', background=tc["bg"], foreground="red")
        self.style.configure('App.TFrame', background=tc["bg"]); self.style.configure('Controls.TFrame', background=tc["bg"])
        self.style.configure('TLabelframe', background=tc["frame_bg"], bordercolor=tc["accent"])
        self.style.configure('Controls.TLabelframe', background=tc["frame_bg"], bordercolor=tc["accent"])
        self.style.configure('TLabelframe.Label', background=tc["frame_bg"], foreground=tc["fg"]) 
        self.style.configure('Controls.TLabelframe.Label', background=tc["frame_bg"], foreground=tc["fg"])
        self.style.configure('Controls.TCheckbutton', background=tc["bg"], foreground=tc["fg"], indicatorrelief=tk.FLAT) 
        self.style.map('Controls.TCheckbutton', indicatorcolor=[('selected', tc["accent"]), ('!selected', tc["input_bg"])], background=[('active', tc["bg"])])
        self.style.configure('Controls.TNotebook', background=tc["bg"], tabmargins=[2, 5, 2, 0] )
        self.style.configure('Controls.TNotebook.Tab', background=tc["frame_bg"], foreground=tc["fg"], padding=[5, 2])
        self.style.map('Controls.TNotebook.Tab', background=[('selected', tc["accent"])], foreground=[('selected', tc["button_fg"])])
        self.style.configure('Controls.Vertical.TScrollbar', background=tc["button_bg"], troughcolor=tc["input_bg"], bordercolor=tc["frame_bg"], arrowcolor=tc["fg"])
        self.style.configure('Controls.TEntry', fieldbackground=tc["input_bg"], foreground=tc["fg"], insertcolor=tc["fg"], bordercolor=tc["accent"])


        try:
            default_scale_layout = self.style.layout('Horizontal.TScale') 
            if default_scale_layout: self.style.layout('Horizontal.Controls.TScale', default_scale_layout)
            else: self.style.layout('Horizontal.Controls.TScale', [('Scale.trough', {'sticky': 'nswe', 'children': [('Scale.slider', {'side': 'left', 'sticky': ''})]})])
        except tk.TclError: self.style.layout('Horizontal.Controls.TScale', [('Scale.trough', {'sticky': 'nswe', 'children': [('Scale.slider', {'side': 'left', 'sticky': ''})]})])
        self.style.configure('Horizontal.Controls.TScale', background=tc["bg"], troughcolor=tc["input_bg"])
        
        self.root.configure(bg=tc["bg"])
        if hasattr(self, 'main_app_frame') and self.main_app_frame: 
            all_widgets_to_theme = self._get_all_children_recursive(self.main_app_frame)
            all_widgets_to_theme.append(self.main_app_frame)
            for widget in all_widgets_to_theme:
                try:
                    if isinstance(widget, (ttk.Label, ttk.Button, ttk.Frame, ttk.LabelFrame, ttk.Checkbutton, ttk.Notebook, ttk.Entry)): # Added Entry
                         current_style = widget.cget('style')
                         if current_style: widget.configure(style=current_style) 
                    elif isinstance(widget, tk.Canvas) and widget == self.brain_canvas: widget.configure(bg=tc["bg"])
                    elif isinstance(widget, scrolledtext.ScrolledText) and widget == self.log_text:
                         widget.config(background=tc["log_bg"], foreground=tc["log_fg"], insertbackground=tc["fg"], selectbackground=tc["accent"], selectforeground=tc["log_bg"])
                    elif isinstance(widget, tk.Listbox) and hasattr(self, 'session_listbox') and widget == self.session_listbox: 
                        widget.configure(bg=tc.get("listbox_bg", "#FFFFFF"), fg=tc.get("listbox_fg", "#000000"),
                                         selectbackground=tc.get("listbox_select_bg", "#0078D7"),
                                         selectforeground=tc.get("listbox_select_fg", "#FFFFFF"))
                except tk.TclError: pass 

    def log_message(self, message):
        def _log():
            if hasattr(self, 'log_text') and self.log_text:
                self.log_text.config(state=tk.NORMAL); self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n"); self.log_text.see(tk.END); self.log_text.config(state=tk.DISABLED)
            elif hasattr(self, 'root') and self.root.winfo_exists(): self.root.after(100, _log) 
        if hasattr(self, 'root') and self.root.winfo_exists(): _log()
        print(message) 

    def toggle_connection(self):
        if self.load_from_file_var.get(): messagebox.showinfo("LSL Disabled", "Uncheck 'Load Data From File' to connect to LSL."); return
        if not self.is_streaming: self.connect_to_stream()
        else: self.stop_lsl_stream()

    def connect_to_stream(self):
        self.log_message("Attempting to connect to LSL stream..."); self.connection_status_var.set("Status: Searching..."); self.root.update_idletasks()
        try:
            streams = resolve_byprop('type', STREAM_TYPE_TO_RESOLVE, timeout=3)
            if not streams: self.log_message(f"No LSL stream of type '{STREAM_TYPE_TO_RESOLVE}' found."); messagebox.showerror("Connection Error", f"No LSL stream found."); self.connection_status_var.set("Status: Not Connected"); return
            selected_stream_info = streams[0]; self.log_message(f"Found stream: {selected_stream_info.name()} ({selected_stream_info.channel_count()} ch). Connecting...")
            self.inlet = StreamInlet(selected_stream_info, max_chunklen=1); stream_info = self.inlet.info(); self.log_message(f"Connected to: '{stream_info.name()}', Channels: {stream_info.channel_count()}")
            if stream_info.channel_count() != EXPECTED_CHANNELS: msg = f"Stream has {stream_info.channel_count()} ch, expected {EXPECTED_CHANNELS}. Display may be incorrect."; self.log_message(f"WARNING: {msg}"); messagebox.showwarning("Channel Mismatch", msg)
            self.connection_status_var.set(f"Status: Connected to {stream_info.name()}"); self.is_streaming = True; 
            self.stream_thread = threading.Thread(target=self.fetch_data_loop, daemon=True); self.stream_thread.start()
        except Exception as e: self.log_message(f"Connection Error: {e}"); messagebox.showerror("Connection Error", f"{e}"); self.connection_status_var.set("Status: Error"); self.is_streaming = False; 
        self.update_data_management_button_states()

    def fetch_data_loop(self):
        try:
            while self.is_streaming and self.inlet:
                sample, timestamp = self.inlet.pull_sample(timeout=1.0) 
                if sample: 
                    self.last_sample_for_viz = list(sample); 
                    if self.is_recording: self.recorded_data.append({'timestamp': timestamp, 'sample': list(sample)})
                    self.root.after(0, self.update_gui_with_sample, sample, timestamp)
        except Exception as e:
            if self.is_streaming: self.log_message(f"Streaming Error: {e}"); self.root.after(0, self.stop_lsl_stream)
        self.log_message("LSL data fetching loop ended.")


    def update_gui_with_sample(self, sample, timestamp): 
        num_received = len(sample)
        for i in range(EXPECTED_CHANNELS):
            value_to_set = sample[i] if i < num_received else 0.0 # Default to 0.0 if sample is short
            str_value = f"{value_to_set:.3f}" if i < num_received else "N/A (Miss)"
            self.band_value_vars[i].set(str_value)
            
            # Update insight tab vars
            band_index = i // 2 # 0 for Delta, 1 for Theta, ...
            base_band_name = BASE_CHANNEL_NAMES[band_index]
            if i % 2 == 0: # Left channel
                self.insight_band_l_vars[base_band_name].set(str_value)
            else: # Right channel
                self.insight_band_r_vars[base_band_name].set(str_value)

            if MATPLOTLIB_AVAILABLE and self.enable_graphs_var.get(): self.plot_data[i].append(value_to_set)
        
        if MATPLOTLIB_AVAILABLE and self.enable_graphs_var.get(): self.update_plots()
        if self.enable_brain_viz_var.get() and hasattr(self, 'brain_canvas') and self.brain_canvas.winfo_exists(): self.update_brain_visualization(sample) 
        self._update_binaural_suggestions() # Update binaural beats too

    def stop_lsl_stream(self): 
        self.log_message("Stopping LSL stream..."); self.is_streaming = False
        if self.stream_thread and self.stream_thread.is_alive(): self.stream_thread.join(timeout=1.0)
        if self.inlet: self.inlet.close_stream(); self.inlet = None; self.log_message("LSL inlet closed.")
        self.connection_status_var.set("Status: Disconnected"); 
        if not self.is_playing_back and not (self.load_from_file_var.get() and self.recorded_data):
            for var in self.band_value_vars: var.set("N/A")
            for band_name in BASE_CHANNEL_NAMES: # Clear insights tab too
                self.insight_band_l_vars[band_name].set("N/A")
                self.insight_band_r_vars[band_name].set("N/A")

        self.update_data_management_button_states()

    def toggle_file_mode(self):
        if self.load_from_file_var.get(): 
            if self.is_streaming: self.stop_lsl_stream()
            if self.is_recording: self.stop_recording() 
            self.log_message("File mode activated. LSL connection disabled.")
        else: 
            if self.is_playing_back: self.stop_playback()
            self.log_message("File mode deactivated. LSL connection enabled.")
        self.update_data_management_button_states()

    def start_recording(self):
        if self.load_from_file_var.get(): messagebox.showinfo("Recording Disabled", "Cannot record when in 'Load From File' mode."); return
        if not self.is_streaming: messagebox.showinfo("Not Connected", "Connect to LSL stream before recording."); return
        if self.is_recording: self.log_message("Already recording."); return
        self.is_recording = True; self.log_message("Recording started..."); self.update_data_management_button_states()

    def stop_recording(self):
        if not self.is_recording: return
        self.is_recording = False; self.log_message(f"Recording stopped. {len(self.recorded_data)} samples recorded."); self.update_data_management_button_states()

    def save_data(self):
        if not self.recorded_data: messagebox.showinfo("No Data", "No data to save. Record or load data first."); return
        if not os.path.exists(SESSIONS_DIR): os.makedirs(SESSIONS_DIR)
        filepath = filedialog.asksaveasfilename(initialdir=SESSIONS_DIR, defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")], title="Save Recorded EEG Data")
        if not filepath: return 
        try:
            with open(filepath, 'w') as f: json.dump(self.recorded_data, f, indent=4)
            self.log_message(f"Data saved to {filepath}"); self.refresh_session_list() 
        except Exception as e: self.log_message(f"Error saving data: {e}"); messagebox.showerror("Save Error", f"Could not save data: {e}")

    def _load_data_from_path(self, filepath):
        try:
            with open(filepath, 'r') as f: loaded_content = json.load(f)
            if isinstance(loaded_content, list) and all(isinstance(item, dict) and 'timestamp' in item and 'sample' in item and isinstance(item['sample'], list) and len(item['sample']) == EXPECTED_CHANNELS for item in loaded_content):
                self.recorded_data = loaded_content; self.log_message(f"Data loaded from {filepath}. {len(self.recorded_data)} samples.")
                if self.recorded_data: 
                    first_record = self.recorded_data[0]
                    self.update_gui_with_sample(first_record['sample'], first_record['timestamp'])
                    self.last_sample_for_viz = list(first_record['sample'])
                return True 
            else: raise ValueError("Invalid file format or channel count mismatch.")
        except Exception as e: 
            self.log_message(f"Error loading data from {filepath}: {e}"); messagebox.showerror("Load Error", f"Could not load data: {e}"); self.recorded_data = [] 
            return False 
        finally:
            self.update_data_management_button_states()

    def load_selected_session(self):
        selected_indices = self.session_listbox.curselection()
        if not selected_indices: messagebox.showinfo("No Selection", "Please select a session from the list."); return
        selected_filename = self.session_listbox.get(selected_indices[0]); filepath = os.path.join(SESSIONS_DIR, selected_filename)
        if not self.load_from_file_var.get(): self.load_from_file_var.set(True); self.toggle_file_mode() 
        if self._load_data_from_path(filepath):
            self.notebook.select(0); self.log_message(f"Switched to Live/Playback tab with loaded session: {selected_filename}")
        self.update_data_management_button_states()

    def refresh_session_list(self):
        if not hasattr(self, 'session_listbox'): return 
        self.session_listbox.delete(0, tk.END)
        if not os.path.exists(SESSIONS_DIR):
            try: os.makedirs(SESSIONS_DIR); self.log_message(f"Created sessions directory: {SESSIONS_DIR}")
            except OSError as e: self.log_message(f"Error creating sessions directory {SESSIONS_DIR}: {e}"); return
        try:
            files = [f for f in os.listdir(SESSIONS_DIR) if f.endswith('.json')]
            for filename in sorted(files): self.session_listbox.insert(tk.END, filename)
            self.log_message(f"Refreshed session list. Found {len(files)} sessions.")
        except Exception as e: self.log_message(f"Error refreshing session list: {e}")
        self.on_session_select() 

    def on_session_select(self, event=None):
        if hasattr(self, 'load_selected_session_button'):
            if self.session_listbox.curselection(): self.load_selected_session_button.config(state=tk.NORMAL)
            else: self.load_selected_session_button.config(state=tk.DISABLED)

    def start_playback(self):
        if not self.load_from_file_var.get(): messagebox.showinfo("File Mode Disabled", "Playback requires 'Load Data From File' mode."); return
        if not self.recorded_data: messagebox.showinfo("No Data", "No data loaded for playback."); return
        if self.is_playing_back: self.log_message("Playback already in progress."); return
        self.is_playing_back = True; self.playback_current_index = 0; self.playback_start_time = time.monotonic() 
        if self.recorded_data: self.first_sample_timestamp_offset = self.recorded_data[0]['timestamp'] 
        self.log_message("Playback started..."); self.playback_thread = threading.Thread(target=self.playback_loop, daemon=True); self.playback_thread.start()
        self.update_data_management_button_states()

    def playback_loop(self):
        try:
            while self.is_playing_back and self.playback_current_index < len(self.recorded_data):
                record = self.recorded_data[self.playback_current_index]; sample_data = record['sample']; lsl_timestamp = record['timestamp'] 
                time_since_first_sample_recorded = lsl_timestamp - self.first_sample_timestamp_offset
                time_since_playback_started = time.monotonic() - self.playback_start_time
                if time_since_playback_started >= time_since_first_sample_recorded:
                    self.root.after(0, self.update_gui_with_sample, sample_data, lsl_timestamp)
                    self.last_sample_for_viz = list(sample_data); self.playback_current_index += 1
                time.sleep(PLAYBACK_UPDATE_INTERVAL_MS / 1000.0) 
            if self.is_playing_back: self.root.after(0, self.stop_playback) 
        except Exception as e: self.log_message(f"Error during playback: {e}"); 
        if self.is_playing_back: self.root.after(0, self.stop_playback) 
        self.log_message("Playback loop ended.")

    def stop_playback(self):
        if not self.is_playing_back: return
        self.is_playing_back = False; self.log_message("Playback stopped."); self.update_data_management_button_states()

    def reset_data(self):
        if self.is_recording: self.stop_recording()
        if self.is_playing_back: self.stop_playback()
        self.recorded_data = []; self.log_message("Recorded/loaded data has been reset.")
        for var in self.band_value_vars: var.set("N/A")
        for band_name in BASE_CHANNEL_NAMES:
            self.insight_band_l_vars[band_name].set("N/A")
            self.insight_band_r_vars[band_name].set("N/A")
        self.last_sample_for_viz = [0.0] * EXPECTED_CHANNELS
        if self.enable_brain_viz_var.get(): self.update_brain_visualization(self.last_sample_for_viz)
        self.clear_graphs(force_clear=True) 
        self.update_data_management_button_states()

    def clear_graphs(self, force_clear=False):
        if MATPLOTLIB_AVAILABLE and self.enable_graphs_var.get():
            if (self.is_streaming or self.is_playing_back or force_clear):
                for i in range(EXPECTED_CHANNELS): self.plot_data[i] = collections.deque(np.zeros(PLOT_HISTORY_SIZE), maxlen=PLOT_HISTORY_SIZE)
                self.update_plots(); self.log_message("Graphs cleared.")
            elif not (self.is_streaming or self.is_playing_back): self.log_message("Graphs not active, no need to clear.")
        elif MATPLOTLIB_AVAILABLE and not self.enable_graphs_var.get(): self.log_message("Graphs are disabled, cannot clear.")

    def update_data_management_button_states(self):
        self.connect_button.config(text="Connect to LSL Stream" if not self.is_streaming else "Disconnect LSL", state=tk.NORMAL if not self.load_from_file_var.get() else tk.DISABLED)
        can_record = self.is_streaming and not self.load_from_file_var.get()
        self.record_button.config(state=tk.NORMAL if can_record and not self.is_recording else tk.DISABLED)
        self.stop_record_button.config(state=tk.NORMAL if self.is_recording else tk.DISABLED)
        self.save_button.config(state=tk.NORMAL if self.recorded_data and not self.is_recording and not self.is_playing_back else tk.DISABLED) 
        can_playback = self.load_from_file_var.get() and self.recorded_data
        self.playback_button.config(state=tk.NORMAL if can_playback and not self.is_playing_back else tk.DISABLED)
        self.stop_playback_button.config(state=tk.NORMAL if self.is_playing_back else tk.DISABLED)
        self.reset_data_button.config(state=tk.NORMAL if self.recorded_data else tk.DISABLED)
        self.clear_graphs_button.config(state=tk.NORMAL if MATPLOTLIB_AVAILABLE and self.enable_graphs_var.get() else tk.DISABLED)

    def on_closing(self):
        self.log_message("Application closing..."); 
        if self.is_recording: self.stop_recording() 
        if self.is_playing_back: self.stop_playback() 
        if self.is_streaming: self.stop_lsl_stream() 
        if MATPLOTLIB_AVAILABLE and self.fig: plt.close(self.fig)
        self.root.destroy()

if __name__ == "__main__":
    main_root = tk.Tk()
    app = NeurofeedbackApp(main_root)
    main_root.mainloop()
