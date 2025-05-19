import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import time
import random
import math
# No numpy needed for these basic signal generators, but can be added if complex signals are desired.
from pylsl import StreamInfo, StreamOutlet

# --- Configuration (Copied from the original simulator) ---
STREAM_NAME = 'SimulatedEEG_GUI' # Slightly different name to distinguish if both run
STREAM_TYPE = 'EEG'
CHANNEL_COUNT = 5
SAMPLE_RATE = 10  # Hz
CHANNEL_FORMAT = 'float32'
UNIQUE_ID = 'my_simulated_eeg_gui_source_67890'

# --- Signal Generation Parameters (Copied) ---
def generate_delta_signal(t):
    return 0.5 + 0.5 * math.sin(2 * math.pi * 0.5 * t)

def generate_theta_signal(t):
    return 0.5 + 0.5 * math.sin(2 * math.pi * 1.5 * t)

def generate_alpha_signal(t):
    return 0.6 + 0.4 * math.sin(2 * math.pi * 2.5 * t) + random.uniform(-0.1, 0.1)

def generate_beta_signal(t):
    return 0.4 + 0.3 * math.sin(2 * math.pi * 4 * t) + 0.1 * math.sin(2 * math.pi * 8 * t)

def generate_gamma_signal(t):
    return random.uniform(0.1, 0.5)

SIGNAL_GENERATORS = [
    generate_delta_signal,
    generate_theta_signal,
    generate_alpha_signal,
    generate_beta_signal,
    generate_gamma_signal
]
CHANNEL_LABELS_SIM = ["SimDelta", "SimTheta", "SimAlpha", "SimBeta", "SimGamma"]


class SimulatorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("LSL EEG Simulator Control")
        self.root.geometry("450x400")

        self.is_simulating = False
        self.simulation_thread = None
        self.lsl_outlet = None
        self.start_time = 0

        # --- UI Elements ---
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(expand=True, fill=tk.BOTH)

        title_label = ttk.Label(main_frame, text="LSL EEG Simulator", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=(0, 10))

        self.status_var = tk.StringVar(value="Status: Not Simulating")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, font=("Helvetica", 10))
        status_label.pack(pady=(0, 10))

        self.toggle_button = ttk.Button(main_frame, text="Start Simulation", command=self.toggle_simulation)
        self.toggle_button.pack(pady=10)
        
        # Stream Info Display
        info_frame = ttk.LabelFrame(main_frame, text="Stream Details")
        info_frame.pack(pady=10, padx=5, fill="x")

        ttk.Label(info_frame, text=f"Stream Name: {STREAM_NAME}").pack(anchor="w", padx=5)
        ttk.Label(info_frame, text=f"Stream Type: {STREAM_TYPE}").pack(anchor="w", padx=5)
        ttk.Label(info_frame, text=f"Channels: {CHANNEL_COUNT} ({', '.join(CHANNEL_LABELS_SIM)})").pack(anchor="w", padx=5)
        ttk.Label(info_frame, text=f"Sample Rate: {SAMPLE_RATE} Hz").pack(anchor="w", padx=5)


        # Log Area
        log_frame = ttk.LabelFrame(main_frame, text="Log")
        log_frame.pack(pady=10, padx=5, expand=True, fill=tk.BOTH)

        self.log_text_area = scrolledtext.ScrolledText(log_frame, height=8, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text_area.pack(expand=True, fill=tk.BOTH, padx=5, pady=5)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.log_message("Simulator GUI initialized.")
        if len(SIGNAL_GENERATORS) != CHANNEL_COUNT:
            self.log_message(f"ERROR: CHANNEL_COUNT is {CHANNEL_COUNT} but SIGNAL_GENERATORS has {len(SIGNAL_GENERATORS)} functions.")
            messagebox.showerror("Configuration Error", "Mismatch in channel count and signal generators.")
            self.toggle_button.config(state=tk.DISABLED)


    def log_message(self, message):
        self.log_text_area.config(state=tk.NORMAL)
        self.log_text_area.insert(tk.END, f"{time.strftime('%H:%M:%S')} - {message}\n")
        self.log_text_area.see(tk.END)
        self.log_text_area.config(state=tk.DISABLED)
        print(message) # Also print to console

    def toggle_simulation(self):
        if not self.is_simulating:
            self.start_simulation()
        else:
            self.stop_simulation()

    def start_simulation(self):
        self.log_message("Starting simulation...")
        try:
            # Create LSL StreamInfo
            info = StreamInfo(STREAM_NAME, STREAM_TYPE, CHANNEL_COUNT, SAMPLE_RATE, CHANNEL_FORMAT, UNIQUE_ID)
            
            # Add channel metadata (optional but good)
            chans = info.desc().append_child("channels")
            for label in CHANNEL_LABELS_SIM:
                ch = chans.append_child("channel")
                ch.append_child_value("label", label)
                ch.append_child_value("unit", "relative_power")
                ch.append_child_value("type", "EEG_Band")

            # Create LSL Outlet
            self.lsl_outlet = StreamOutlet(info)
            self.log_message(f"LSL Stream '{STREAM_NAME}' created and broadcasting.")
            
            self.is_simulating = True
            self.toggle_button.config(text="Stop Simulation")
            self.status_var.set(f"Status: Simulating ({STREAM_NAME})")
            self.start_time = time.time()

            # Start the simulation loop in a new thread
            self.simulation_thread = threading.Thread(target=self.simulation_loop, daemon=True)
            self.simulation_thread.start()
            self.log_message("Simulation thread started.")

        except Exception as e:
            self.log_message(f"Error starting simulation: {e}")
            messagebox.showerror("Simulation Error", f"Could not start LSL stream: {e}")
            self.status_var.set("Status: Error")
            if self.lsl_outlet: # Should not happen if error was in StreamInfo or Outlet creation
                self.lsl_outlet = None # Dereference
            self.is_simulating = False


    def simulation_loop(self):
        """Continuously generates and sends data via LSL."""
        try:
            while self.is_simulating and self.lsl_outlet:
                current_sim_time = time.time() - self.start_time
                
                sample = [gen(current_sim_time) for gen in SIGNAL_GENERATORS]
                sample = [max(0.0, min(1.0, val)) for val in sample] # Clamp values

                self.lsl_outlet.push_sample(sample)
                
                # Log a sample occasionally, not every time to avoid flooding the log
                # if int(current_sim_time * SAMPLE_RATE) % (SAMPLE_RATE * 5) == 0: # Log every 5 seconds
                #     self.root.after(0, self.log_message, f"Sent sample: {[f'{s:.2f}' for s in sample]}")

                time.sleep(1.0 / SAMPLE_RATE)
        except Exception as e:
            # This might happen if the outlet is suddenly gone or another LSL error
            if self.is_simulating: # Only log if we were supposed to be running
                self.root.after(0, self.log_message, f"Error in simulation loop: {e}")
                # self.root.after(0, self.stop_simulation) # Consider stopping automatically
        finally:
            self.root.after(0, self.log_message, "Simulation loop ended.")


    def stop_simulation(self):
        self.log_message("Stopping simulation...")
        self.is_simulating = False # Signal the thread to stop

        if self.simulation_thread and self.simulation_thread.is_alive():
            self.log_message("Waiting for simulation thread to join...")
            self.simulation_thread.join(timeout=2.0) # Wait for the thread to finish
            if self.simulation_thread.is_alive():
                self.log_message("Warning: Simulation thread did not join in time.")
            else:
                self.log_message("Simulation thread joined.")
        
        # The LSL outlet is managed by pylsl and should close when dereferenced or program exits.
        # Explicitly setting to None helps ensure it's garbage collected if no other refs exist.
        if self.lsl_outlet:
            self.log_message(f"LSL outlet for '{STREAM_NAME}' will be closed.")
            self.lsl_outlet = None 
        
        self.toggle_button.config(text="Start Simulation")
        self.status_var.set("Status: Not Simulating")
        self.log_message("Simulation stopped.")

    def on_closing(self):
        self.log_message("Application closing...")
        if self.is_simulating:
            self.stop_simulation()
        self.root.destroy()

if __name__ == "__main__":
    gui_root = tk.Tk()
    app = SimulatorGUI(gui_root)
    gui_root.mainloop()
