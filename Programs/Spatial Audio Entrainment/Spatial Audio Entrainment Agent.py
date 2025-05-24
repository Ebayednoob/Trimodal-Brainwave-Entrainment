import tkinter as tk
from tkinter import ttk
from tkinter import filedialog, messagebox
import numpy as np
import sounddevice as sd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading
import json # For saving and loading configurations
import soundfile # For saving WAV files
import time # For recording timing

# --- Constants ---
NUM_CHANNELS = 10 # Maximum number of channels
SAMPLE_RATE = 44100  # Hz

MIN_FREQ = 20  # Hz
MAX_FREQ = 5000 # Hz
DEFAULT_FREQ = 100 # Hz

MIN_AMP = 0.0
MAX_AMP = 1.0 
DEFAULT_AMP = 0.5 

MIN_ISO_FREQ = 0.0 # Hz
MAX_ISO_FREQ = 50.0 # Hz
DEFAULT_ISO_FREQ = 0.0 # Hz

MIN_POS = -1.0 
MAX_POS = 1.0  
DEFAULT_POS = 0.0 

BUFFER_DURATION = 0.05 
PLOT_DURATION = 1.0 
CHANNEL_PREVIEW_DURATION_SEC = 0.05 
RECORDING_BUFFER_SIZE_SEC = 0.1 # How often to generate audio for recording buffer

class AudioChannel:
    def __init__(self, master, channel_id, app_instance):
        self.channel_id = channel_id
        self.app = app_instance
        self.frame = ttk.LabelFrame(master, text=f"Channel {channel_id + 1}")

        # Internal state attributes
        self.frequency = DEFAULT_FREQ
        self.amplitude = DEFAULT_AMP
        self.is_active = True
        self.isochronic_frequency = DEFAULT_ISO_FREQ
        self.is_iso_active = False
        self.x_pos = DEFAULT_POS
        self.y_pos = DEFAULT_POS
        self.z_pos = DEFAULT_POS

        # --- UI Elements ---
        active_frame = ttk.Frame(self.frame)
        active_frame.pack(fill="x", pady=(0, 2))
        self.is_active_var = tk.BooleanVar(value=self.is_active)
        self.active_check = ttk.Checkbutton(active_frame, text="Active", variable=self.is_active_var, command=self._params_changed_by_ui)
        self.active_check.pack(side=tk.LEFT, padx=(5,0))

        freq_controls_frame = ttk.Frame(self.frame)
        freq_controls_frame.pack(fill="x", pady=1)
        ttk.Label(freq_controls_frame, text="Freq (Hz):", width=10).pack(side=tk.LEFT, padx=(5,0))
        self.freq_var = tk.DoubleVar(value=self.frequency)
        self.freq_slider = ttk.Scale(freq_controls_frame, from_=MIN_FREQ, to=MAX_FREQ, orient=tk.HORIZONTAL, variable=self.freq_var)
        self.freq_slider.pack(side=tk.LEFT, expand=True, fill="x", padx=5)
        self.freq_slider.bind("<ButtonRelease-1>", self._params_changed_by_ui)
        self.freq_label_var = tk.StringVar(value=f"{self.freq_var.get():.0f} Hz")
        ttk.Label(freq_controls_frame, textvariable=self.freq_label_var, width=7).pack(side=tk.LEFT, padx=(0,5))
        self.freq_entry = ttk.Entry(freq_controls_frame, textvariable=self.freq_var, width=6)
        self.freq_entry.pack(side=tk.LEFT, padx=(0,5))
        self.freq_entry.bind("<Return>", self._validate_and_update_freq_from_entry)
        self.freq_entry.bind("<FocusOut>", self._validate_and_update_freq_from_entry)

        amp_controls_frame = ttk.Frame(self.frame)
        amp_controls_frame.pack(fill="x", pady=1)
        ttk.Label(amp_controls_frame, text="Amp:", width=10).pack(side=tk.LEFT, padx=(5,0))
        self.amp_var = tk.DoubleVar(value=self.amplitude)
        self.amp_slider = ttk.Scale(amp_controls_frame, from_=MIN_AMP, to=MAX_AMP, orient=tk.HORIZONTAL, variable=self.amp_var)
        self.amp_slider.pack(side=tk.LEFT, expand=True, fill="x", padx=5)
        self.amp_slider.bind("<ButtonRelease-1>", self._params_changed_by_ui)
        self.amp_label_var = tk.StringVar(value=f"{self.amp_var.get():.2f}")
        ttk.Label(amp_controls_frame, textvariable=self.amp_label_var, width=5).pack(side=tk.LEFT, padx=(0,5))

        iso_controls_frame = ttk.Frame(self.frame)
        iso_controls_frame.pack(fill="x", pady=1)
        self.iso_active_var = tk.BooleanVar(value=self.is_iso_active)
        self.iso_active_check = ttk.Checkbutton(iso_controls_frame, text="Enable Iso", variable=self.iso_active_var, command=self._on_iso_active_toggled)
        self.iso_active_check.pack(side=tk.LEFT, padx=(5,5))
        ttk.Label(iso_controls_frame, text="Iso Freq (Hz):", width=10).pack(side=tk.LEFT, padx=(0,0))
        self.iso_freq_var = tk.DoubleVar(value=self.isochronic_frequency) 
        self.iso_freq_entry = ttk.Entry(iso_controls_frame, textvariable=self.iso_freq_var, width=6)
        self.iso_freq_entry.pack(side=tk.LEFT, padx=(5,5))
        self.iso_freq_entry.bind("<Return>", self._validate_and_update_iso_from_entry)
        self.iso_freq_entry.bind("<FocusOut>", self._validate_and_update_iso_from_entry)
        self.iso_freq_label_var = tk.StringVar(value=f"{self.iso_freq_var.get():.1f} Hz")
        self.iso_display_label = ttk.Label(iso_controls_frame, textvariable=self.iso_freq_label_var, width=7)
        self.iso_display_label.pack(side=tk.LEFT, padx=(0,5))

        spatial_frame = ttk.Frame(self.frame)
        spatial_frame.pack(fill="x", pady=1)
        x_frame = ttk.Frame(spatial_frame); x_frame.pack(fill="x")
        ttk.Label(x_frame, text="X Pos (L/R):", width=10).pack(side=tk.LEFT, padx=(5,0))
        self.x_pos_var = tk.DoubleVar(value=self.x_pos)
        self.x_pos_slider = ttk.Scale(x_frame, from_=MIN_POS, to=MAX_POS, orient=tk.HORIZONTAL, variable=self.x_pos_var)
        self.x_pos_slider.pack(side=tk.LEFT, expand=True, fill="x", padx=5); self.x_pos_slider.bind("<ButtonRelease-1>", self._params_changed_by_ui)
        self.x_pos_label_var = tk.StringVar(value=f"{self.x_pos_var.get():.2f}")
        ttk.Label(x_frame, textvariable=self.x_pos_label_var, width=5).pack(side=tk.LEFT, padx=(0,5))
        
        y_frame = ttk.Frame(spatial_frame); y_frame.pack(fill="x")
        ttk.Label(y_frame, text="Y Pos (F/B):", width=10).pack(side=tk.LEFT, padx=(5,0))
        self.y_pos_var = tk.DoubleVar(value=self.y_pos)
        self.y_pos_slider = ttk.Scale(y_frame, from_=MIN_POS, to=MAX_POS, orient=tk.HORIZONTAL, variable=self.y_pos_var)
        self.y_pos_slider.pack(side=tk.LEFT, expand=True, fill="x", padx=5); self.y_pos_slider.bind("<ButtonRelease-1>", self._params_changed_by_ui)
        self.y_pos_label_var = tk.StringVar(value=f"{self.y_pos_var.get():.2f}")
        ttk.Label(y_frame, textvariable=self.y_pos_label_var, width=5).pack(side=tk.LEFT, padx=(0,5))

        z_frame = ttk.Frame(spatial_frame); z_frame.pack(fill="x")
        ttk.Label(z_frame, text="Z Pos (U/D):", width=10).pack(side=tk.LEFT, padx=(5,0))
        self.z_pos_var = tk.DoubleVar(value=self.z_pos)
        self.z_pos_slider = ttk.Scale(z_frame, from_=MIN_POS, to=MAX_POS, orient=tk.HORIZONTAL, variable=self.z_pos_var)
        self.z_pos_slider.pack(side=tk.LEFT, expand=True, fill="x", padx=5); self.z_pos_slider.bind("<ButtonRelease-1>", self._params_changed_by_ui)
        self.z_pos_label_var = tk.StringVar(value=f"{self.z_pos_var.get():.2f}")
        ttk.Label(z_frame, textvariable=self.z_pos_label_var, width=5).pack(side=tk.LEFT, padx=(0,5))

        preview_plot_frame = ttk.Frame(self.frame)
        preview_plot_frame.pack(fill="x", pady=(3,1), padx=5)
        self.fig_preview, self.ax_preview = plt.subplots(figsize=(3.5, 0.7)) 
        self.fig_preview.patch.set_facecolor('#F0F0F0') 
        self.ax_preview.set_facecolor('#FEFEFE') 
        self.ax_preview.set_yticks([]); self.ax_preview.set_xticks([])
        for spine in self.ax_preview.spines.values(): spine.set_visible(False) 
        self.fig_preview.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02) 
        self.preview_line, = self.ax_preview.plot([], [], lw=1, color='#4A8CFF') 
        self.ax_preview.set_ylim(-MAX_AMP * 1.1, MAX_AMP * 1.1) 
        self.canvas_preview = FigureCanvasTkAgg(self.fig_preview, master=preview_plot_frame)
        self.canvas_preview_widget = self.canvas_preview.get_tk_widget()
        self.canvas_preview_widget.pack(fill=tk.BOTH, expand=True)
        
        self.freq_var.trace_add('write', self._sync_freq_display_from_var)
        self.amp_var.trace_add('write', self._sync_amp_display_from_var)
        self.iso_freq_var.trace_add('write', self._sync_iso_display_from_var)
        self.x_pos_var.trace_add('write', lambda *args: (self.x_pos_label_var.set(f"{self.x_pos_var.get():.2f}"), self._params_changed_by_ui() if self.app and self.app.is_playing else None))
        self.y_pos_var.trace_add('write', lambda *args: (self.y_pos_label_var.set(f"{self.y_pos_var.get():.2f}"), self._params_changed_by_ui() if self.app and self.app.is_playing else None))
        self.z_pos_var.trace_add('write', lambda *args: (self.z_pos_label_var.set(f"{self.z_pos_var.get():.2f}"), self._params_changed_by_ui() if self.app and self.app.is_playing else None))

        self._update_iso_entry_state()
        self._update_internal_params_from_vars()
        self.update_waveform_preview() 

    def _update_internal_params_from_vars(self):
        self.frequency = self.freq_var.get()
        self.amplitude = self.amp_var.get()
        self.is_active = self.is_active_var.get()
        self.is_iso_active = self.iso_active_var.get()
        try: self.isochronic_frequency = self.iso_freq_var.get()
        except tk.TclError: self.iso_freq_var.set(DEFAULT_ISO_FREQ); self.isochronic_frequency = DEFAULT_ISO_FREQ
        self.x_pos = self.x_pos_var.get()
        self.y_pos = self.y_pos_var.get()
        self.z_pos = self.z_pos_var.get()

    def _params_changed_by_ui(self, event=None):
        self._update_internal_params_from_vars()
        self.update_waveform_preview() 
        if self.app: self.app.notify_param_change()

    def _sync_freq_display_from_var(self, *args): val = self.freq_var.get(); self.freq_label_var.set(f"{val:.0f} Hz"); self.frequency = val
    def _validate_and_update_freq_from_entry(self, event=None):
        try: val = float(self.freq_entry.get()); val = max(MIN_FREQ, min(val, MAX_FREQ)); self.freq_var.set(val)
        except ValueError: self.freq_var.set(self.frequency)
        self._params_changed_by_ui() 
    def _sync_amp_display_from_var(self, *args): val = self.amp_var.get(); self.amp_label_var.set(f"{val:.2f}"); self.amplitude = val
    def _sync_iso_display_from_var(self, *args):
        try: val = self.iso_freq_var.get(); self.iso_freq_label_var.set(f"{val:.1f} Hz"); self.isochronic_frequency = val
        except tk.TclError: self.iso_freq_label_var.set("--- Hz" if not self.is_iso_active else f"{DEFAULT_ISO_FREQ:.1f} Hz (inv)")
    def _validate_and_update_iso_from_entry(self, event=None):
        if not self.is_iso_active: self.iso_freq_var.set(self.isochronic_frequency); return
        try: val = float(self.iso_freq_entry.get()); val = max(MIN_ISO_FREQ, min(val, MAX_ISO_FREQ)); self.iso_freq_var.set(val)
        except ValueError: self.iso_freq_var.set(self.isochronic_frequency)
        self._params_changed_by_ui() 
    def _update_iso_entry_state(self):
        is_active = self.iso_active_var.get()
        new_state = tk.NORMAL if is_active else tk.DISABLED
        self.iso_freq_entry.config(state=new_state); self.iso_display_label.config(state=new_state)
        if not is_active: self.iso_freq_label_var.set("--- Hz")
        else: self.iso_freq_label_var.set(f"{self.iso_freq_var.get():.1f} Hz")
    def _on_iso_active_toggled(self, event=None):
        self.is_iso_active = self.iso_active_var.get(); self._update_iso_entry_state()
        if not self.is_iso_active: self.iso_freq_var.set(DEFAULT_ISO_FREQ); self.isochronic_frequency = DEFAULT_ISO_FREQ
        else: self.iso_freq_var.set(self.isochronic_frequency) 
        self._params_changed_by_ui() 

    def get_params_as_dict(self):
        """Returns channel parameters as a dictionary for saving."""
        self._update_internal_params_from_vars() # Ensure current
        return {
            "id": self.channel_id,
            "is_active": self.is_active,
            "frequency": self.frequency,
            "amplitude": self.amplitude,
            "is_iso_active": self.is_iso_active,
            "isochronic_frequency": self.isochronic_frequency,
            "x_pos": self.x_pos,
            "y_pos": self.y_pos,
            "z_pos": self.z_pos
        }

    def load_params_from_dict(self, data_dict):
        """Loads channel parameters from a dictionary."""
        self.is_active_var.set(data_dict.get("is_active", True))
        self.freq_var.set(data_dict.get("frequency", DEFAULT_FREQ))
        self.amp_var.set(data_dict.get("amplitude", DEFAULT_AMP))
        self.iso_active_var.set(data_dict.get("is_iso_active", False))
        self.iso_freq_var.set(data_dict.get("isochronic_frequency", DEFAULT_ISO_FREQ))
        self.x_pos_var.set(data_dict.get("x_pos", DEFAULT_POS))
        self.y_pos_var.set(data_dict.get("y_pos", DEFAULT_POS))
        self.z_pos_var.set(data_dict.get("z_pos", DEFAULT_POS))
        
        self._update_internal_params_from_vars()
        self._update_iso_entry_state() 
        self.update_waveform_preview() 

    def get_params(self): # Used for audio engine
        self._update_internal_params_from_vars()
        effective_iso_freq = self.isochronic_frequency if self.is_iso_active and self.isochronic_frequency > 0.001 else 0.0
        return self.frequency, self.amplitude, self.is_active, effective_iso_freq, self.x_pos, self.y_pos, self.z_pos

    def reset(self):
        self.is_active_var.set(True); self.freq_var.set(DEFAULT_FREQ); self.amp_var.set(DEFAULT_AMP)
        self.iso_active_var.set(False); self.iso_freq_var.set(DEFAULT_ISO_FREQ)
        self.x_pos_var.set(DEFAULT_POS); self.y_pos_var.set(DEFAULT_POS); self.z_pos_var.set(DEFAULT_POS)
        self._update_internal_params_from_vars(); self._update_iso_entry_state(); 
        self._params_changed_by_ui() 

    def set_controls_state(self, new_state):
        controls_to_toggle = [self.active_check, self.freq_slider, self.freq_entry, self.amp_slider, 
                              self.iso_active_check, self.x_pos_slider, self.y_pos_slider, self.z_pos_slider]
        for control in controls_to_toggle: control.config(state=new_state)
        iso_entry_state = tk.NORMAL if new_state == tk.NORMAL and self.iso_active_var.get() else tk.DISABLED
        self.iso_freq_entry.config(state=iso_entry_state)
        self.iso_display_label.config(state=iso_entry_state if new_state == tk.NORMAL else tk.DISABLED)
        if new_state == tk.NORMAL and not self.iso_active_var.get(): self.iso_freq_label_var.set("--- Hz")
    
    def update_waveform_preview(self):
        if not hasattr(self, 'canvas_preview'): return 
        freq = self.frequency; amp = self.amplitude; is_active_main = self.is_active
        iso_freq_val = self.isochronic_frequency; is_iso_module_active = self.is_iso_active
        effective_iso_freq = iso_freq_val if is_active_main and is_iso_module_active and iso_freq_val > 0.001 else 0.0
        num_samples_preview = int(SAMPLE_RATE * CHANNEL_PREVIEW_DURATION_SEC)
        t_preview = np.linspace(0, CHANNEL_PREVIEW_DURATION_SEC, num_samples_preview, endpoint=False, dtype=np.float64)
        if not is_active_main or amp < 0.001 or freq <=0: 
            preview_signal = np.zeros_like(t_preview); y_limit = max(MAX_AMP * 0.1, 0.01) 
        else:
            preview_signal = amp * np.sin(2 * np.pi * freq * t_preview)
            if effective_iso_freq > 0.001: preview_signal *= np.where((effective_iso_freq * t_preview)%1.0 < 0.5, 1.0, 0.0)
            y_limit = max(amp * 1.1, 0.01)
        self.preview_line.set_data(t_preview, preview_signal); self.ax_preview.set_ylim(-y_limit, y_limit)
        self.ax_preview.set_xlim(0, CHANNEL_PREVIEW_DURATION_SEC); self.canvas_preview.draw_idle() 

class AudioEntrainmentApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("3D Audio Entrainment Platform")
        self.root.geometry("900x800") 

        self.channels = []
        self.audio_stream = None
        self.is_playing = False 
        self.playback_params_lock = threading.Lock()
        self.current_time_offset = 0.0
        self.active_channel_audio_params = []
        self.displayed_channels_count = tk.IntVar(value=NUM_CHANNELS)
        self.channel_points_viz = [] 

        # Recording state variables
        self.is_recording = False
        self.is_recording_paused = False
        self.recording_duration_var = tk.StringVar(value="60") 
        self.recorded_frames = []
        self.recording_thread = None
        self.recording_filepath = ""
        self.recording_elapsed_time = 0.0
        self.recording_pause_start_time = 0.0
        self.volume_keyframes = [] 


        style = ttk.Style(); style.theme_use('clam') 
        self.root.configure(background='#F0F0F0') 
        
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill="both", padx=5, pady=5)

        self.main_controls_tab = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(self.main_controls_tab, text="Controls & Visualization")
        self._setup_main_controls_tab() 

        self.data_io_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.data_io_tab, text="Data I/O & Setup")
        self._setup_data_io_tab() 

        self.recording_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.recording_tab, text="Recording")
        self._setup_recording_tab() 
        
        self.update_active_channel_audio_params()
        self.record_and_display_waveform() 
        self.update_visualization_plot() 
        self.update_config_display_text() 
        self.update_volume_automation_graph() 

    def _setup_main_controls_tab(self):
        self.controls_frame = ttk.Frame(self.main_controls_tab, padding="5"); 
        self.controls_frame.pack(side=tk.TOP, fill="x", pady=(0,5)) 
        main_content_frame = ttk.Frame(self.main_controls_tab)
        main_content_frame.pack(side=tk.TOP, fill="both", expand=True, pady=(0,5))
        channel_controls_width_approx = 420 
        self.channels_outer_frame = ttk.LabelFrame(main_content_frame, text="Channel Controls", padding="5") 
        self.channels_outer_frame.pack(side=tk.LEFT, fill="y", expand=False, padx=(0, 5))
        self.channels_canvas = tk.Canvas(self.channels_outer_frame, borderwidth=0, background="#ffffff", width=channel_controls_width_approx - 30) 
        self.channels_scrollbar = ttk.Scrollbar(self.channels_outer_frame, orient="vertical", command=self.channels_canvas.yview)
        self.scrollable_channels_frame = ttk.Frame(self.channels_canvas, padding="5")
        self.scrollable_channels_frame.bind("<Configure>", lambda e: self.channels_canvas.configure(scrollregion=self.channels_canvas.bbox("all")))
        self.channels_canvas.create_window((0, 0), window=self.scrollable_channels_frame, anchor="nw")
        self.channels_canvas.configure(yscrollcommand=self.channels_scrollbar.set)
        self.channels_canvas.pack(side="left", fill="y", expand=False); self.channels_scrollbar.pack(side="right", fill="y")
        self.channels_canvas.bind('<Enter>', lambda e: self._bind_mousewheel(e, self.channels_canvas))
        self.channels_canvas.bind('<Leave>', lambda e: self._unbind_mousewheel(e, self.channels_canvas))
        self.visualization_frame = ttk.LabelFrame(main_content_frame, text="3D Spatial Preview", padding="5")
        self.visualization_frame.pack(side=tk.LEFT, fill="both", expand=True, padx=(5, 0))
        self.fig_viz, self.ax_viz = plt.subplots(figsize=(4,4)) 
        self.fig_viz.patch.set_facecolor('#F0F0F0'); self.ax_viz.set_facecolor('#FFFFFF')
        self.ax_viz.set_title("Channel Positions (Top-Down)", fontsize=9); self.ax_viz.set_xlabel("X (Left/Right)", fontsize=8); self.ax_viz.set_ylabel("Y (Back/Front)", fontsize=8)
        self.ax_viz.set_xlim(-MAX_POS*1.2, MAX_POS*1.2); self.ax_viz.set_ylim(-MAX_POS*1.2, MAX_POS*1.2)
        self.ax_viz.axhline(0, color='grey', lw=0.5, linestyle='--'); self.ax_viz.axvline(0, color='grey', lw=0.5, linestyle='--')
        self.ax_viz.set_aspect('equal', adjustable='box')
        self.listener_representation = plt.Circle((0,0), 0.08, color='darkgrey', alpha=0.6, label="Listener") 
        self.ax_viz.add_artist(self.listener_representation)
        self.canvas_viz = FigureCanvasTkAgg(self.fig_viz, master=self.visualization_frame)
        self.canvas_viz_widget = self.canvas_viz.get_tk_widget(); self.canvas_viz_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.fig_viz.subplots_adjust(left=0.15, bottom=0.15, right=0.85, top=0.85); self.canvas_viz.draw()
        self.plot_frame = ttk.LabelFrame(self.main_controls_tab, text="Combined Output Waveform (L+R)/2", padding="5") 
        self.plot_frame.pack(side=tk.TOP, fill="both", expand=True, pady=(5,0)) 
        self.play_button = ttk.Button(self.controls_frame, text="Play", command=self.play_audio, width=8); self.play_button.pack(side=tk.LEFT, padx=3)
        self.stop_button = ttk.Button(self.controls_frame, text="Stop", command=self.stop_audio, state=tk.DISABLED, width=8); self.stop_button.pack(side=tk.LEFT, padx=3)
        self.record_button = ttk.Button(self.controls_frame, text="Display Waveform", command=self.record_and_display_waveform, width=18); self.record_button.pack(side=tk.LEFT, padx=3)
        self.reset_button = ttk.Button(self.controls_frame, text="Reset All", command=self.reset_all_channels, width=10); self.reset_button.pack(side=tk.LEFT, padx=3)
        ttk.Label(self.controls_frame, text="Channels:").pack(side=tk.LEFT, padx=(10, 2))
        self.channel_count_combo = ttk.Combobox(self.controls_frame, textvariable=self.displayed_channels_count, values=[str(i) for i in range(1, NUM_CHANNELS + 1)], width=3, state="readonly")
        self.channel_count_combo.pack(side=tk.LEFT, padx=(0, 3)); self.channel_count_combo.bind("<<ComboboxSelected>>", self.on_channel_count_changed)
        for i in range(NUM_CHANNELS):
            channel = AudioChannel(self.scrollable_channels_frame, i, self)
            self.channels.append(channel)
        self.fig, self.ax = plt.subplots(figsize=(7, 2.0)); self.fig.patch.set_facecolor('#F0F0F0'); self.ax.set_facecolor('#FFFFFF') 
        self.ax.set_title("Combined Output (L+R)/2", fontsize=9); self.ax.set_xlabel("Time (s)", fontsize=8); self.ax.set_ylabel("Amplitude", fontsize=8)
        self.ax.tick_params(axis='both', which='major', labelsize=7); self.ax.grid(True, linestyle=':', alpha=0.7); self.line, = self.ax.plot([], [], lw=1, color='dodgerblue')
        self.ax.set_ylim(-1.1, 1.1); self.plot_canvas = FigureCanvasTkAgg(self.fig, master=self.plot_frame)
        self.plot_canvas_widget = self.plot_canvas.get_tk_widget(); self.plot_canvas_widget.pack(fill=tk.BOTH, expand=True, padx=5, pady=2)
        self.fig.tight_layout(pad=0.5); self.plot_canvas.draw()

    def _setup_data_io_tab(self):
        data_controls_frame = ttk.Frame(self.data_io_tab) # Renamed for clarity
        data_controls_frame.pack(pady=10, fill="x")
        
        self.save_button = ttk.Button(data_controls_frame, text="Save Configuration", command=self.save_configuration, width=20)
        self.save_button.pack(side=tk.LEFT, padx=5)
        self.load_button = ttk.Button(data_controls_frame, text="Load Configuration", command=self.load_configuration, width=20)
        self.load_button.pack(side=tk.LEFT, padx=5)
        self.apply_json_text_button = ttk.Button(data_controls_frame, text="Apply JSON from Text", command=self.apply_json_from_text_area, width=22)
        self.apply_json_text_button.pack(side=tk.LEFT, padx=5)

        config_display_frame = ttk.LabelFrame(self.data_io_tab, text="Current Configuration (JSON) - Editable", padding=5)
        config_display_frame.pack(fill="both", expand=True, pady=5)
        self.config_text = tk.Text(config_display_frame, wrap=tk.WORD, height=15, width=70, state=tk.NORMAL) # Editable
        self.config_text_scroll = ttk.Scrollbar(config_display_frame, orient=tk.VERTICAL, command=self.config_text.yview)
        self.config_text.configure(yscrollcommand=self.config_text_scroll.set)
        self.config_text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.config_text.pack(side=tk.LEFT, fill="both", expand=True)

    def _setup_recording_tab(self):
        duration_frame = ttk.Frame(self.recording_tab); duration_frame.pack(pady=5, fill="x")
        ttk.Label(duration_frame, text="Total Recording Time (seconds):").pack(side=tk.LEFT, padx=5)
        self.recording_duration_entry = ttk.Entry(duration_frame, textvariable=self.recording_duration_var, width=10)
        self.recording_duration_entry.pack(side=tk.LEFT, padx=5)
        self.recording_duration_var.trace_add("write", lambda *args: self.update_volume_automation_graph())

        rec_controls_frame = ttk.Frame(self.recording_tab); rec_controls_frame.pack(pady=5, fill="x")
        self.start_rec_button = ttk.Button(rec_controls_frame, text="Start Recording", command=self.start_recording, width=18)
        self.start_rec_button.pack(side=tk.LEFT, padx=2)
        self.pause_rec_button = ttk.Button(rec_controls_frame, text="Pause Recording", command=self.toggle_pause_recording, width=18, state=tk.DISABLED)
        self.pause_rec_button.pack(side=tk.LEFT, padx=2)
        self.stop_rec_button = ttk.Button(rec_controls_frame, text="Stop Recording", command=self.stop_recording, width=18, state=tk.DISABLED)
        self.stop_rec_button.pack(side=tk.LEFT, padx=2)
        self.clear_keyframes_button = ttk.Button(rec_controls_frame, text="Clear Keyframes", command=self.clear_volume_keyframes, width=18)
        self.clear_keyframes_button.pack(side=tk.LEFT, padx=2)

        progress_frame = ttk.Frame(self.recording_tab); progress_frame.pack(pady=5, fill="x")
        self.recording_progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=300, mode="determinate")
        self.recording_progress_bar.pack(pady=2, fill="x")
        self.recording_status_label = ttk.Label(progress_frame, text="Status: Idle")
        self.recording_status_label.pack(pady=2)

        automation_graph_frame = ttk.LabelFrame(self.recording_tab, text="Volume Automation", padding=5)
        automation_graph_frame.pack(pady=10, fill="both", expand=True)
        self.fig_vol_auto, self.ax_vol_auto = plt.subplots(figsize=(6, 2.5))
        self.fig_vol_auto.patch.set_facecolor('#F0F0F0'); self.ax_vol_auto.set_facecolor('#FFFFFF')
        self.ax_vol_auto.set_title("Volume (%) vs. Time (s)", fontsize=9); self.ax_vol_auto.set_xlabel("Time (s)", fontsize=8)
        self.ax_vol_auto.set_ylabel("Volume (%)", fontsize=8); self.ax_vol_auto.set_ylim(0, 105)
        self.ax_vol_auto.grid(True, linestyle=':', alpha=0.7)
        self.vol_auto_line, = self.ax_vol_auto.plot([], [], 'bo-', markersize=4, picker=True, pickradius=5) # picker for click detection
        self.canvas_vol_auto = FigureCanvasTkAgg(self.fig_vol_auto, master=automation_graph_frame)
        self.canvas_vol_auto_widget = self.canvas_vol_auto.get_tk_widget(); self.canvas_vol_auto_widget.pack(fill=tk.BOTH, expand=True)
        self.fig_vol_auto.tight_layout(pad=0.5)
        self.canvas_vol_auto.mpl_connect('button_press_event', self._on_volume_graph_click)
        self.canvas_vol_auto.draw()

    def _bind_mousewheel(self, event, widget): widget.bind_all("<MouseWheel>", lambda e: self._on_mousewheel(e, widget))
    def _unbind_mousewheel(self, event, widget): widget.unbind_all("<MouseWheel>")
    def _on_mousewheel(self, event, canvas_widget):
        if event.delta: canvas_widget.yview_scroll(int(-1*(event.delta/120)), "units")
        elif event.num == 4: canvas_widget.yview_scroll(-1, "units")
        elif event.num == 5: canvas_widget.yview_scroll(1, "units")

    def on_channel_count_changed(self, event=None):
        new_count = self.displayed_channels_count.get()
        for i, ch_obj in enumerate(self.channels):
            if i < new_count:
                if not ch_obj.frame.winfo_manager(): ch_obj.frame.pack(pady=2, padx=5, fill="x")
            else: ch_obj.frame.pack_forget()
        self.update_active_channel_audio_params() 
        if not self.is_playing: self.record_and_display_waveform() 
        self.update_visualization_plot() 
        self.update_config_display_text()
        self.scrollable_channels_frame.update_idletasks(); self.channels_canvas.config(scrollregion=self.channels_canvas.bbox("all"))

    def notify_param_change(self):
        self.update_active_channel_audio_params()
        if not self.is_playing: self.record_and_display_waveform() 
        self.update_visualization_plot() 
        self.update_config_display_text()

    def update_active_channel_audio_params(self):
        with self.playback_params_lock:
            self.active_channel_audio_params = []
            num_to_process = self.displayed_channels_count.get()
            for i in range(num_to_process): 
                ch = self.channels[i]
                freq, amp, active, iso_freq, x, y, z = ch.get_params()
                if active and amp > 0.001:
                    self.active_channel_audio_params.append({'id': ch.channel_id, 'freq': freq, 'amp': amp, 'iso_freq': iso_freq, 'x': x, 'y': y, 'z': z})

    def update_visualization_plot(self):
        if not hasattr(self, 'ax_viz'): return
        for artist in self.channel_points_viz: artist.remove()
        self.channel_points_viz.clear()
        params_for_viz = []
        with self.playback_params_lock: 
            num_to_display = self.displayed_channels_count.get()
            for i in range(num_to_display):
                ch = self.channels[i]; _f,_a,active,_iso,x,y,z = ch.get_params() 
                if active and _a > 0.001: params_for_viz.append({'id':ch.channel_id,'x':x,'y':y,'z':z,'amp':_a})
        if not params_for_viz: 
            if hasattr(self, 'canvas_viz'): self.canvas_viz.draw_idle()
            return
        cmap = plt.get_cmap('tab10')
        text_label_color = 'black' 
        for p_data in params_for_viz:
            x,y,z = p_data['x'],p_data['y'],p_data['z']; channel_id_text = str(p_data['id']+1)
            min_s=25; max_s=125; norm_z=(z-MIN_POS)/(MAX_POS-MIN_POS); marker_s=min_s+norm_z*(max_s-min_s)
            point_color = cmap(p_data['id']%10)
            point_collection = self.ax_viz.scatter([x],[y],s=marker_s,color=point_color,alpha=0.75,edgecolors='black',linewidth=0.5,zorder=5)
            self.channel_points_viz.append(point_collection)
            text_label = self.ax_viz.text(x,y,channel_id_text,fontsize=7,color=text_label_color,ha='center',va='center',zorder=10) 
            self.channel_points_viz.append(text_label)
        if hasattr(self, 'canvas_viz'): self.canvas_viz.draw_idle()

    def _generate_audio_block(self, num_frames, time_offset_samples, apply_automation=False):
        with self.playback_params_lock: current_params = list(self.active_channel_audio_params)
        t_abs = (time_offset_samples + np.arange(num_frames)) / SAMPLE_RATE 
        left_mix = np.zeros(num_frames, dtype=np.float32); right_mix = np.zeros(num_frames, dtype=np.float32)
        if not current_params: return np.zeros((num_frames, 2), dtype=np.float32) 
        total_potential_amp_sum = sum(p['amp'] for p in current_params if p['amp'] > 0.001)
        for params in current_params:
            freq, amp, iso_freq, x, y, z = params['freq'],params['amp'],params['iso_freq'],params['x'],params['y'],params['z']
            mono_signal = amp*np.sin(2*np.pi*freq*t_abs.astype(np.float64))
            if iso_freq > 0.001: mono_signal *= np.where((iso_freq*t_abs.astype(np.float64))%1.0 < 0.5, 1.0, 0.0)
            distance=np.sqrt(x**2+y**2+z**2); dist_gain=1.0/(1.0+distance*0.5); y_gain=0.75+0.25*y
            processed_signal=mono_signal.astype(np.float32)*dist_gain*y_gain
            pan_angle=(x+1.0)*np.pi/4.0; gain_left=np.cos(pan_angle); gain_right=np.sin(pan_angle)
            left_mix+=processed_signal*gain_left; right_mix+=processed_signal*gain_right
        if total_potential_amp_sum > 1.0: left_mix/=total_potential_amp_sum; right_mix/=total_potential_amp_sum
        stereo_out = np.zeros((num_frames, 2), dtype=np.float32)
        stereo_out[:, 0] = left_mix; stereo_out[:, 1] = right_mix
        if apply_automation:
            try: total_rec_duration = float(self.recording_duration_var.get())
            except ValueError: total_rec_duration = 0 # Should not happen if entry is validated
            if total_rec_duration > 0:
                for i in range(num_frames):
                    current_sample_time = (time_offset_samples + i) / SAMPLE_RATE
                    automation_gain = self._get_automation_volume_at_time(current_sample_time, total_rec_duration)
                    stereo_out[i, :] *= automation_gain 
        stereo_out[:, 0] = np.clip(stereo_out[:, 0], -0.999, 0.999)
        stereo_out[:, 1] = np.clip(stereo_out[:, 1], -0.999, 0.999)
        return stereo_out

    def audio_callback(self, outdata, frames, time_info, status):
        if status: print(f"Audio CB Status: {status}", flush=True)
        outdata[:] = self._generate_audio_block(frames, self.current_time_offset, apply_automation=False)
        self.current_time_offset += frames

    def play_audio(self):
        if self.is_playing or self.is_recording: return 
        self.update_active_channel_audio_params()
        with self.playback_params_lock:
            if not self.active_channel_audio_params: self.show_message("Playback Info", "No active channels."); return
        try:
            self.current_time_offset = 0
            self.audio_stream = sd.OutputStream(samplerate=SAMPLE_RATE, channels=2, callback=self.audio_callback, blocksize=int(SAMPLE_RATE*BUFFER_DURATION), dtype='float32')
            self.audio_stream.start(); self.is_playing = True
            ui_state_playback(self, tk.DISABLED, tk.DISABLED) 
            print("Audio playback started (Stereo).")
        except Exception as e:
            print(f"Error starting audio stream: {e}"); self.show_message("Audio Error", f"Could not start: {e}")
            if self.audio_stream: self.audio_stream.close() 
            self.audio_stream = None; self.is_playing = False
            ui_state_playback(self, tk.NORMAL, "readonly")

    def stop_audio(self):
        if not self.is_playing or not self.audio_stream: return
        try: self.audio_stream.stop(); self.audio_stream.close(); print("Audio playback stopped.")
        except Exception as e: print(f"Error stopping: {e}"); self.show_message("Audio Error", f"Error stopping: {e}")
        finally:
            self.audio_stream = None; self.is_playing = False
            ui_state_playback(self, tk.NORMAL, "readonly")
            self.update_active_channel_audio_params()

    def record_and_display_waveform(self): 
        if self.is_playing or self.is_recording: return 
        self.update_active_channel_audio_params() 
        num_samples=int(SAMPLE_RATE*PLOT_DURATION); t_plot=np.linspace(0,PLOT_DURATION,num_samples,endpoint=False,dtype=np.float64)
        stereo_plot_data = self._generate_audio_block(num_samples, 0, apply_automation=False) 
        averaged_plot_signal = (stereo_plot_data[:,0] + stereo_plot_data[:,1]) / 2.0
        if not self.active_channel_audio_params: 
            if hasattr(self, 'line'): self.line.set_data([],[])
            if hasattr(self, 'ax'): self.ax.set_ylim(-1.1,1.1); self.ax.set_title("Combined Waveform (No active ch.)",fontsize=9)
            if hasattr(self, 'plot_canvas'): self.plot_canvas.draw_idle()
            return
        actual_max_amp=np.max(np.abs(averaged_plot_signal)) if averaged_plot_signal.size>0 else 1.0
        plot_y_abs_max=max(0.1, actual_max_amp if actual_max_amp > 0.001 else 1.0)
        if hasattr(self, 'ax'): self.ax.set_ylim(-plot_y_abs_max*1.15, plot_y_abs_max*1.15)
        if hasattr(self, 'line'): self.line.set_data(t_plot, averaged_plot_signal)
        if hasattr(self, 'ax'): self.ax.set_title(f"Combined Waveform (L+R)/2 ({len(self.active_channel_audio_params)} ch.)",fontsize=9)
        if hasattr(self, 'plot_canvas'): self.plot_canvas.draw_idle()

    def reset_all_channels(self):
        if self.is_playing or self.is_recording: self.show_message("Reset Info", "Stop audio/recording first."); return
        for channel in self.channels: channel.reset() 
        self.clear_volume_keyframes() 
        self.update_config_display_text() 
        print("All channels reset.")

    def show_message(self, title, message):
        messagebox.showinfo(title, message, parent=self.root)

    def on_closing(self): 
        if self.is_recording: self.stop_recording(force_stop=True) 
        if self.is_playing: self.stop_audio()
        print("Closing..."); 
        self.root.destroy()

    def get_current_configuration_dict(self):
        config = {
            "app_settings": { 
                "displayed_channels": self.displayed_channels_count.get(),
                "recording_duration": self.recording_duration_var.get(),
                "volume_keyframes": self.volume_keyframes
            },
            "channels": [ch.get_params_as_dict() for ch in self.channels] 
        }
        return config

    def update_config_display_text(self):
        if not hasattr(self, 'config_text'): return
        try:
            current_config = self.get_current_configuration_dict()
            config_json = json.dumps(current_config, indent=2)
            # self.config_text.configure(state=tk.NORMAL) # Keep it normal for editing
            self.config_text.delete(1.0, tk.END); self.config_text.insert(tk.END, config_json)
            # self.config_text.configure(state=tk.DISABLED) # No longer disable
        except Exception as e:
            print(f"Error updating config display: {e}")
            # self.config_text.configure(state=tk.NORMAL)
            self.config_text.delete(1.0, tk.END); self.config_text.insert(tk.END, f"Error: {e}")
            # self.config_text.configure(state=tk.DISABLED)

    def save_configuration(self):
        if self.is_playing or self.is_recording: self.show_message("Save Error", "Stop audio/recording first."); return
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")], title="Save Configuration As", parent=self.root)
        if not filepath: return
        try:
            # Get data from text area if user was editing, otherwise from current app state
            # For now, always save from current app state for consistency.
            config_data = self.get_current_configuration_dict()
            with open(filepath, 'w') as f: json.dump(config_data, f, indent=2)
            self.show_message("Save Successful", f"Configuration saved to:\n{filepath}")
        except Exception as e: self.show_message("Save Error", f"Failed to save: {e}"); print(f"Error saving: {e}")

    def _process_loaded_config_data(self, loaded_data):
        """Helper function to process and apply loaded configuration data."""
        if "app_settings" not in loaded_data or "channels" not in loaded_data:
            raise ValueError("Invalid config: Missing 'app_settings' or 'channels'.")
        if not isinstance(loaded_data["channels"], list):
            raise ValueError("Invalid config: 'channels' should be a list.")
        
        app_settings = loaded_data.get("app_settings", {})
        self.displayed_channels_count.set(app_settings.get("displayed_channels", NUM_CHANNELS))
        self.recording_duration_var.set(app_settings.get("recording_duration", "60"))
        self.volume_keyframes = app_settings.get("volume_keyframes", [])
        self.volume_keyframes.sort() 
        self.on_channel_count_changed() 
        self.update_volume_automation_graph() 

        loaded_channels_data = loaded_data["channels"]
        for i in range(NUM_CHANNELS):
            if i < len(loaded_channels_data):
                ch_data = loaded_channels_data[i]
                if ch_data.get("id") == self.channels[i].channel_id: self.channels[i].load_params_from_dict(ch_data)
                else: print(f"Warning: Ch ID mismatch {i}. Loading by order."); self.channels[i].load_params_from_dict(ch_data) 
            else: self.channels[i].reset() 
        self.notify_param_change() # This will update config text display too

    def load_configuration(self):
        if self.is_playing or self.is_recording: self.show_message("Load Error", "Stop audio/recording first."); return
        filepath = filedialog.askopenfilename(defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")], title="Load Configuration", parent=self.root)
        if not filepath: return
        try:
            with open(filepath, 'r') as f: loaded_data = json.load(f)
            self._process_loaded_config_data(loaded_data)
            self.show_message("Load Successful", f"Loaded from:\n{filepath}")
        except Exception as e: self.show_message("Load Error", f"Failed to load from file: {e}"); print(f"Error loading: {e}")

    def apply_json_from_text_area(self):
        if self.is_playing or self.is_recording:
            self.show_message("Action Denied", "Stop audio/recording before applying changes.")
            return
        try:
            json_string = self.config_text.get(1.0, tk.END)
            loaded_data = json.loads(json_string)
            self._process_loaded_config_data(loaded_data)
            self.show_message("Apply Successful", "Configuration applied from text area.")
            # notify_param_change in _process_loaded_config_data also calls update_config_display_text,
            # which will re-format/update the JSON in the text area.
        except json.JSONDecodeError:
            self.show_message("JSON Error", "Invalid JSON in text area. Please correct and try again.")
        except Exception as e:
            self.show_message("Apply Error", f"Failed to apply configuration: {e}")
            print(f"Error applying JSON from text: {e}")


    def start_recording(self):
        if self.is_playing: self.show_message("Recording Error", "Stop live playback first."); return
        if self.is_recording: self.show_message("Recording Info", "Already recording."); return
        try:
            total_duration_sec = float(self.recording_duration_var.get())
            if total_duration_sec <= 0: self.show_message("Input Error", "Duration > 0."); return
        except ValueError: self.show_message("Input Error", "Invalid duration."); return
        self.recording_filepath = filedialog.asksaveasfilename(defaultextension=".wav", filetypes=[("WAV files", "*.wav")], title="Save Recording As", parent=self.root)
        if not self.recording_filepath: return
        self.is_recording = True; self.is_recording_paused = False; self.recorded_frames = []
        self.recording_elapsed_time = 0.0; self.recording_pause_start_time = 0.0
        self.update_active_channel_audio_params() 
        self.recording_status_label.config(text="Status: Recording...")
        self.start_rec_button.config(state=tk.DISABLED); self.pause_rec_button.config(text="Pause Recording", state=tk.NORMAL)
        self.stop_rec_button.config(state=tk.NORMAL); self.recording_duration_entry.config(state=tk.DISABLED)
        self.clear_keyframes_button.config(state=tk.DISABLED)
        ui_state_main_controls(self, tk.DISABLED) 
        self.recording_thread = threading.Thread(target=self._recording_process_thread, args=(total_duration_sec,), daemon=True)
        self.recording_thread.start()

    def toggle_pause_recording(self):
        if not self.is_recording: return
        if self.is_recording_paused: 
            self.is_recording_paused = False
            self.recording_status_label.config(text="Status: Recording...")
            self.pause_rec_button.config(text="Pause Recording")
        else: 
            self.is_recording_paused = True
            self.recording_status_label.config(text="Status: Paused")
            self.pause_rec_button.config(text="Resume Recording")
            
    def stop_recording(self, force_stop=False):
        if not self.is_recording and not force_stop: return
        self.is_recording = False 
        if self.recording_thread and self.recording_thread.is_alive() and not force_stop:
            try: self.recording_thread.join(timeout=2.0) 
            except Exception as e: print(f"Error joining recording thread: {e}")
        if self.recorded_frames and not force_stop: 
            try:
                final_audio_data = np.concatenate(self.recorded_frames, axis=0)
                soundfile.write(self.recording_filepath, final_audio_data, SAMPLE_RATE)
                self.show_message("Recording Complete", f"Audio saved to:\n{self.recording_filepath}")
            except Exception as e: self.show_message("Save Error", f"Failed to save: {e}"); print(f"Error saving: {e}")
        elif force_stop and self.recording_filepath: self.show_message("Recording Aborted", f"Recording to {self.recording_filepath} stopped.")
        elif force_stop: self.show_message("Recording Aborted", "Recording stopped.")
        self.recording_status_label.config(text="Status: Idle")
        self.start_rec_button.config(state=tk.NORMAL); self.pause_rec_button.config(text="Pause Recording", state=tk.DISABLED)
        self.stop_rec_button.config(state=tk.DISABLED); self.recording_duration_entry.config(state=tk.NORMAL)
        self.clear_keyframes_button.config(state=tk.NORMAL)
        self.recording_progress_bar['value'] = 0; self.recorded_frames = []; self.recording_filepath = ""
        self.recording_thread = None; ui_state_main_controls(self, tk.NORMAL) 

    def _recording_process_thread(self, total_duration_sec):
        recording_buffer_frames = int(SAMPLE_RATE * RECORDING_BUFFER_SIZE_SEC)
        current_recorded_samples = 0
        total_samples_to_record = int(total_duration_sec * SAMPLE_RATE)
        while self.is_recording and current_recorded_samples < total_samples_to_record:
            if not self.is_recording_paused:
                loop_start_time = time.monotonic()
                frames_this_iteration = min(recording_buffer_frames, total_samples_to_record - current_recorded_samples)
                if frames_this_iteration <= 0: break
                audio_block = self._generate_audio_block(frames_this_iteration, current_recorded_samples, apply_automation=True)
                self.recorded_frames.append(audio_block)
                current_recorded_samples += frames_this_iteration
                progress = (current_recorded_samples / total_samples_to_record) * 100
                self.root.after(0, lambda p=progress: self.recording_progress_bar.config(value=p))
                elapsed_loop = time.monotonic() - loop_start_time
                time.sleep(max(0, RECORDING_BUFFER_SIZE_SEC - elapsed_loop))
            else: time.sleep(0.1) 
        self.root.after(0, self.stop_recording, False) 

    def _on_volume_graph_click(self, event):
        if event.inaxes != self.ax_vol_auto or self.is_recording: return 
        clicked_time = event.xdata; clicked_volume = event.ydata
        if clicked_time is None or clicked_volume is None: return
        try: total_duration = float(self.recording_duration_var.get())
        except ValueError: total_duration = 60.0 
        clicked_time = max(0, min(clicked_time, total_duration)); clicked_volume = max(0, min(clicked_volume, 100))
        self.volume_keyframes.append((clicked_time, clicked_volume)); self.volume_keyframes.sort() 
        self.update_volume_automation_graph(); self.update_config_display_text() 

    def update_volume_automation_graph(self):
        if not hasattr(self, 'ax_vol_auto'): return
        self.ax_vol_auto.clear(); self.ax_vol_auto.set_title("Volume (%) vs. Time (s)", fontsize=9)
        self.ax_vol_auto.set_xlabel("Time (s)", fontsize=8); self.ax_vol_auto.set_ylabel("Volume (%)", fontsize=8)
        self.ax_vol_auto.set_ylim(0, 105); self.ax_vol_auto.grid(True, linestyle=':', alpha=0.7)
        try: total_duration = float(self.recording_duration_var.get())
        except ValueError: total_duration = 60.0 
        if total_duration <=0: total_duration = 0.1 # Prevent zero or negative xlim
        self.ax_vol_auto.set_xlim(0, total_duration)
        
        plot_keyframes = list(self.volume_keyframes) 
        if not plot_keyframes: plot_keyframes = [(0, 100.0), (total_duration, 100.0)]
        else:
            if plot_keyframes[0][0] > 0: plot_keyframes.insert(0, (0, plot_keyframes[0][1]))
            if plot_keyframes[-1][0] < total_duration: plot_keyframes.append((total_duration, plot_keyframes[-1][1]))
        plot_keyframes.sort()
        times = [kf[0] for kf in plot_keyframes]; volumes = [kf[1] for kf in plot_keyframes]
        if self.volume_keyframes:
            user_times = [kf[0] for kf in self.volume_keyframes]; user_volumes = [kf[1] for kf in self.volume_keyframes]
            self.ax_vol_auto.plot(user_times, user_volumes, 'bo', markersize=5)
        self.vol_auto_line, = self.ax_vol_auto.plot(times, volumes, 'b-')
        if hasattr(self, 'canvas_vol_auto'): self.canvas_vol_auto.draw_idle()

    def clear_volume_keyframes(self):
        if self.is_recording: self.show_message("Action Denied", "Cannot clear keyframes while recording."); return
        self.volume_keyframes.clear(); self.update_volume_automation_graph(); self.update_config_display_text()
        self.show_message("Keyframes Cleared", "Volume automation keyframes cleared.")

    def _get_automation_volume_at_time(self, current_time_sec, total_duration_sec):
        if not self.volume_keyframes: return 1.0 
        working_keyframes = list(self.volume_keyframes)
        # Ensure start and end keyframes for interpolation range
        if not working_keyframes or working_keyframes[0][0] > 0:
            first_vol = working_keyframes[0][1] if working_keyframes else 100.0
            working_keyframes.insert(0, (0, first_vol))
        if working_keyframes[-1][0] < total_duration_sec: # Make sure this uses actual total_duration_sec
            last_vol = working_keyframes[-1][1]
            working_keyframes.append((total_duration_sec, last_vol))
        working_keyframes.sort() 
        
        if current_time_sec <= working_keyframes[0][0]: return working_keyframes[0][1] / 100.0
        if current_time_sec >= working_keyframes[-1][0]: return working_keyframes[-1][1] / 100.0
        
        for i in range(len(working_keyframes) - 1):
            kf1_time, kf1_vol = working_keyframes[i]; kf2_time, kf2_vol = working_keyframes[i+1]
            if kf1_time <= current_time_sec <= kf2_time:
                if kf2_time == kf1_time: return kf1_vol / 100.0
                slope = (kf2_vol - kf1_vol) / (kf2_time - kf1_time)
                interpolated_vol = kf1_vol + slope * (current_time_sec - kf1_time)
                return max(0, min(interpolated_vol, 100.0)) / 100.0
        return 1.0 # Fallback, should ideally not be reached if logic above is correct


def ui_state_main_controls(app, state):
    app.play_button.config(state=state)
    app.record_button.config(state=state) 
    app.reset_button.config(state=state)
    app.channel_count_combo.config(state="readonly" if state == tk.NORMAL else tk.DISABLED)
    if hasattr(app, 'save_button'): app.save_button.config(state=state)
    if hasattr(app, 'load_button'): app.load_button.config(state=state)
    if hasattr(app, 'apply_json_text_button'): app.apply_json_text_button.config(state=state)


def ui_state_playback(app, channel_controls_state, combo_box_state): 
    app.play_button.config(state=tk.DISABLED if channel_controls_state == tk.DISABLED else tk.NORMAL)
    app.stop_button.config(state=tk.NORMAL if channel_controls_state == tk.DISABLED else tk.DISABLED)
    app.record_button.config(state=channel_controls_state)
    app.reset_button.config(state=channel_controls_state)
    app.channel_count_combo.config(state=combo_box_state)
    
    if hasattr(app, 'start_rec_button'):
        rec_tab_state = tk.DISABLED if app.is_playing else tk.NORMAL
        app.start_rec_button.config(state=rec_tab_state)
        app.recording_duration_entry.config(state=rec_tab_state)
        app.clear_keyframes_button.config(state=rec_tab_state)
        # Disabling the volume automation graph interaction if main playback is active
        if hasattr(app, 'canvas_vol_auto'):
            if app.is_playing:
                if hasattr(app, '_vol_auto_click_cid'): # Disconnect if connected
                    if app._vol_auto_click_cid: app.canvas_vol_auto.mpl_disconnect(app._vol_auto_click_cid)
                    app._vol_auto_click_cid = None
            else:
                if not hasattr(app, '_vol_auto_click_cid') or app._vol_auto_click_cid is None: # Reconnect if not connected
                     app._vol_auto_click_cid = app.canvas_vol_auto.mpl_connect('button_press_event', app._on_volume_graph_click)


    for i in range(app.displayed_channels_count.get()): app.channels[i].set_controls_state(channel_controls_state)

if __name__ == "__main__":
    main_root_window = tk.Tk()
    app_instance = AudioEntrainmentApp(main_root_window)
    main_root_window.protocol("WM_DELETE_WINDOW", app_instance.on_closing)
    main_root_window.mainloop()
