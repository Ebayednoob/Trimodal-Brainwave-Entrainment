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
import urllib.request # For making HTTP requests to LLM APIs
import urllib.error

# --- Constants ---
NUM_CHANNELS = 12 # Maximum number of channels
SAMPLE_RATE = 44100  # Hz

MIN_FREQ = 20
DEFAULT_SLIDER_MAX_FREQ = 5000
ABSOLUTE_MAX_FREQ_LIMIT = 20000 # The highest possible max frequency selectable
MAX_FREQ_OPTIONS = [5000, 10000, 15000, 20000]
DEFAULT_FREQ = 100

MIN_AMP = 0.0; MAX_AMP = 1.0; DEFAULT_AMP = 0.5
MIN_ISO_FREQ = 0.0; MAX_ISO_FREQ = 50.0; DEFAULT_ISO_FREQ = 0.0
MIN_POS = -1.0; MAX_POS = 1.0; DEFAULT_POS = 0.0

BUFFER_DURATION = 0.05 
PLOT_DURATION = 1.0 
CHANNEL_PREVIEW_DURATION_SEC = 0.05 
RECORDING_BUFFER_SIZE_SEC = 0.1

# --- Frequency Preset Definitions ---
# Standard Presets (apply to as many displayed channels as available)
STANDARD_FREQUENCY_PRESETS = {
    "Solfeggio Harmonics": [99, 198, 396, 417, 528, 639, 741, 852, 1056, 1278, 1482, 1704],
    "Angel Frequencies": [111, 222, 333, 444, 555, 666, 777, 888, 999, 1111, 1222, 1333],
    "Phi Ratio Frequencies": [
        69, 111.5, 180.5, 292, 472.5, 764.5, 
        1236.5, 2002, 3238.5, 5240.5, 
        8479, 13719.5 
    ] 
}

# Binaural Beat Presets (fixed 440Hz carrier, apply to first 12 channels if available)
BINAURAL_BEAT_PRESETS = {
    "Binaural - Delta Low (0.5 Hz)": {"beat": 0.5, "left": 439.75, "right": 440.25},
    "Binaural - Delta High (3 Hz)": {"beat": 3.0, "left": 438.5, "right": 441.5},
    "Binaural - Theta Low (4 Hz)": {"beat": 4.0, "left": 438.0, "right": 442.0},
    "Binaural - Theta High (7 Hz)": {"beat": 7.0, "left": 436.5, "right": 443.5},
    "Binaural - Alpha Low (8 Hz)": {"beat": 8.0, "left": 436.0, "right": 444.0},
    "Binaural - Alpha High (12 Hz)": {"beat": 12.0, "left": 434.0, "right": 446.0},
    "Binaural - Beta Low (15 Hz)": {"beat": 15.0, "left": 432.5, "right": 447.5},
    "Binaural - Beta High (25 Hz)": {"beat": 25.0, "left": 427.5, "right": 452.5},
    "Binaural - Gamma Low (30 Hz)": {"beat": 30.0, "left": 425.0, "right": 455.0},
    "Binaural - Gamma High (40 Hz)": {"beat": 40.0, "left": 420.0, "right": 460.0},
}

# Combine all presets for the dropdown
ALL_FREQUENCY_PRESETS = {"Custom/Manual": []}
ALL_FREQUENCY_PRESETS.update(STANDARD_FREQUENCY_PRESETS)
ALL_FREQUENCY_PRESETS.update(BINAURAL_BEAT_PRESETS) # Keys will be unique

AI_ANALYSIS_PROMPT_TEMPLATE = """Prompt for AI Agent: Audio Entrainment Protocol Designer
Objective:  
You are an AI agent trained to create optimized audio entrainment protocols based on an input dataset formatted as follows:
json

{
  "app_settings": {
    "displayed_channels": 12,
    "recording_duration": "60",
    "channel_volume_keyframes": {"0": [[10.0, 80.0], [20.0, 50.0]], "1": [[5.0, 90.0]]}, // Example per-channel
    "active_frequency_preset": "Custom/Manual",
    "slider_max_frequency": 5000
  },
  "channels": [
    {
      "id": 0,
      "is_active": true,
      "frequency": 100.0,
      "amplitude": 0.5,
      "is_iso_active": false,
      "isochronic_frequency": 0.0,
      "x_pos": 0.0,
      "y_pos": 0.0,
      "z_pos": 0.0
    }
    // Remaining channels (up to 11) follow the same structure
  ]}
Instructions for Analysis:

Parse the dataset to identify active audio channels and their frequency, amplitude, and modulation parameters.
Recognize spatial positioning (X, Y, Z coordinates) and speaker assignment (L/R placement).
Determine the likely brainwave entrainment benefits based on frequency bands:
Delta (0.5-4 Hz): Deep sleep, relaxation
Theta (4-8 Hz): Meditation, creativity
Alpha (8-14 Hz): Calm focus, reduced stress
Beta (14-30 Hz): Alertness, active thinking
Gamma (30-100 Hz+): Higher cognitive processing
Response Format:  
Your response must be structured in the same format as the input dataset, while including a short summary at the beginning, explaining the expected entrainment benefits. Example response:
json

{
  "summary": "This configuration primarily targets Theta (meditative, creative states) and Alpha (calm, alert focus). Frequencies range from 100 Hz, which aligns with Gamma processing effects.",
  "app_settings": {
    "displayed_channels": 12,
    "recording_duration": "60",
    "channel_volume_keyframes": {"0": [[10.0, 80.0], [20.0, 50.0]], "1": [[5.0, 90.0]]},
    "active_frequency_preset": "Custom/Manual",
    "slider_max_frequency": 5000
  },
  "channels": [
    {
      "id": 0,
      "is_active": true,
      "frequency": 100.0,
      "amplitude": 0.5,
      "is_iso_active": false,
      "isochronic_frequency": 0.0,
      "x_pos": 0.0,
      "y_pos": 0.0,
      "z_pos": 0.0
    }
    // Remaining channels follow same format
  ]}
This prompt provides precise instructions to ensure structured input parsing, adherence to the correct output format, and contextual analysis of the frequencies for brainwave entrainment.

Current Configuration to Analyze:
"""


class AudioChannel:
    def __init__(self, master, channel_id, app_instance):
        self.channel_id = channel_id
        self.app = app_instance
        self.frame = ttk.LabelFrame(master, text=f"Channel {channel_id + 1}")

        self.frequency = DEFAULT_FREQ; self.amplitude = DEFAULT_AMP; self.is_active = True
        self.isochronic_frequency = DEFAULT_ISO_FREQ; self.is_iso_active = False
        self.x_pos = DEFAULT_POS; self.y_pos = DEFAULT_POS; self.z_pos = DEFAULT_POS

        active_frame = ttk.Frame(self.frame); active_frame.pack(fill="x", pady=(0, 2))
        self.is_active_var = tk.BooleanVar(value=self.is_active)
        self.active_check = ttk.Checkbutton(active_frame, text="Active", variable=self.is_active_var, command=self._params_changed_by_ui)
        self.active_check.pack(side=tk.LEFT, padx=(5,0))

        freq_controls_frame = ttk.Frame(self.frame); freq_controls_frame.pack(fill="x", pady=1)
        ttk.Label(freq_controls_frame, text="Freq (Hz):", width=10).pack(side=tk.LEFT, padx=(5,0))
        self.freq_var = tk.DoubleVar(value=self.frequency)
        self.freq_slider = ttk.Scale(freq_controls_frame, from_=MIN_FREQ, to=self.app.current_slider_max_freq.get(), orient=tk.HORIZONTAL, variable=self.freq_var)
        self.freq_slider.pack(side=tk.LEFT, expand=True, fill="x", padx=5)
        self.freq_slider.bind("<ButtonRelease-1>", self._manual_freq_change_handler) 
        self.freq_label_var = tk.StringVar(value=f"{self.freq_var.get():.0f} Hz")
        ttk.Label(freq_controls_frame, textvariable=self.freq_label_var, width=7).pack(side=tk.LEFT, padx=(0,5))
        self.freq_entry = ttk.Entry(freq_controls_frame, textvariable=self.freq_var, width=6)
        self.freq_entry.pack(side=tk.LEFT, padx=(0,5))
        self.freq_entry.bind("<Return>", self._manual_freq_change_handler)
        self.freq_entry.bind("<FocusOut>", self._manual_freq_change_handler)


        amp_controls_frame = ttk.Frame(self.frame); amp_controls_frame.pack(fill="x", pady=1)
        ttk.Label(amp_controls_frame, text="Amp:", width=10).pack(side=tk.LEFT, padx=(5,0))
        self.amp_var = tk.DoubleVar(value=self.amplitude)
        self.amp_slider = ttk.Scale(amp_controls_frame, from_=MIN_AMP, to=MAX_AMP, orient=tk.HORIZONTAL, variable=self.amp_var)
        self.amp_slider.pack(side=tk.LEFT, expand=True, fill="x", padx=5)
        self.amp_slider.bind("<ButtonRelease-1>", self._params_changed_by_ui)
        self.amp_label_var = tk.StringVar(value=f"{self.amp_var.get():.2f}")
        ttk.Label(amp_controls_frame, textvariable=self.amp_label_var, width=5).pack(side=tk.LEFT, padx=(0,5))

        iso_controls_frame = ttk.Frame(self.frame); iso_controls_frame.pack(fill="x", pady=1)
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

        spatial_frame = ttk.Frame(self.frame); spatial_frame.pack(fill="x", pady=1)
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

        preview_plot_frame = ttk.Frame(self.frame); preview_plot_frame.pack(fill="x", pady=(3,1), padx=5)
        self.fig_preview, self.ax_preview = plt.subplots(figsize=(3.5, 0.7)) 
        self.fig_preview.patch.set_facecolor('#F0F0F0'); self.ax_preview.set_facecolor('#FEFEFE') 
        self.ax_preview.set_yticks([]); self.ax_preview.set_xticks([])
        for spine in self.ax_preview.spines.values(): spine.set_visible(False) 
        self.fig_preview.subplots_adjust(left=0.02, right=0.98, top=0.98, bottom=0.02) 
        self.preview_line, = self.ax_preview.plot([], [], lw=1, color='#4A8CFF') 
        self.ax_preview.set_ylim(-MAX_AMP * 1.1, MAX_AMP * 1.1) 
        self.canvas_preview = FigureCanvasTkAgg(self.fig_preview, master=preview_plot_frame)
        self.canvas_preview_widget = self.canvas_preview.get_tk_widget(); self.canvas_preview_widget.pack(fill=tk.BOTH, expand=True)
        
        self.freq_var.trace_add('write', self._sync_freq_display_from_var) 
        self.amp_var.trace_add('write', self._sync_amp_display_from_var)
        self.iso_freq_var.trace_add('write', self._sync_iso_display_from_var)
        self.x_pos_var.trace_add('write', lambda *args: (self.x_pos_label_var.set(f"{self.x_pos_var.get():.2f}"), self._params_changed_by_ui() if self.app and self.app.is_playing else None))
        self.y_pos_var.trace_add('write', lambda *args: (self.y_pos_label_var.set(f"{self.y_pos_var.get():.2f}"), self._params_changed_by_ui() if self.app and self.app.is_playing else None))
        self.z_pos_var.trace_add('write', lambda *args: (self.z_pos_label_var.set(f"{self.z_pos_var.get():.2f}"), self._params_changed_by_ui() if self.app and self.app.is_playing else None))

        self._update_iso_entry_state(); self._update_internal_params_from_vars(); self.update_waveform_preview() 

    def update_slider_max_freq(self, new_max_freq):
        """Updates the 'to' value of the frequency slider and clamps current frequency."""
        self.freq_slider.config(to=new_max_freq)
        current_freq = self.freq_var.get()
        if current_freq > new_max_freq:
            self.freq_var.set(new_max_freq)
        elif current_freq < MIN_FREQ: 
            self.freq_var.set(MIN_FREQ)

    def _manual_freq_change_handler(self, event=None):
        self._validate_and_update_freq_from_entry(event) 
        if self.app:
            self.app.set_frequency_preset_to_custom() 

    def _update_internal_params_from_vars(self):
        self.frequency=self.freq_var.get(); self.amplitude=self.amp_var.get(); self.is_active=self.is_active_var.get()
        self.is_iso_active=self.iso_active_var.get()
        try: self.isochronic_frequency=self.iso_freq_var.get()
        except tk.TclError: self.iso_freq_var.set(DEFAULT_ISO_FREQ); self.isochronic_frequency=DEFAULT_ISO_FREQ
        self.x_pos=self.x_pos_var.get(); self.y_pos=self.y_pos_var.get(); self.z_pos=self.z_pos_var.get()

    def _params_changed_by_ui(self, event=None): self._update_internal_params_from_vars(); self.update_waveform_preview(); self.app.notify_param_change()
    def _sync_freq_display_from_var(self, *args): val=self.freq_var.get(); self.freq_label_var.set(f"{val:.0f} Hz"); self.frequency=val
    def _validate_and_update_freq_from_entry(self, event=None):
        try: 
            val=float(self.freq_entry.get())
            val=max(MIN_FREQ,min(val, self.app.current_slider_max_freq.get())) 
            self.freq_var.set(val)
        except ValueError: self.freq_var.set(self.frequency)
    def _sync_amp_display_from_var(self, *args): val=self.amp_var.get(); self.amp_label_var.set(f"{val:.2f}"); self.amplitude=val
    def _sync_iso_display_from_var(self, *args):
        try: val=self.iso_freq_var.get(); self.iso_freq_label_var.set(f"{val:.1f} Hz"); self.isochronic_frequency=val
        except tk.TclError: self.iso_freq_label_var.set("--- Hz" if not self.is_iso_active else f"{DEFAULT_ISO_FREQ:.1f} Hz (inv)")
    def _validate_and_update_iso_from_entry(self, event=None):
        if not self.is_iso_active: self.iso_freq_var.set(self.isochronic_frequency); return
        try: val=float(self.iso_freq_entry.get()); val=max(MIN_ISO_FREQ,min(val,MAX_ISO_FREQ)); self.iso_freq_var.set(val)
        except ValueError: self.iso_freq_var.set(self.isochronic_frequency)
        self._params_changed_by_ui() 
    def _update_iso_entry_state(self):
        is_active=self.iso_active_var.get(); new_state=tk.NORMAL if is_active else tk.DISABLED
        self.iso_freq_entry.config(state=new_state); self.iso_display_label.config(state=new_state)
        if not is_active: self.iso_freq_label_var.set("--- Hz")
        else: self.iso_freq_label_var.set(f"{self.iso_freq_var.get():.1f} Hz")
    def _on_iso_active_toggled(self, event=None):
        self.is_iso_active=self.iso_active_var.get(); self._update_iso_entry_state()
        if not self.is_iso_active: self.iso_freq_var.set(DEFAULT_ISO_FREQ); self.isochronic_frequency=DEFAULT_ISO_FREQ
        else: self.iso_freq_var.set(self.isochronic_frequency) 
        self._params_changed_by_ui() 
    def get_params_as_dict(self):
        self._update_internal_params_from_vars()
        return {"id":self.channel_id,"is_active":self.is_active,"frequency":self.frequency,"amplitude":self.amplitude,
                "is_iso_active":self.is_iso_active,"isochronic_frequency":self.isochronic_frequency,
                "x_pos":self.x_pos,"y_pos":self.y_pos,"z_pos":self.z_pos}
    def load_params_from_dict(self, data_dict):
        loaded_freq = data_dict.get("frequency", DEFAULT_FREQ)
        clamped_freq = max(MIN_FREQ, min(loaded_freq, self.app.current_slider_max_freq.get()))
        self.is_active_var.set(data_dict.get("is_active",True)); self.freq_var.set(clamped_freq)
        self.amp_var.set(data_dict.get("amplitude",DEFAULT_AMP)); self.iso_active_var.set(data_dict.get("is_iso_active",False))
        self.iso_freq_var.set(data_dict.get("isochronic_frequency",DEFAULT_ISO_FREQ)); self.x_pos_var.set(data_dict.get("x_pos",DEFAULT_POS))
        self.y_pos_var.set(data_dict.get("y_pos",DEFAULT_POS)); self.z_pos_var.set(data_dict.get("z_pos",DEFAULT_POS))
        self._update_internal_params_from_vars(); self._update_iso_entry_state(); self.update_waveform_preview() 
    def get_params(self):
        self._update_internal_params_from_vars()
        effective_iso_freq = self.isochronic_frequency if self.is_iso_active and self.isochronic_frequency > 0.001 else 0.0
        return self.frequency,self.amplitude,self.is_active,effective_iso_freq,self.x_pos,self.y_pos,self.z_pos
    def reset(self):
        self.is_active_var.set(True); self.freq_var.set(DEFAULT_FREQ); self.amp_var.set(DEFAULT_AMP)
        self.iso_active_var.set(False); self.iso_freq_var.set(DEFAULT_ISO_FREQ)
        self.x_pos_var.set(DEFAULT_POS); self.y_pos_var.set(DEFAULT_POS); self.z_pos_var.set(DEFAULT_POS)
        self._update_internal_params_from_vars(); self._update_iso_entry_state(); self._params_changed_by_ui() 
    def set_controls_state(self, new_state):
        controls=[self.active_check,self.freq_slider,self.freq_entry,self.amp_slider,self.iso_active_check,
                  self.x_pos_slider,self.y_pos_slider,self.z_pos_slider]
        for ctrl in controls: ctrl.config(state=new_state)
        iso_entry_state=tk.NORMAL if new_state==tk.NORMAL and self.iso_active_var.get() else tk.DISABLED
        self.iso_freq_entry.config(state=iso_entry_state); self.iso_display_label.config(state=iso_entry_state)
        if new_state==tk.NORMAL and not self.iso_active_var.get(): self.iso_freq_label_var.set("--- Hz")
    def update_waveform_preview(self):
        if not hasattr(self,'canvas_preview'): return 
        freq=self.frequency; amp=self.amplitude; active=self.is_active; iso_val=self.isochronic_frequency; iso_on=self.is_iso_active
        eff_iso = iso_val if active and iso_on and iso_val > 0.001 else 0.0
        N = int(SAMPLE_RATE*CHANNEL_PREVIEW_DURATION_SEC); t = np.linspace(0,CHANNEL_PREVIEW_DURATION_SEC,N,endpoint=False)
        if not active or amp < 0.001 or freq <=0: sig=np.zeros_like(t); y_lim=max(MAX_AMP*0.1,0.01) 
        else:
            sig=amp*np.sin(2*np.pi*freq*t)
            if eff_iso > 0.001: sig *= np.where((eff_iso*t)%1.0 < 0.5,1.0,0.0)
            y_lim=max(amp*1.1,0.01)
        self.preview_line.set_data(t,sig); self.ax_preview.set_ylim(-y_lim,y_lim)
        self.ax_preview.set_xlim(0,CHANNEL_PREVIEW_DURATION_SEC); self.canvas_preview.draw_idle() 

class AudioEntrainmentApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("Bio-Entrainment Therapeutics Spatial Audio Agent") # Updated Title
        self.root.geometry("950x850") 

        self.channels = []
        self.audio_stream = None
        self.is_playing = False 
        self.playback_params_lock = threading.Lock()
        self.current_time_offset = 0.0
        self.active_channel_audio_params = []
        self.displayed_channels_count = tk.IntVar(value=NUM_CHANNELS) 
        self.channel_points_viz = [] 

        self.is_recording = False; self.is_recording_paused = False
        self.recording_duration_var = tk.StringVar(value="60") 
        self.recorded_frames = []; self.recording_thread = None; self.recording_filepath = ""
        self.recording_elapsed_time = 0.0; self.recording_pause_start_time = 0.0
        self.channel_volume_keyframes = {i: [] for i in range(NUM_CHANNELS)} # Per-channel keyframes
        self.selected_automation_channel_var = tk.StringVar(value="Channel 1")


        self.selected_llm = tk.StringVar(value="Gemini")
        self.api_key_var = tk.StringVar() 
        self.ai_chat_history = [] 
        self.active_frequency_preset = tk.StringVar(value="Custom/Manual")
        self.current_slider_max_freq = tk.IntVar(value=DEFAULT_SLIDER_MAX_FREQ)


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

        self.ai_agent_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.ai_agent_tab, text="AI Agent")
        self._setup_ai_agent_tab()
        
        self.on_channel_count_changed() 
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
        self.channels_canvas.pack(side=tk.LEFT, fill="y", expand=False); self.channels_scrollbar.pack(side="right", fill="y")
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
        
        # Playback and general controls
        self.play_button = ttk.Button(self.controls_frame, text="Play", command=self.play_audio, width=8); self.play_button.pack(side=tk.LEFT, padx=2)
        self.stop_button = ttk.Button(self.controls_frame, text="Stop", command=self.stop_audio, state=tk.DISABLED, width=8); self.stop_button.pack(side=tk.LEFT, padx=2)
        self.record_button = ttk.Button(self.controls_frame, text="Display Waveform", command=self.record_and_display_waveform, width=16); self.record_button.pack(side=tk.LEFT, padx=2)
        self.reset_button = ttk.Button(self.controls_frame, text="Reset All", command=self.reset_all_channels, width=10); self.reset_button.pack(side=tk.LEFT, padx=2)
        
        # Channel count dropdown
        ttk.Label(self.controls_frame, text="Channels:").pack(side=tk.LEFT, padx=(5, 2))
        self.channel_count_combo = ttk.Combobox(self.controls_frame, textvariable=self.displayed_channels_count, values=[str(i) for i in range(1, NUM_CHANNELS + 1)], width=3, state="readonly")
        self.channel_count_combo.pack(side=tk.LEFT, padx=(0, 5)); self.channel_count_combo.bind("<<ComboboxSelected>>", self.on_channel_count_changed)

        # Max Frequency Dropdown
        ttk.Label(self.controls_frame, text="Max Freq:").pack(side=tk.LEFT, padx=(5,2))
        self.max_freq_combo = ttk.Combobox(self.controls_frame, textvariable=self.current_slider_max_freq, values=MAX_FREQ_OPTIONS, width=7, state="readonly")
        self.max_freq_combo.pack(side=tk.LEFT, padx=(0,5))
        self.max_freq_combo.bind("<<ComboboxSelected>>", self._on_slider_max_freq_changed)

        # Frequency Preset Dropdown
        ttk.Label(self.controls_frame, text="Preset:").pack(side=tk.LEFT, padx=(5,2))
        self.freq_preset_combo = ttk.Combobox(self.controls_frame, textvariable=self.active_frequency_preset, values=list(ALL_FREQUENCY_PRESETS.keys()), width=20, state="readonly")
        self.freq_preset_combo.pack(side=tk.LEFT, padx=(0,5))
        self.freq_preset_combo.bind("<<ComboboxSelected>>", self.on_frequency_preset_selected)

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
        data_controls_frame = ttk.Frame(self.data_io_tab); data_controls_frame.pack(pady=10, fill="x")
        self.save_button = ttk.Button(data_controls_frame, text="Save Configuration", command=self.save_configuration, width=20)
        self.save_button.pack(side=tk.LEFT, padx=5)
        self.load_button = ttk.Button(data_controls_frame, text="Load Configuration", command=self.load_configuration, width=20)
        self.load_button.pack(side=tk.LEFT, padx=5)
        self.apply_json_text_button = ttk.Button(data_controls_frame, text="Apply JSON from Text", command=self.apply_json_from_text_area, width=22)
        self.apply_json_text_button.pack(side=tk.LEFT, padx=5)
        config_display_frame = ttk.LabelFrame(self.data_io_tab, text="Current Configuration (JSON) - Editable", padding=5)
        config_display_frame.pack(fill="both", expand=True, pady=5)
        self.config_text = tk.Text(config_display_frame, wrap=tk.WORD, height=15, width=70, state=tk.NORMAL) 
        self.config_text_scroll = ttk.Scrollbar(config_display_frame, orient=tk.VERTICAL, command=self.config_text.yview)
        self.config_text.configure(yscrollcommand=self.config_text_scroll.set)
        self.config_text_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.config_text.pack(side=tk.LEFT, fill="both", expand=True)

    def _setup_recording_tab(self):
        # Top frame for duration and channel selector
        top_rec_frame = ttk.Frame(self.recording_tab)
        top_rec_frame.pack(pady=5, fill="x")

        duration_frame = ttk.Frame(top_rec_frame)
        duration_frame.pack(side=tk.LEFT, padx=(0, 20))
        ttk.Label(duration_frame, text="Total Recording Time (seconds):").pack(side=tk.LEFT, padx=5)
        self.recording_duration_entry = ttk.Entry(duration_frame, textvariable=self.recording_duration_var, width=10)
        self.recording_duration_entry.pack(side=tk.LEFT, padx=5)
        self.recording_duration_var.trace_add("write", lambda *args: self.update_volume_automation_graph())

        automation_channel_frame = ttk.Frame(top_rec_frame)
        automation_channel_frame.pack(side=tk.LEFT)
        ttk.Label(automation_channel_frame, text="Edit Automation for:").pack(side=tk.LEFT, padx=5)
        self.automation_channel_combo = ttk.Combobox(
            automation_channel_frame, 
            textvariable=self.selected_automation_channel_var, 
            values=[f"Channel {i+1}" for i in range(NUM_CHANNELS)], 
            width=12, 
            state="readonly"
        )
        self.automation_channel_combo.pack(side=tk.LEFT, padx=5)
        self.automation_channel_combo.bind("<<ComboboxSelected>>", lambda event: self.update_volume_automation_graph())


        rec_controls_frame = ttk.Frame(self.recording_tab); rec_controls_frame.pack(pady=5, fill="x")
        self.start_rec_button = ttk.Button(rec_controls_frame, text="Start Recording", command=self.start_recording, width=18)
        self.start_rec_button.pack(side=tk.LEFT, padx=2)
        self.pause_rec_button = ttk.Button(rec_controls_frame, text="Pause Recording", command=self.toggle_pause_recording, width=18, state=tk.DISABLED)
        self.pause_rec_button.pack(side=tk.LEFT, padx=2)
        self.stop_rec_button = ttk.Button(rec_controls_frame, text="Stop Recording", command=self.stop_recording, width=18, state=tk.DISABLED)
        self.stop_rec_button.pack(side=tk.LEFT, padx=2)
        self.clear_keyframes_button = ttk.Button(rec_controls_frame, text="Clear Keyframes (Selected Ch)", command=self.clear_volume_keyframes, width=25)
        self.clear_keyframes_button.pack(side=tk.LEFT, padx=2)
        
        progress_frame = ttk.Frame(self.recording_tab); progress_frame.pack(pady=5, fill="x")
        self.recording_progress_bar = ttk.Progressbar(progress_frame, orient="horizontal", length=300, mode="determinate")
        self.recording_progress_bar.pack(pady=2, fill="x")
        self.recording_status_label = ttk.Label(progress_frame, text="Status: Idle")
        self.recording_status_label.pack(pady=2)
        
        automation_graph_frame = ttk.LabelFrame(self.recording_tab, text="Volume Automation for Selected Channel", padding=5)
        automation_graph_frame.pack(pady=10, fill="both", expand=True)
        self.fig_vol_auto, self.ax_vol_auto = plt.subplots(figsize=(6, 2.5))
        self.fig_vol_auto.patch.set_facecolor('#F0F0F0'); self.ax_vol_auto.set_facecolor('#FFFFFF')
        self.ax_vol_auto.set_title("Volume (%) vs. Time (s)", fontsize=9); self.ax_vol_auto.set_xlabel("Time (s)", fontsize=8)
        self.ax_vol_auto.set_ylabel("Volume (%)", fontsize=8); self.ax_vol_auto.set_ylim(0, 105)
        self.ax_vol_auto.grid(True, linestyle=':', alpha=0.7)
        self.vol_auto_line, = self.ax_vol_auto.plot([], [], 'bo-', markersize=4, picker=True, pickradius=5) 
        self.canvas_vol_auto = FigureCanvasTkAgg(self.fig_vol_auto, master=automation_graph_frame)
        self.canvas_vol_auto_widget = self.canvas_vol_auto.get_tk_widget(); self.canvas_vol_auto_widget.pack(fill=tk.BOTH, expand=True)
        self.fig_vol_auto.tight_layout(pad=0.5)
        self._vol_auto_click_cid = self.canvas_vol_auto.mpl_connect('button_press_event', self._on_volume_graph_click) 
        self.canvas_vol_auto.draw()

    def _setup_ai_agent_tab(self):
        llm_config_frame = ttk.Frame(self.ai_agent_tab); llm_config_frame.pack(pady=5, fill="x")
        ttk.Label(llm_config_frame, text="Select LLM:").pack(side=tk.LEFT, padx=(0,5))
        self.llm_selector = ttk.Combobox(llm_config_frame, textvariable=self.selected_llm, 
                                         values=["Gemini", "OpenAI"], width=15, state="readonly")
        self.llm_selector.pack(side=tk.LEFT, padx=5)
        self.api_key_label = ttk.Label(llm_config_frame, text="API Key:")
        self.api_key_label.pack(side=tk.LEFT, padx=(10,2))
        self.api_key_entry = ttk.Entry(llm_config_frame, textvariable=self.api_key_var, width=30, show="*") 
        self.api_key_entry.pack(side=tk.LEFT, padx=2)
        self.test_connection_button = ttk.Button(llm_config_frame, text="Test Connection", command=self._test_llm_connection)
        self.test_connection_button.pack(side=tk.LEFT, padx=(10,0))
        status_frame = ttk.LabelFrame(self.ai_agent_tab, text="AI Status", padding=5); status_frame.pack(pady=5, fill="x")
        self.ai_status_text = tk.Text(status_frame, height=3, wrap=tk.WORD, state=tk.DISABLED, bg="#F0F0F0", fg="black")
        self.ai_status_text.pack(fill="x", expand=True); self._update_ai_status("AI Agent Idle.")
        chat_history_frame = ttk.LabelFrame(self.ai_agent_tab, text="Chat History", padding=5)
        chat_history_frame.pack(pady=5, fill="both", expand=True)
        self.ai_chat_history_text = tk.Text(chat_history_frame, wrap=tk.WORD, state=tk.DISABLED, bg="#FFFFFF", fg="black")
        chat_scroll = ttk.Scrollbar(chat_history_frame, command=self.ai_chat_history_text.yview)
        self.ai_chat_history_text.configure(yscrollcommand=chat_scroll.set); chat_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.ai_chat_history_text.pack(fill="both", expand=True)
        input_frame = ttk.Frame(self.ai_agent_tab); input_frame.pack(pady=5, fill="x")
        self.ai_message_entry = ttk.Entry(input_frame, width=60) 
        self.ai_message_entry.pack(side=tk.LEFT, fill="x", expand=True, padx=(0,5))
        self.ai_message_entry.bind("<Return>", self._send_ai_message_event) 
        send_button = ttk.Button(input_frame, text="Send", command=self._send_ai_message_event, width=8); send_button.pack(side=tk.LEFT, padx=(0,2))
        self.analyze_config_button = ttk.Button(input_frame, text="Analyze Config", command=self._analyze_configuration_with_ai, width=15)
        self.analyze_config_button.pack(side=tk.LEFT, padx=2)
        clear_chat_button = ttk.Button(input_frame, text="Clear Chat", command=self._clear_ai_chat, width=10); clear_chat_button.pack(side=tk.LEFT, padx=2)
        
    def _bind_mousewheel(self, event, widget): widget.bind_all("<MouseWheel>", lambda e: self._on_mousewheel(e, widget))
    def _unbind_mousewheel(self, event, widget): widget.unbind_all("<MouseWheel>")
    def _on_mousewheel(self, event, canvas_widget):
        if event.delta: canvas_widget.yview_scroll(int(-1*(event.delta/120)), "units")
        elif event.num == 4: canvas_widget.yview_scroll(-1, "units")
        elif event.num == 5: canvas_widget.yview_scroll(1, "units")

    def _on_slider_max_freq_changed(self, event=None):
        new_max_f = self.current_slider_max_freq.get()
        for channel in self.channels:
            channel.update_slider_max_freq(new_max_f)
        current_preset = self.active_frequency_preset.get()
        if current_preset != "Custom/Manual":
            self.on_frequency_preset_selected() 
        self.notify_param_change()

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

    def on_frequency_preset_selected(self, event=None):
        preset_name = self.active_frequency_preset.get()
        if preset_name not in ALL_FREQUENCY_PRESETS or preset_name == "Custom/Manual": 
            if preset_name != "Custom/Manual": 
                 self.active_frequency_preset.set("Custom/Manual")
            return 
        
        num_displayed = self.displayed_channels_count.get()
        current_max_slider_freq = self.current_slider_max_freq.get()

        if preset_name in STANDARD_FREQUENCY_PRESETS:
            preset_freqs = STANDARD_FREQUENCY_PRESETS[preset_name]
            for i in range(num_displayed):
                if i < len(preset_freqs):
                    freq_to_set = max(MIN_FREQ, min(preset_freqs[i], current_max_slider_freq)) 
                    self.channels[i].freq_var.set(freq_to_set)
                    # Keep other params as they are for standard presets
                else: 
                    self.channels[i].freq_var.set(DEFAULT_FREQ)
            for i in range(len(preset_freqs), num_displayed): 
                self.channels[i].freq_var.set(DEFAULT_FREQ)
        
        elif preset_name in BINAURAL_BEAT_PRESETS:
            binaural_data = BINAURAL_BEAT_PRESETS[preset_name]
            left_freq = max(MIN_FREQ, min(binaural_data["left"], current_max_slider_freq))
            right_freq = max(MIN_FREQ, min(binaural_data["right"], current_max_slider_freq))
            
            for i in range(NUM_CHANNELS): # Apply to all 12 internal channels
                ch = self.channels[i]
                if i < NUM_CHANNELS / 2: # First 6 channels for left ear
                    ch.freq_var.set(left_freq)
                    ch.x_pos_var.set(-1.0)
                else: # Next 6 channels for right ear
                    ch.freq_var.set(right_freq)
                    ch.x_pos_var.set(1.0)
                
                # Set other params to defaults for a clean binaural setup
                ch.amp_var.set(DEFAULT_AMP)
                ch.is_active_var.set(True) # Ensure they are active
                ch.iso_active_var.set(False)
                ch.iso_freq_var.set(DEFAULT_ISO_FREQ)
                ch.y_pos_var.set(DEFAULT_POS)
                ch.z_pos_var.set(DEFAULT_POS)
                ch._update_internal_params_from_vars() # Sync internal state
                ch.update_waveform_preview()

        self.notify_param_change() 

    def set_frequency_preset_to_custom(self):
        if self.active_frequency_preset.get() != "Custom/Manual":
            self.active_frequency_preset.set("Custom/Manual")

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
        
        stereo_out = np.zeros((num_frames, 2), dtype=np.float32)

        for params in current_params:
            channel_id = params['id']
            freq, amp, iso_freq, x, y, z = params['freq'],params['amp'],params['iso_freq'],params['x'],params['y'],params['z']
            
            mono_signal_channel = amp*np.sin(2*np.pi*freq*t_abs.astype(np.float64))
            if iso_freq > 0.001: mono_signal_channel *= np.where((iso_freq*t_abs.astype(np.float64))%1.0 < 0.5, 1.0, 0.0)
            
            if apply_automation:
                try: total_rec_duration = float(self.recording_duration_var.get())
                except ValueError: total_rec_duration = 0 
                if total_rec_duration > 0:
                    channel_keyframes = self.channel_volume_keyframes.get(channel_id, [])
                    automation_gain_block = np.ones(num_frames, dtype=np.float32)
                    for i in range(num_frames):
                        current_sample_time = (time_offset_samples + i) / SAMPLE_RATE
                        automation_gain_block[i] = self._get_automation_volume_at_time(current_sample_time, total_rec_duration, channel_keyframes)
                    mono_signal_channel *= automation_gain_block

            distance=np.sqrt(x**2+y**2+z**2); dist_gain=1.0/(1.0+distance*0.5); y_gain=0.75+0.25*y
            processed_signal=mono_signal_channel.astype(np.float32)*dist_gain*y_gain
            pan_angle=(x+1.0)*np.pi/4.0; gain_left=np.cos(pan_angle); gain_right=np.sin(pan_angle)
            
            left_mix += processed_signal*gain_left
            right_mix += processed_signal*gain_right
        
        total_potential_amp_sum = sum(p['amp'] for p in current_params if p['amp'] > 0.001 and self.channels[p['id']].is_active) 
        if total_potential_amp_sum > 1.0: 
            left_mix/=total_potential_amp_sum
            right_mix/=total_potential_amp_sum

        stereo_out[:, 0] = np.clip(left_mix, -0.999, 0.999)
        stereo_out[:, 1] = np.clip(right_mix, -0.999, 0.999)
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
        self.clear_volume_keyframes(clear_all=True) 
        self.active_frequency_preset.set("Custom/Manual") 
        self.current_slider_max_freq.set(DEFAULT_SLIDER_MAX_FREQ) 
        self._on_slider_max_freq_changed() 
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
                "channel_volume_keyframes": self.channel_volume_keyframes, # Changed
                "active_frequency_preset": self.active_frequency_preset.get(),
                "slider_max_frequency": self.current_slider_max_freq.get() 
            },
            "channels": [ch.get_params_as_dict() for ch in self.channels] 
        }
        return config

    def update_config_display_text(self):
        if not hasattr(self, 'config_text'): return
        try:
            current_config = self.get_current_configuration_dict()
            config_json = json.dumps(current_config, indent=2)
            self.config_text.delete(1.0, tk.END); self.config_text.insert(tk.END, config_json)
        except Exception as e:
            print(f"Error updating config display: {e}")
            self.config_text.delete(1.0, tk.END); self.config_text.insert(tk.END, f"Error: {e}")

    def save_configuration(self):
        if self.is_playing or self.is_recording: self.show_message("Save Error", "Stop audio/recording first."); return
        filepath = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json"), ("All files", "*.*")], title="Save Configuration As", parent=self.root)
        if not filepath: return
        try:
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
        
        loaded_channel_keyframes_str_keys = app_settings.get("channel_volume_keyframes", {})
        self.channel_volume_keyframes = {int(k): sorted(v) for k, v in loaded_channel_keyframes_str_keys.items() if isinstance(v, list)}

        for i in range(NUM_CHANNELS):
            if i not in self.channel_volume_keyframes:
                self.channel_volume_keyframes[i] = []

        self.active_frequency_preset.set(app_settings.get("active_frequency_preset", "Custom/Manual")) 
        
        loaded_slider_max_freq = app_settings.get("slider_max_frequency", DEFAULT_SLIDER_MAX_FREQ)
        self.current_slider_max_freq.set(loaded_slider_max_freq)
        self._on_slider_max_freq_changed() 

        self.on_channel_count_changed() 
        self.update_volume_automation_graph() 

        loaded_channels_data = loaded_data["channels"]
        for i in range(NUM_CHANNELS):
            if i < len(loaded_channels_data):
                ch_data = loaded_channels_data[i]
                if ch_data.get("id") == self.channels[i].channel_id: self.channels[i].load_params_from_dict(ch_data)
                else: print(f"Warning: Ch ID mismatch {i}. Loading by order."); self.channels[i].load_params_from_dict(ch_data) 
            else: self.channels[i].reset() 
        self.notify_param_change() 

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
        self.automation_channel_combo.config(state=tk.DISABLED) 
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
        self.automation_channel_combo.config(state="readonly") 
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
        
        try:
            selected_channel_str = self.selected_automation_channel_var.get() # "Channel X"
            selected_channel_id = int(selected_channel_str.split(" ")[1]) - 1
            if 0 <= selected_channel_id < NUM_CHANNELS:
                self.channel_volume_keyframes.setdefault(selected_channel_id, []).append((clicked_time, clicked_volume))
                self.channel_volume_keyframes[selected_channel_id].sort() 
                self.update_volume_automation_graph(); self.update_config_display_text() 
        except Exception as e:
            print(f"Error adding keyframe: {e}")


    def update_volume_automation_graph(self):
        if not hasattr(self, 'ax_vol_auto'): return
        self.ax_vol_auto.clear(); self.ax_vol_auto.set_title("Volume (%) vs. Time (s)", fontsize=9)
        self.ax_vol_auto.set_xlabel("Time (s)", fontsize=8); self.ax_vol_auto.set_ylabel("Volume (%)", fontsize=8)
        self.ax_vol_auto.set_ylim(0, 105); self.ax_vol_auto.grid(True, linestyle=':', alpha=0.7)
        try: total_duration = float(self.recording_duration_var.get())
        except ValueError: total_duration = 60.0 
        if total_duration <=0: total_duration = 0.1 
        self.ax_vol_auto.set_xlim(0, total_duration)
        
        try:
            selected_channel_str = self.selected_automation_channel_var.get()
            selected_channel_id = int(selected_channel_str.split(" ")[1]) - 1
        except: 
            selected_channel_id = 0
            self.selected_automation_channel_var.set("Channel 1")

        current_channel_keyframes = self.channel_volume_keyframes.get(selected_channel_id, [])
        plot_keyframes = list(current_channel_keyframes) 
        
        if not plot_keyframes: plot_keyframes = [(0, 100.0), (total_duration, 100.0)]
        else:
            if plot_keyframes[0][0] > 0: plot_keyframes.insert(0, (0, plot_keyframes[0][1]))
            if plot_keyframes[-1][0] < total_duration: plot_keyframes.append((total_duration, plot_keyframes[-1][1]))
        plot_keyframes.sort()
        times = [kf[0] for kf in plot_keyframes]; volumes = [kf[1] for kf in plot_keyframes]
        if current_channel_keyframes: 
            user_times = [kf[0] for kf in current_channel_keyframes]; user_volumes = [kf[1] for kf in current_channel_keyframes]
            self.ax_vol_auto.plot(user_times, user_volumes, 'bo', markersize=5)
        self.vol_auto_line, = self.ax_vol_auto.plot(times, volumes, 'b-')
        if hasattr(self, 'canvas_vol_auto'): self.canvas_vol_auto.draw_idle()

    def clear_volume_keyframes(self, clear_all=False):
        if self.is_recording: self.show_message("Action Denied", "Cannot clear keyframes while recording."); return
        if clear_all:
            self.channel_volume_keyframes = {i: [] for i in range(NUM_CHANNELS)}
            self.show_message("Keyframes Cleared", "All volume automation keyframes cleared.")
        else:
            try:
                selected_channel_str = self.selected_automation_channel_var.get()
                selected_channel_id = int(selected_channel_str.split(" ")[1]) - 1
                if 0 <= selected_channel_id < NUM_CHANNELS:
                    self.channel_volume_keyframes[selected_channel_id] = []
                    self.show_message("Keyframes Cleared", f"Volume keyframes cleared for {selected_channel_str}.")
                else:
                    self.show_message("Error", "Invalid channel selected for clearing keyframes.")
            except Exception as e:
                self.show_message("Error", f"Could not clear keyframes: {e}")
        self.update_volume_automation_graph()
        self.update_config_display_text()


    def _get_automation_volume_at_time(self, current_time_sec, total_duration_sec, keyframes_list):
        if not keyframes_list: return 1.0 
        working_keyframes = list(keyframes_list) 
        if not working_keyframes or working_keyframes[0][0] > 0:
            first_vol = working_keyframes[0][1] if working_keyframes else 100.0
            working_keyframes.insert(0, (0, first_vol))
        if working_keyframes[-1][0] < total_duration_sec: 
            last_vol = working_keyframes[-1][1]
            working_keyframes.append((total_duration_sec, last_vol))
        working_keyframes.sort() 
        
        if current_time_sec <= working_keyframes[0][0]: return working_keyframes[0][1] / 100.0
        if current_time_sec >= working_keyframes[-1][0]: return working_keyframes[-1][1] / 100.0
        
        for i in range(len(working_keyframes) - 1):
            kf1_time, kf1_vol = working_keyframes[i]; kf2_time, kf2_vol = working_keyframes[i+1]
            if kf1_time <= current_time_sec <= kf2_time:
                if kf2_time == kf1_time: return kf1_vol / 100.0
                time_range = kf2_time - kf1_time
                if time_range == 0 : return kf1_vol / 100.0 # Avoid division by zero
                slope = (kf2_vol - kf1_vol) / time_range
                interpolated_vol = kf1_vol + slope * (current_time_sec - kf1_time)
                return max(0, min(interpolated_vol, 100.0)) / 100.0
        return 1.0 

    # --- AI Agent Methods ---
    def _on_llm_selected(self, event=None):
        pass 

    def _update_ai_status(self, message):
        self.ai_status_text.config(state=tk.NORMAL); self.ai_status_text.delete(1.0, tk.END)
        self.ai_status_text.insert(tk.END, message); self.ai_status_text.config(state=tk.DISABLED)

    def _add_to_chat_history(self, role, content):
        self.ai_chat_history_text.config(state=tk.NORMAL)
        if self.ai_chat_history_text.index('end-1c') != "1.0": self.ai_chat_history_text.insert(tk.END, "\n\n")
        tag_name = "user_message" if role == "user" else "ai_message"
        self.ai_chat_history_text.insert(tk.END, f"{role.capitalize()}: ", (tag_name + "_role",))
        self.ai_chat_history_text.insert(tk.END, content, (tag_name + "_content",))
        self.ai_chat_history_text.tag_configure("user_message_role", font=("TkDefaultFont", 10, "bold"), foreground="blue")
        self.ai_chat_history_text.tag_configure("ai_message_role", font=("TkDefaultFont", 10, "bold"), foreground="green")
        self.ai_chat_history_text.see(tk.END); self.ai_chat_history_text.config(state=tk.DISABLED)

    def _clear_ai_chat(self):
        self.ai_chat_history_text.config(state=tk.NORMAL); self.ai_chat_history_text.delete(1.0, tk.END)
        self.ai_chat_history_text.config(state=tk.DISABLED); self.ai_chat_history = []
        self._update_ai_status("Chat cleared. AI Agent Idle.")

    def _send_ai_message_event(self, event=None): 
        user_message = self.ai_message_entry.get().strip()
        if not user_message: return
        self._add_to_chat_history("user", user_message); self.ai_message_entry.delete(0, tk.END)
        self._update_ai_status(f"Sending to {self.selected_llm.get()}...")
        threading.Thread(target=self._process_ai_request_with_prompt, args=(user_message,), daemon=True).start()

    def _analyze_configuration_with_ai(self):
        if self.is_playing or self.is_recording:
            self.show_message("AI Analysis", "Please stop playback/recording before analyzing configuration.")
            return
        self._update_ai_status(f"Analyzing configuration with {self.selected_llm.get()}...")
        current_config_dict = self.get_current_configuration_dict()
        current_config_json = json.dumps(current_config_dict, indent=2)
        full_prompt_for_analysis = AI_ANALYSIS_PROMPT_TEMPLATE + "\n" + current_config_json
        self._add_to_chat_history("user", "Analyze current audio configuration (see details in prompt sent to AI).")
        threading.Thread(target=self._process_ai_request_with_prompt, args=(full_prompt_for_analysis, False, True), daemon=True).start()

    def _test_llm_connection(self):
        self._update_ai_status(f"Testing connection to {self.selected_llm.get()}...")
        test_prompt = "Confirm you are operational." 
        threading.Thread(target=self._process_ai_request_with_prompt, args=(test_prompt, True), daemon=True).start()

    def _process_ai_request_with_prompt(self, prompt_content, is_test=False, is_analysis=False):
        llm_choice = self.selected_llm.get()
        api_key = self.api_key_var.get().strip() 
        if llm_choice == "OpenAI" and not api_key:
            self.root.after(0, self._update_ai_status, "Error: OpenAI API Key is required.")
            if not is_test: self.root.after(0, self._add_to_chat_history, "assistant", "Error: OpenAI API Key is missing.")
            return
        messages_to_send = [{"role": "user", "content": prompt_content}] if is_test or is_analysis else \
                           (self.ai_chat_history + [{"role": "user", "content": prompt_content}])
        if not is_test and not is_analysis: self.ai_chat_history.append({"role": "user", "content": prompt_content})
        try:
            if llm_choice == "Gemini":
                gemini_payload_content = []
                if len(messages_to_send) == 1 and messages_to_send[0]["role"] == "user":
                    gemini_payload_content = [{"role": "user", "parts": [{"text": messages_to_send[0]["content"]}]}]
                else: 
                    for msg in messages_to_send: 
                        gemini_role = "model" if msg["role"] == "assistant" else "user"
                        gemini_payload_content.append({"role": gemini_role, "parts": [{"text": msg["content"]}]})
                response_content = self._call_gemini_api(gemini_payload_content, api_key) 
            elif llm_choice == "OpenAI":
                response_content = self._call_openai_api(messages_to_send, api_key) 
            else: response_content = "Error: Unknown LLM selected."
            if is_test: self.root.after(0, self._update_ai_status, f"Test for {llm_choice}: {response_content[:100].strip()}...") 
            else: 
                self.ai_chat_history.append({"role": "assistant", "content": response_content})
                self.root.after(0, self._add_to_chat_history, "assistant", response_content)
                self.root.after(0, self._update_ai_status, "Response received. AI Agent Idle.")
        except Exception as e:
            error_message = f"Error communicating with AI: {e}"; print(error_message)
            self.root.after(0, self._update_ai_status, error_message)
            if not is_test: self.root.after(0, self._add_to_chat_history, "assistant", error_message)

    def _call_gemini_api(self, contents_payload, api_key_param): 
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key_param}" 
        payload = {"contents": contents_payload} 
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(api_url, data=data, headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=30) as response: 
                result_json = json.load(response)
                candidates = result_json.get("candidates")
                if candidates and candidates[0].get("content") and candidates[0]["content"].get("parts") and \
                   candidates[0]["content"]["parts"][0].get("text"):
                    return candidates[0]["content"]["parts"][0]["text"]
                elif result_json.get("promptFeedback"): return f"Gemini API Error: Blocked - {result_json.get('promptFeedback')}"
                else: return f"Error: Unexpected Gemini API response. {str(result_json)[:200]}"
        except urllib.error.HTTPError as e:
            error_body = e.read().decode(); print(f"Gemini HTTP Error Body: {error_body}")
            return f"Gemini API Error: {e.code} - {e.reason}\nDetails: {error_body[:200]}"
        except Exception as e: return f"Error calling Gemini API: {str(e)[:200]}"

    def _call_openai_api(self, messages_history, api_key):
        api_url = "https://api.openai.com/v1/chat/completions"
        headers = { 'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json' }
        payload = { "model": "gpt-3.5-turbo", "messages": messages_history }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(api_url, data=data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=30) as response: 
                result_json = json.load(response)
                if result_json.get("choices") and result_json["choices"][0].get("message"):
                    return result_json["choices"][0]["message"]["content"]
                else: return f"Error: Unexpected OpenAI API response format. {str(result_json)[:200]}"
        except urllib.error.HTTPError as e:
            error_body = e.read().decode(); print(f"OpenAI HTTP Error Body: {error_body}")
            return f"OpenAI API Error: {e.code} - {e.reason}\nDetails: {error_body[:200]}"
        except Exception as e: return f"Error calling OpenAI API: {str(e)[:200]}"


def ui_state_main_controls(app, state):
    app.play_button.config(state=state); app.record_button.config(state=state) 
    app.reset_button.config(state=state)
    app.channel_count_combo.config(state="readonly" if state == tk.NORMAL else tk.DISABLED)
    app.max_freq_combo.config(state="readonly" if state == tk.NORMAL else tk.DISABLED)
    app.freq_preset_combo.config(state="readonly" if state == tk.NORMAL else tk.DISABLED)
    if hasattr(app, 'save_button'): app.save_button.config(state=state)
    if hasattr(app, 'load_button'): app.load_button.config(state=state)
    if hasattr(app, 'apply_json_text_button'): app.apply_json_text_button.config(state=state)

def ui_state_playback(app, channel_controls_state, combo_box_state): 
    app.play_button.config(state=tk.DISABLED if channel_controls_state == tk.DISABLED else tk.NORMAL)
    app.stop_button.config(state=tk.NORMAL if channel_controls_state == tk.DISABLED else tk.DISABLED)
    app.record_button.config(state=channel_controls_state); app.reset_button.config(state=channel_controls_state)
    app.channel_count_combo.config(state=combo_box_state)
    app.freq_preset_combo.config(state=combo_box_state) 
    app.max_freq_combo.config(state=combo_box_state) 
    
    rec_ai_tab_state = tk.DISABLED if app.is_playing or app.is_recording else tk.NORMAL 
    main_controls_during_rec_ai = tk.DISABLED if app.is_recording else channel_controls_state 

    if hasattr(app, 'start_rec_button'):
        app.start_rec_button.config(state=tk.DISABLED if app.is_playing else tk.NORMAL) 
        app.recording_duration_entry.config(state=tk.DISABLED if app.is_playing or app.is_recording else tk.NORMAL)
        app.clear_keyframes_button.config(state=tk.DISABLED if app.is_playing or app.is_recording else tk.NORMAL)
        app.automation_channel_combo.config(state=tk.DISABLED if app.is_playing or app.is_recording else "readonly")
        if hasattr(app, 'canvas_vol_auto'): 
            if app.is_playing or app.is_recording:
                if hasattr(app, '_vol_auto_click_cid') and app._vol_auto_click_cid:
                    app.canvas_vol_auto.mpl_disconnect(app._vol_auto_click_cid); app._vol_auto_click_cid = None
            else:
                if not hasattr(app, '_vol_auto_click_cid') or not app._vol_auto_click_cid:
                     app._vol_auto_click_cid = app.canvas_vol_auto.mpl_connect('button_press_event', app._on_volume_graph_click)
    
    if hasattr(app, 'ai_message_entry'):
        app.ai_message_entry.config(state=rec_ai_tab_state)
        app.llm_selector.config(state=rec_ai_tab_state if rec_ai_tab_state == tk.DISABLED else "readonly")
        app.test_connection_button.config(state=rec_ai_tab_state)
        app.api_key_entry.config(state=rec_ai_tab_state)
        if hasattr(app, 'analyze_config_button'): app.analyze_config_button.config(state=rec_ai_tab_state)


    for i in range(app.displayed_channels_count.get()): app.channels[i].set_controls_state(main_controls_during_rec_ai)

if __name__ == "__main__":
    main_root_window = tk.Tk()
    app_instance = AudioEntrainmentApp(main_root_window)
    main_root_window.protocol("WM_DELETE_WINDOW", app_instance.on_closing)
    main_root_window.mainloop()
