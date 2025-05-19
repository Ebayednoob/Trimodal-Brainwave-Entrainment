import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from pylsl import StreamInlet, resolve_byprop
import threading
import time
import collections # For deque, to store plot data

# --- Matplotlib Imports ---
# Ensure matplotlib is installed: pip install matplotlib
try:
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("Matplotlib not found. Graphs will not be displayed. Please install it: pip install matplotlib")

# Configuration
STREAM_TYPE = 'EEG'
EXPECTED_CHANNELS = 5
BAND_LABELS = ["Rel. Delta", "Rel. Theta", "Rel. Alpha", "Rel. Beta", "Rel. Gamma"]
PLOT_HISTORY_SIZE = 100 # Number of data points to show on the graphs (e.g., 100 points at 10Hz = 10 seconds)

class NeurofeedbackApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Neurofeedback Display with Graphs")
        # Increased size to accommodate graphs
        self.root.geometry("800x750" if MATPLOTLIB_AVAILABLE else "500x600")


        self.is_streaming = False
        self.inlet = None
        self.stream_thread = None

        # Data buffers for plots
        self.plot_data = [collections.deque(np.zeros(PLOT_HISTORY_SIZE), maxlen=PLOT_HISTORY_SIZE) for _ in range(EXPECTED_CHANNELS)]
        self.plot_lines = [None] * EXPECTED_CHANNELS
        self.fig = None
        self.canvas_widget = None

        # --- UI Elements ---
        # Main frame that will hold controls on left, plots on right (if available)
        top_level_frame = ttk.Frame(root)
        top_level_frame.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

        # Left panel for controls and log
        left_panel = ttk.Frame(top_level_frame, width=350) # Fixed width for control panel
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_panel.pack_propagate(False) # Prevent left_panel from shrinking

        # Title
        self.title_label = ttk.Label(left_panel, text="EEG Band Powers", font=("Helvetica", 16, "bold"))
        self.title_label.pack(pady=(0,10), anchor='center')

        # Connection Status
        self.connection_status_var = tk.StringVar(value="Status: Not Connected")
        self.status_label = ttk.Label(left_panel, textvariable=self.connection_status_var, font=("Helvetica", 10))
        self.status_label.pack(pady=(0,10), anchor='center')

        # Connect Button
        self.connect_button = ttk.Button(left_panel, text="Connect to EEG Stream", command=self.toggle_connection)
        self.connect_button.pack(pady=5, anchor='center')

        # Data Display Frame
        self.data_frame = ttk.LabelFrame(left_panel, text="Current Brainwave Data")
        self.data_frame.pack(pady=10, padx=5, fill="x")

        self.band_value_vars = []
        for i in range(EXPECTED_CHANNELS):
            frame = ttk.Frame(self.data_frame)
            frame.pack(fill="x", padx=5, pady=2)
            label_text = BAND_LABELS[i] if i < len(BAND_LABELS) else f"Channel {i+1}"
            label = ttk.Label(frame, text=f"{label_text}:", width=15, anchor="w")
            label.pack(side=tk.LEFT)
            value_var = tk.StringVar(value="N/A")
            value_label = ttk.Label(frame, textvariable=value_var, width=10, anchor="e")
            value_label.pack(side=tk.RIGHT, padx=(0,5))
            self.band_value_vars.append(value_var)

        # Log Area Frame
        log_frame = ttk.LabelFrame(left_panel, text="Log Output")
        log_frame.pack(pady=10, padx=5, expand=True, fill=tk.BOTH)
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)
        
        self.instructions_label = ttk.Label(
            left_panel,
            text="Instructions:\n1. Ensure Muse/Simulator is streaming via LSL.\n2. Click 'Connect'. Check log for stream details.",
            justify=tk.LEFT, font=("Helvetica", 9)
        )
        self.instructions_label.pack(pady=(5,0), anchor='w')

        # Right panel for plots (if matplotlib is available)
        if MATPLOTLIB_AVAILABLE:
            right_panel = ttk.LabelFrame(top_level_frame, text="Time-Domain EEG Graphs")
            right_panel.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH)
            self.setup_plots(right_panel)
        else:
            self.log_message("Matplotlib not found. Graphs are disabled.")
            warning_label = ttk.Label(top_level_frame, text="Matplotlib not found. Install it to see graphs.", foreground="red")
            warning_label.pack(side=tk.RIGHT, expand=True, fill=tk.BOTH, padx=10, pady=10)


        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log_message("Application started.")
        if not MATPLOTLIB_AVAILABLE:
             self.log_message("To enable graphs, please install matplotlib: pip install matplotlib")

    def setup_plots(self, parent_frame):
        """Sets up the matplotlib figure and subplots."""
        if not MATPLOTLIB_AVAILABLE:
            return

        # Create a figure and a set of subplots
        # Adjust subplot layout for better spacing if needed
        self.fig, self.axes = plt.subplots(EXPECTED_CHANNELS, 1, sharex=True, figsize=(5, 7)) 
        self.fig.tight_layout(pad=2.0) # Add padding between subplots

        if EXPECTED_CHANNELS == 1: # If only one channel, axes is not a list
            self.axes = [self.axes] 

        for i in range(EXPECTED_CHANNELS):
            ax = self.axes[i]
            # Initialize plot with placeholder data
            self.plot_lines[i], = ax.plot(np.arange(PLOT_HISTORY_SIZE), list(self.plot_data[i]), '-')
            ax.set_title(BAND_LABELS[i] if i < len(BAND_LABELS) else f"Channel {i+1}", fontsize=10)
            ax.set_ylim(0, 1) # Assuming relative band powers are between 0 and 1
            ax.set_ylabel("Power", fontsize=8)
            if i == EXPECTED_CHANNELS - 1: # Only show x-label on the bottom plot
                ax.set_xlabel("Time Steps", fontsize=8)
            else:
                ax.set_xticklabels([]) # Hide x-axis labels for upper plots
            ax.tick_params(axis='y', labelsize=8)
            ax.grid(True, linestyle=':', alpha=0.7)


        # Embed the Matplotlib figure in Tkinter
        self.canvas_widget = FigureCanvasTkAgg(self.fig, master=parent_frame)
        self.canvas_widget.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.canvas_widget.draw()
        self.log_message("Graphs initialized.")

    def update_plots(self):
        """Updates the data in the plots and redraws them."""
        if not MATPLOTLIB_AVAILABLE or not self.is_streaming or self.fig is None:
            return

        for i in range(EXPECTED_CHANNELS):
            if self.plot_lines[i]:
                self.plot_lines[i].set_ydata(list(self.plot_data[i]))
                # Optional: Adjust y-axis limits dynamically, but can be jumpy
                # min_val = min(self.plot_data[i])
                # max_val = max(self.plot_data[i])
                # self.axes[i].set_ylim(min_val - 0.1*(max_val-min_val+1e-6), max_val + 0.1*(max_val-min_val+1e-6))

        # Redraw the canvas
        try:
            self.canvas_widget.draw_idle() # More efficient than draw() for frequent updates
        except Exception as e:
            self.log_message(f"Error drawing canvas: {e}")


    def log_message(self, message):
        if not hasattr(self, 'log_text'):
            print(f"LOG (early): {message}")
            return
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        print(message)

    def toggle_connection(self):
        if not self.is_streaming:
            self.connect_to_stream()
        else:
            self.stop_stream()

    def connect_to_stream(self):
        self.log_message("Attempting to connect to LSL stream...")
        self.connection_status_var.set("Status: Searching...")
        self.root.update_idletasks()

        try:
            self.log_message(f"Searching for LSL streams with type='{STREAM_TYPE}'...")
            streams = resolve_byprop('type', STREAM_TYPE, timeout=5)

            if not streams:
                self.log_message(f"No LSL stream of type '{STREAM_TYPE}' found.")
                messagebox.showerror("Connection Error", f"No LSL stream of type '{STREAM_TYPE}' found.\nMake sure muse-lsl or simulator is streaming.")
                self.connection_status_var.set("Status: Not Connected")
                return

            self.log_message(f"Found {len(streams)} stream(s):")
            for i, stream_info_obj in enumerate(streams):
                self.log_message(f"  {i}: Name: '{stream_info_obj.name()}', Type: '{stream_info_obj.type()}', Channels: {stream_info_obj.channel_count()}, UID: {stream_info_obj.uid()}")
            
            selected_stream_info = streams[0]
            self.log_message(f"Connecting to stream: '{selected_stream_info.name()}' (UID: {selected_stream_info.uid()})")

            self.inlet = StreamInlet(selected_stream_info, max_chunklen=1)
            stream_info = self.inlet.info()
            self.log_message(f"Successfully connected to LSL stream: '{stream_info.name()}'")
            self.log_message(f"  Type: {stream_info.type()}, Channels: {stream_info.channel_count()}, Nominal Rate: {stream_info.nominal_srate()}")
            self.log_message(f"  Source ID: {stream_info.source_id()}")

            if stream_info.channel_count() != EXPECTED_CHANNELS:
                warning_msg = (f"Connected stream '{stream_info.name()}' has {stream_info.channel_count()} channels, "
                               f"expected {EXPECTED_CHANNELS}. Data/Graph display might be incorrect.")
                self.log_message(f"WARNING: {warning_msg}")
                messagebox.showwarning("Stream Warning", warning_msg)
            
            self.connection_status_var.set(f"Status: Connected to {stream_info.name()}")
            self.is_streaming = True
            self.connect_button.config(text="Disconnect")
            
            # Reset plot data on new connection
            if MATPLOTLIB_AVAILABLE:
                for i in range(EXPECTED_CHANNELS):
                    self.plot_data[i] = collections.deque(np.zeros(PLOT_HISTORY_SIZE), maxlen=PLOT_HISTORY_SIZE)
                self.update_plots()


            self.stream_thread = threading.Thread(target=self.fetch_data_loop, daemon=True)
            self.stream_thread.start()
            self.log_message("Data fetching thread started.")

        except Exception as e:
            self.log_message(f"Connection Error: {e}")
            messagebox.showerror("Connection Error", f"Could not connect to LSL stream: {e}")
            self.connection_status_var.set("Status: Error")
            self.is_streaming = False
            self.connect_button.config(text="Connect to EEG Stream")


    def fetch_data_loop(self):
        try:
            while self.is_streaming and self.inlet:
                sample, timestamp = self.inlet.pull_sample(timeout=1.0) 
                if sample:
                    self.root.after(0, self.update_gui, sample, timestamp)
        except Exception as e:
            if self.is_streaming:
                self.log_message(f"Error during streaming: {e}")
                self.root.after(0, lambda: messagebox.showerror("Streaming Error", f"Lost connection or error: {e}"))
                self.root.after(0, self.stop_stream)

    def update_gui(self, sample, timestamp):
        # Update numerical displays
        if len(sample) == EXPECTED_CHANNELS:
            for i in range(EXPECTED_CHANNELS):
                self.band_value_vars[i].set(f"{sample[i]:.3f}")
                if MATPLOTLIB_AVAILABLE:
                    self.plot_data[i].append(sample[i]) # Add new data to plot buffer
        elif len(sample) > 0:
            self.log_message(f"Data update: Received sample with {len(sample)} values, expected {EXPECTED_CHANNELS}.")
            for i in range(min(len(sample), EXPECTED_CHANNELS)):
                self.band_value_vars[i].set(f"{sample[i]:.3f}")
                if MATPLOTLIB_AVAILABLE:
                     self.plot_data[i].append(sample[i])
            for i in range(len(sample), EXPECTED_CHANNELS):
                self.band_value_vars[i].set("N/A (Mismatch)")
                if MATPLOTLIB_AVAILABLE: # Fill with 0 or NaN if mismatch for plotting
                    self.plot_data[i].append(0) 
        else:
            self.log_message(f"Data update: Received empty or invalid sample.")
            for i in range(EXPECTED_CHANNELS):
                self.band_value_vars[i].set("N/A (Data error)")
                if MATPLOTLIB_AVAILABLE:
                    self.plot_data[i].append(0) # Fill with 0 or NaN

        # Update plots
        if MATPLOTLIB_AVAILABLE:
            self.update_plots()


    def stop_stream(self):
        self.log_message("Stopping stream...")
        self.is_streaming = False
        if self.stream_thread and self.stream_thread.is_alive():
            self.log_message("Waiting for data fetching thread to join...")
            self.stream_thread.join(timeout=1.5)
            if self.stream_thread.is_alive():
                 self.log_message("Warning: Data fetching thread did not join in time.")
            else:
                 self.log_message("Data fetching thread joined.")
        
        if self.inlet:
            self.log_message("Closing LSL inlet...")
            try:
                self.inlet.close_stream()
                self.log_message("LSL inlet closed.")
            except Exception as e:
                self.log_message(f"Error closing LSL inlet: {e}")
            self.inlet = None
        
        self.connection_status_var.set("Status: Disconnected")
        self.connect_button.config(text="Connect to EEG Stream")
        for var in self.band_value_vars:
            var.set("N/A")
        # Optionally clear plots or leave last state
        # if MATPLOTLIB_AVAILABLE:
        #     for i in range(EXPECTED_CHANNELS):
        #         self.plot_data[i] = collections.deque(np.zeros(PLOT_HISTORY_SIZE), maxlen=PLOT_HISTORY_SIZE)
        #     self.update_plots()
        self.log_message("Streaming stopped and UI reset.")

    def on_closing(self):
        self.log_message("Application closing...")
        if self.is_streaming:
            self.stop_stream()
        
        # Properly close matplotlib figure
        if MATPLOTLIB_AVAILABLE and self.fig:
            plt.close(self.fig)
            self.log_message("Matplotlib figure closed.")

        self.root.destroy()

if __name__ == "__main__":
    main_root = tk.Tk()
    app = NeurofeedbackApp(main_root)
    main_root.mainloop()
