import tkinter as tk
from tkinter import ttk, colorchooser, filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk, ImageOps
import os
import math
import itertools
import json 
import threading 
import datetime 
import re # For parsing imported data

# Attempt to import google.generativeai
try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("Warning: Google Generative AI SDK (google-generativeai) not found. LLM features will be simulated or unavailable.")


# --- Configuration ---
INITIAL_VISUAL_GRID_SIZE = 20
INITIAL_PIXELS_PER_CM = 4.0 
MAX_PIXELS_PER_CM = 10.0    
INITIAL_SYMBOL_WIDTH_CM = 5.0
INITIAL_SYMBOL_HEIGHT_CM = 5.0
INITIAL_TARGET_SPINE_LENGTH_CM = 100.0 
HEAD_OFFSET_FROM_SPINE_ANCHOR_CM = 10.0  
SPINE_START_INSET_FROM_BODY_VISUAL_EDGE_CM = 25.0 # New: For initial placement

REAL_WORLD_WIDTH_FEET = 6.0
REAL_WORLD_HEIGHT_FEET = 4.0
FEET_TO_CM = 30.48
REAL_WORLD_WIDTH_CM = REAL_WORLD_WIDTH_FEET * FEET_TO_CM
REAL_WORLD_HEIGHT_CM = REAL_WORLD_HEIGHT_FEET * FEET_TO_CM

CANVAS_VISIBLE_WIDTH = 950
CANVAS_VISIBLE_HEIGHT = 650

LINE_COLOR_MAP = { "speaker": "blue", "magnet": "gold", "light": "red" }
DISTANCE_TEXT_COLOR = "black"

BODY_SYMBOL_FILENAME = "Body symbol.png"
BODY_SYMBOL_REAL_OBJECT_HEIGHT_FEET = 5.0 
BODY_SYMBOL_REAL_OBJECT_WIDTH_FEET = 2.0
BODY_SYMBOL_OBJECT_CM_HEIGHT = BODY_SYMBOL_REAL_OBJECT_HEIGHT_FEET * FEET_TO_CM
BODY_SYMBOL_OBJECT_CM_WIDTH = BODY_SYMBOL_REAL_OBJECT_WIDTH_FEET * FEET_TO_CM
BODY_SYMBOL_DISPLAY_ROTATION = 90 

CALIBRATION_POINT_RADIUS_CM = 1.0 
CALIBRATION_HEAD_COLOR = "orange"
CALIBRATION_SPINE_COLOR = "purple"

PRESET_ALIGNMENT_PROMPT = """Prompt: Audio Entrainment Alignment Analyzer
You are an AI agent specializing in audio entrainment optimization. Your task is to analyze Alignment Data and provide recommendations for optimal speaker placement, frequency distribution, and waveform interaction within a 6ft x 4ft test environment, where the subject is centered lengthwise.

Goals:
Assess spatial coherence: How well the nodes are positioned for brainwave entrainment.
Optimize frequency mapping: Ensure the placement supports binaural beats, monaural beats, and isochronic tones.
Refine wave interaction dynamics: Identify potential phase interference patterns and suggest angle adjustments.
Evaluate surround sound virtualization: Consider 5.1 spatialization for full-body immersion.

Input Format (Alignment Data) will be attached at the end, and will contain the following information:
Calibration Points:
Head Center (X, Y)
Spine Start (X, Y)
Spine End (X, Y)
Actual Spine Length vs. Target Length
Placed Nodes:
Node ID & Type (speaker, light, magnet)
Position (X, Y)
Size (W x H)
Angle (degrees)

Analysis Requirements
Speaker Placement:
Are speakers properly positioned for binaural and monaural wave propagation?
Does the spatial distribution reinforce isochronic pulse clarity?
Should angles be adjusted to enhance resonance patterns?
Waveform Interactions:
Identify standing wave risks.
Propose node spacing refinements for phase reinforcement.
5.1 Surround Integration:
Determine ideal speaker positions for virtualized surround sound.
Suggest configurations that maximize entrainment efficiency.
Exclusions
Magnetic Nodes: Mention only in relation to closest meridian points, but focus primarily on audio entrainment effects.
Output Expectations
Summary of current layout efficiency.
Recommendations for node repositioning.
Suggestions for phase alignment optimizations.
Potential frequency adjustments based on cymatic principles.

--- ALIGNMENT DATA TO ANALYZE ---
"""


# --- Node List Window Class ---
class NodeListWindow(tk.Toplevel):
    def __init__(self, master_app):
        super().__init__(master_app.master)
        self.master_app = master_app
        self.title("Node List & Properties")
        self.geometry("550x400")
        self.protocol("WM_DELETE_WINDOW", self.master_app.toggle_node_list_window)

        tree_frame = ttk.Frame(self)
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(10,0))

        self.tree = ttk.Treeview(tree_frame, columns=("id", "label", "type", "x", "y", "w", "h", "angle"), show="headings")
        self.tree.heading("id", text="ID"); self.tree.column("id", width=40, anchor=tk.CENTER)
        self.tree.heading("label", text="Label"); self.tree.column("label", width=100)
        self.tree.heading("type", text="Type"); self.tree.column("type", width=60, anchor=tk.W)
        self.tree.heading("x", text="X (cm)"); self.tree.column("x", width=60, anchor=tk.E)
        self.tree.heading("y", text="Y (cm)"); self.tree.column("y", width=60, anchor=tk.E)
        self.tree.heading("w", text="W (cm)"); self.tree.column("w", width=60, anchor=tk.E)
        self.tree.heading("h", text="H (cm)"); self.tree.column("h", width=60, anchor=tk.E)
        self.tree.heading("angle", text="Angle (°)"); self.tree.column("angle", width=50, anchor=tk.E)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.bind("<<TreeviewSelect>>", self.on_list_select)

        edit_frame = ttk.LabelFrame(self, text="Edit Selected Node Label", padding=5)
        edit_frame.pack(fill=tk.X, padx=10, pady=10)
        self.label_var = tk.StringVar()
        self.label_entry = ttk.Entry(edit_frame, textvariable=self.label_var, width=30)
        self.label_entry.pack(side=tk.LEFT, padx=(0,5), expand=True, fill=tk.X)
        self.set_label_button = ttk.Button(edit_frame, text="Update Label", command=self.update_node_label_from_list)
        self.set_label_button.pack(side=tk.LEFT)
        self.populate_list()

    def populate_list(self):
        for i in self.tree.get_children(): self.tree.delete(i)
        for idx, node_data in enumerate(self.master_app.nodes):
            self.tree.insert("", tk.END, iid=str(idx), values=(
                idx + 1, node_data.get('label', f"Node {idx+1}"), node_data['type'],
                f"{node_data['cm_x']:.1f}", f"{node_data['cm_y']:.1f}",
                f"{node_data['symbol_cm_width']:.1f}", f"{node_data['symbol_cm_height']:.1f}",
                node_data['angle']))

    def on_list_select(self, event):
        selected_items = self.tree.selection()
        if selected_items:
            try:
                node_idx = int(selected_items[0])
                self.master_app.select_node_by_index(node_idx, source="list")
                if 0 <= node_idx < len(self.master_app.nodes):
                    self.label_var.set(self.master_app.nodes[node_idx].get('label', ''))
            except ValueError: print(f"Error converting tree ID '{selected_items[0]}' to int.")

    def update_node_label_from_list(self):
        selected_items = self.tree.selection()
        if selected_items:
            try:
                node_idx = int(selected_items[0])
                self.master_app.update_node_label(node_idx, self.label_var.get())
            except ValueError: print(f"Error updating label: Invalid node index string '{selected_items[0]}'")

    def highlight_selected_node(self, node_index):
        if node_index is None:
            for item in self.tree.selection(): self.tree.selection_remove(item)
        else:
            node_idx_str = str(node_index)
            if self.tree.exists(node_idx_str):
                if not self.tree.selection() or self.tree.selection()[0] != node_idx_str:
                    self.tree.selection_set(node_idx_str)
                    self.tree.focus(node_idx_str); self.tree.see(node_idx_str)
                if 0 <= node_index < len(self.master_app.nodes):
                     self.label_var.set(self.master_app.nodes[node_index].get('label', ''))

# --- Main Application Class ---
class EntrainmentDesignerApp:
    def __init__(self, master):
        self.master = master
        master.title("Bio-Entrainment Therapeutics - Full Body Entrainment Designer")

        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.symbol_folder = os.path.join(self.script_dir, "Symbol-Folder")

        self.nodes = []
        self.selected_tool = None
        self.selected_node_index = None

        self.visual_grid_size_px = tk.IntVar(value=INITIAL_VISUAL_GRID_SIZE)
        self.pixels_per_cm = tk.DoubleVar(value=INITIAL_PIXELS_PER_CM) 
        self.current_symbol_width_cm_var = tk.DoubleVar(value=INITIAL_SYMBOL_WIDTH_CM)
        self.current_symbol_height_cm_var = tk.DoubleVar(value=INITIAL_SYMBOL_HEIGHT_CM)
        self.angle_slider_var = tk.DoubleVar(value=0)
        self.target_spine_length_cm_var = tk.DoubleVar(value=INITIAL_TARGET_SPINE_LENGTH_CM)


        self.show_distances_var = tk.BooleanVar(value=False)
        self.node_list_window = None
        self.node_id_counter = 0

        self.node_images_pil = {} 
        self.body_symbol_pil = None 
        self.show_body_symbol_var = tk.BooleanVar(value=False)
        self.flip_body_orientation_var = tk.BooleanVar(value=False) 
        self.calibration_points = [] 

        self.genai_available = GENAI_AVAILABLE 
        if self.genai_available:
            self.genai = genai 

        self.load_assets() 

        self.llm_api_key_var = tk.StringVar()
        self.chat_history = [] 

        main_notebook = ttk.Notebook(master)
        main_notebook.pack(expand=True, fill='both', padx=5, pady=5)

        designer_tab_frame = ttk.Frame(main_notebook, padding="5")
        main_notebook.add(designer_tab_frame, text='Designer')
        self.create_designer_tab(designer_tab_frame)

        llm_tab_frame = ttk.Frame(main_notebook, padding="5")
        main_notebook.add(llm_tab_frame, text='LLM Control Panel')
        self.create_llm_tab(llm_tab_frame)
        
        self.visual_grid_size_px.trace_add("write", self.on_visual_grid_size_change)
        self.pixels_per_cm.trace_add("write", self.on_pixel_scale_change_via_var)
        self.current_symbol_width_cm_var.trace_add("write", self.on_current_symbol_dim_change)
        self.current_symbol_height_cm_var.trace_add("write", self.on_current_symbol_dim_change)
        self.show_body_symbol_var.trace_add("write", lambda *args: self.redraw_canvas())
        self.flip_body_orientation_var.trace_add("write", self._handle_orientation_flip_trace)

        self.update_canvas_scrollregion() 
        self.draw_grid() 
        self.canvas.bind("<Button-1>", self.on_canvas_click) 
        self.canvas.bind("<Button-3>", self.on_canvas_right_click) 
        self._update_button_styles()
        self._update_alignment_data_display() 

    def create_designer_tab(self, parent_frame):
        controls_frame = ttk.LabelFrame(parent_frame, text="Tools & Controls", padding="10")
        controls_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N), pady=(0,10))
        for i in range(8): controls_frame.columnconfigure(i, weight=1) 

        col = 0
        node_select_frame = ttk.Frame(controls_frame); node_select_frame.grid(row=0, column=col, rowspan=5, sticky=(tk.N, tk.S, tk.W), padx=5, pady=5); col+=1
        ttk.Label(node_select_frame, text="Select Node:").pack(anchor=tk.W)
        self.speaker_button = ttk.Button(node_select_frame, text="Speaker", command=lambda: self.select_tool("speaker")); self.speaker_button.pack(fill=tk.X, pady=2)
        self.magnet_button = ttk.Button(node_select_frame, text="Magnet", command=lambda: self.select_tool("magnet")); self.magnet_button.pack(fill=tk.X, pady=2)
        self.light_button = ttk.Button(node_select_frame, text="Light", command=lambda: self.select_tool("light")); self.light_button.pack(fill=tk.X, pady=2)

        angle_frame = ttk.Frame(controls_frame); angle_frame.grid(row=0, column=col, rowspan=2, sticky=(tk.N, tk.S, tk.W, tk.E), padx=5, pady=5); col+=1
        ttk.Label(angle_frame, text="Angle (0-359):").pack(anchor=tk.W)
        self.angle_slider = ttk.Scale(angle_frame, from_=0, to=359, variable=self.angle_slider_var, orient=tk.HORIZONTAL, command=self.update_angle_from_slider); self.angle_slider.pack(fill=tk.X, expand=True)
        self.angle_label_var = tk.StringVar(value=f"{int(self.angle_slider_var.get())}°"); ttk.Label(angle_frame, textvariable=self.angle_label_var).pack(anchor=tk.W)
        
        symbol_size_frame = ttk.Frame(controls_frame); symbol_size_frame.grid(row=0, column=col, rowspan=3, sticky=(tk.N, tk.S, tk.W, tk.E), padx=5, pady=5); col+=1
        ttk.Label(symbol_size_frame, text="Symbol Width (cm):").pack(anchor=tk.W)
        self.symbol_width_entry = ttk.Entry(symbol_size_frame, textvariable=self.current_symbol_width_cm_var, width=7); self.symbol_width_entry.pack(anchor=tk.W, pady=(0,2))
        ttk.Label(symbol_size_frame, text="Symbol Height (cm):").pack(anchor=tk.W)
        self.symbol_height_entry = ttk.Entry(symbol_size_frame, textvariable=self.current_symbol_height_cm_var, width=7); self.symbol_height_entry.pack(anchor=tk.W, pady=(0,5))
        self.update_sel_size_button = ttk.Button(symbol_size_frame, text="Update Selected Size", command=self.update_selected_node_symbol_size); self.update_sel_size_button.pack(fill=tk.X)

        grid_scale_frame = ttk.Frame(controls_frame); grid_scale_frame.grid(row=0, column=col, rowspan=3, sticky=(tk.N, tk.S, tk.W, tk.E), padx=5, pady=5); col+=1
        ttk.Label(grid_scale_frame, text="Visual Grid (px):").pack(anchor=tk.W)
        self.grid_size_slider = ttk.Scale(grid_scale_frame, from_=5, to=100, variable=self.visual_grid_size_px, orient=tk.HORIZONTAL, command=self.update_visual_grid_size_display); self.grid_size_slider.pack(fill=tk.X, expand=True)
        self.grid_size_label_var = tk.StringVar(value=f"{INITIAL_VISUAL_GRID_SIZE}px"); ttk.Label(grid_scale_frame, textvariable=self.grid_size_label_var).pack(anchor=tk.W, pady=(0,5))
        ttk.Label(grid_scale_frame, text="Scale (px/cm):").pack(anchor=tk.W)
        self.pixels_per_cm_entry = ttk.Entry(grid_scale_frame, textvariable=self.pixels_per_cm, width=7); self.pixels_per_cm_entry.pack(side=tk.LEFT, padx=(0,5))
        self.set_scale_button = ttk.Button(grid_scale_frame, text="Set", command=self.update_pixel_scale); self.set_scale_button.pack(side=tk.LEFT)

        subject_cal_frame = ttk.Frame(controls_frame); subject_cal_frame.grid(row=0, column=col, rowspan=5, sticky=(tk.N, tk.S, tk.W, tk.E), padx=5, pady=5); col+=1 
        self.show_body_check = ttk.Checkbutton(subject_cal_frame, text="Show Test Subject", variable=self.show_body_symbol_var); self.show_body_check.pack(anchor=tk.W, pady=2, fill=tk.X)
        self.flip_body_check = ttk.Checkbutton(subject_cal_frame, text="Flip Subject 180°", variable=self.flip_body_orientation_var); self.flip_body_check.pack(anchor=tk.W, pady=2, fill=tk.X)
        self.set_cal_button = ttk.Button(subject_cal_frame, text="Set/Clear Calibration", command=self.toggle_calibration_points); self.set_cal_button.pack(fill=tk.X, pady=2)
        ttk.Label(subject_cal_frame, text="Target Spine (cm):").pack(anchor=tk.W, pady=(5,0))
        self.spine_length_entry = ttk.Entry(subject_cal_frame, textvariable=self.target_spine_length_cm_var, width=7); self.spine_length_entry.pack(anchor=tk.W, pady=(0,2))
        self.set_spine_length_button = ttk.Button(subject_cal_frame, text="Set Spine Length", command=self._apply_target_spine_length); self.set_spine_length_button.pack(fill=tk.X)


        other_controls_frame = ttk.Frame(controls_frame); other_controls_frame.grid(row=0, column=col, rowspan=5, sticky=(tk.N, tk.S, tk.W, tk.E), padx=5, pady=5); col+=1
        self.show_distances_check = ttk.Checkbutton(other_controls_frame, text="Show Distances (cm)", variable=self.show_distances_var, command=self.toggle_show_distances); self.show_distances_check.pack(anchor=tk.W, pady=2, fill=tk.X)
        self.delete_node_button = ttk.Button(other_controls_frame, text="Delete Selected Node", command=self.delete_selected_node, state=tk.DISABLED); self.delete_node_button.pack(fill=tk.X, pady=2)
        self.clear_button = ttk.Button(other_controls_frame, text="Clear All Nodes", command=self.clear_canvas_nodes); self.clear_button.pack(fill=tk.X, pady=2)
        self.node_list_button = ttk.Button(other_controls_frame, text="Node List", command=self.toggle_node_list_window); self.node_list_button.pack(fill=tk.X, pady=2)
        
        canvas_frame = ttk.Frame(parent_frame) 
        canvas_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        parent_frame.columnconfigure(0, weight=1); parent_frame.rowconfigure(1, weight=1)    
        self.canvas = tk.Canvas(canvas_frame, width=CANVAS_VISIBLE_WIDTH, height=CANVAS_VISIBLE_HEIGHT, bg="ivory")
        self.canvas.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
        hbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview); hbar.grid(row=1, column=0, sticky=(tk.E, tk.W))
        vbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview); vbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.canvas.configure(xscrollcommand=hbar.set, yscrollcommand=vbar.set)
        canvas_frame.columnconfigure(0, weight=1); canvas_frame.rowconfigure(0, weight=1)
        self.status_var = tk.StringVar()
        self.status_var.set(f"Design Area: {REAL_WORLD_WIDTH_FEET:.1f}ft x {REAL_WORLD_HEIGHT_FEET:.1f}ft. Select a tool.")
        status_bar = ttk.Label(parent_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5,0))

    def create_llm_tab(self, parent_frame):
        llm_main_container = ttk.Frame(parent_frame)
        llm_main_container.pack(fill=tk.BOTH, expand=True)
        llm_main_container.columnconfigure(0, weight=1)
        llm_main_container.rowconfigure(0, weight=0) 
        llm_main_container.rowconfigure(1, weight=3) # Chat takes more space
        llm_main_container.rowconfigure(2, weight=1) # Alignment Data Display 
        llm_main_container.rowconfigure(3, weight=2) # Import Alignment Data

        api_outer_frame = ttk.Frame(llm_main_container)
        api_outer_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        api_config_frame = ttk.LabelFrame(api_outer_frame, text="Gemini API Configuration", padding="10") 
        api_config_frame.pack(fill=tk.X, side=tk.TOP)
        api_key_line_frame = ttk.Frame(api_config_frame)
        api_key_line_frame.pack(fill=tk.X)
        ttk.Label(api_key_line_frame, text="API Key:").pack(side=tk.LEFT, padx=5, pady=5)
        api_key_entry = ttk.Entry(api_key_line_frame, textvariable=self.llm_api_key_var, width=30, show="*")
        api_key_entry.pack(side=tk.LEFT, padx=5, pady=5, expand=True, fill=tk.X)
        test_conn_button = ttk.Button(api_key_line_frame, text="Test Connection", command=self._test_api_connection)
        test_conn_button.pack(side=tk.LEFT, padx=5, pady=5)
        api_status_frame = ttk.LabelFrame(api_outer_frame, text="API Call Status Log", padding="5")
        api_status_frame.pack(fill=tk.X, padx=0, pady=(5,0), side=tk.TOP) 
        self.api_status_display = scrolledtext.ScrolledText(api_status_frame, wrap=tk.WORD, state='disabled', height=4)
        self.api_status_display.pack(fill=tk.X, expand=False, padx=5, pady=5)

        chat_frame = ttk.LabelFrame(llm_main_container, text="Design Chat Assistant (Gemini)", padding="10") 
        chat_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        chat_frame.rowconfigure(0, weight=1); chat_frame.columnconfigure(0, weight=1)
        self.chat_display = scrolledtext.ScrolledText(chat_frame, wrap=tk.WORD, state='disabled', height=10) 
        self.chat_display.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        chat_actions_frame = ttk.Frame(chat_frame)
        chat_actions_frame.grid(row=1, column=0, sticky="ew", pady=(5,0))
        chat_actions_frame.columnconfigure(0, weight=1)
        self.chat_input_var = tk.StringVar()
        chat_entry = ttk.Entry(chat_actions_frame, textvariable=self.chat_input_var, width=60)
        chat_entry.grid(row=0, column=0, sticky="ew", padx=(0,5))
        chat_entry.bind("<Return>", self.send_chat_message_event)
        send_button = ttk.Button(chat_actions_frame, text="Send", command=self.send_chat_message_event)
        send_button.grid(row=0, column=1, padx=(0,5))
        analyze_button = ttk.Button(chat_actions_frame, text="Analyze Alignment", command=self.send_preset_alignment_prompt)
        analyze_button.grid(row=0, column=2, padx=(0,5))
        export_button = ttk.Button(chat_actions_frame, text="Export Data", command=self._export_llm_and_alignment_data)
        export_button.grid(row=0, column=3)

        alignment_data_display_frame = ttk.LabelFrame(llm_main_container, text="Current Alignment Data", padding="10")
        alignment_data_display_frame.grid(row=2, column=0, sticky="nsew", padx=5, pady=(5,5)) 
        alignment_data_display_frame.rowconfigure(0, weight=1); alignment_data_display_frame.columnconfigure(0, weight=1)
        self.alignment_data_display = scrolledtext.ScrolledText(alignment_data_display_frame, wrap=tk.WORD, state='disabled', height=6) 
        self.alignment_data_display.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

        import_data_frame = ttk.LabelFrame(llm_main_container, text="Import/Update Alignment Data", padding="10")
        import_data_frame.grid(row=3, column=0, sticky="nsew", padx=5, pady=(5,5))
        import_data_frame.rowconfigure(0, weight=1); import_data_frame.columnconfigure(0, weight=1)
        self.import_data_text = scrolledtext.ScrolledText(import_data_frame, wrap=tk.WORD, height=6) 
        self.import_data_text.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        load_data_button = ttk.Button(import_data_frame, text="Load Data & Update Designer", command=self._load_and_update_from_imported_data)
        load_data_button.grid(row=1, column=0, pady=(5,0), sticky="ew")


    def _log_api_status(self, message):
        if hasattr(self, 'api_status_display') and self.api_status_display:
            def update_display():
                self.api_status_display.config(state='normal')
                self.api_status_display.insert(tk.END, f"{message}\n")
                self.api_status_display.config(state='disabled')
                self.api_status_display.see(tk.END)
            self.master.after(0, update_display)


    def _append_to_chat_display(self, sender, message):
        self.chat_display.config(state='normal')
        self.chat_display.insert(tk.END, f"{sender}: {message}\n\n")
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)

    def _handle_llm_response(self, response_text, is_preset_prompt, error_message=None):
        if error_message:
            self._append_to_chat_display("System (Error)", error_message)
            self._log_api_status(f"LLM Call Error: {error_message}")
            return

        self._append_to_chat_display("Gemini", response_text)
        self._log_api_status("LLM response received successfully.")
        if not is_preset_prompt: 
            self.chat_history.append({"role": "model", "parts": [{"text": response_text}]})
            if len(self.chat_history) > 20: 
                self.chat_history = self.chat_history[-20:]

    def _test_api_connection_threaded_target(self):
        self._log_api_status("Testing Gemini API connection...")
        if not self.genai_available:
            self.master.after(0, self._handle_test_connection_response, False, "Gemini SDK not installed.")
            return

        api_key = self.llm_api_key_var.get()
        if not api_key:
            self.master.after(0, self._handle_test_connection_response, False, "Gemini API Key is missing.")
            return
        
        try:
            self.genai.configure(api_key=api_key)
            model = self.genai.GenerativeModel('gemini-2.0-flash') 
            response = model.generate_content("test", generation_config=genai.types.GenerationConfig(candidate_count=1, max_output_tokens=5))

            if response.text or (response.parts and response.parts[0].text):
                self.master.after(0, self._handle_test_connection_response, True, "Gemini connection successful!")
            else:
                feedback = response.prompt_feedback if response.prompt_feedback else "No specific feedback."
                self.master.after(0, self._handle_test_connection_response, False, f"Connection test failed: Empty response. Feedback: {feedback}")
        except Exception as e:
            self.master.after(0, self._handle_test_connection_response, False, f"Connection failed: {str(e)}")

    def _handle_test_connection_response(self, success, message):
        self._log_api_status(message)
        if success:
            messagebox.showinfo("API Test", message)
        else:
            messagebox.showerror("API Test Failed", message)


    def _test_api_connection(self):
        threading.Thread(target=self._test_api_connection_threaded_target, daemon=True).start()


    def _make_gemini_api_call_threaded_target(self, contents_for_api, is_preset_prompt):
        self._log_api_status(f"Attempting to send prompt to Gemini ({'preset' if is_preset_prompt else 'chat'})...")
        if not self.genai_available:
            self.master.after(0, self._handle_llm_response, None, is_preset_prompt, "Gemini SDK (google-generativeai) not installed.")
            return

        api_key = self.llm_api_key_var.get()
        if not api_key:
            self.master.after(0, self._handle_llm_response, None, is_preset_prompt, "Gemini API Key is missing.")
            return
        
        try:
            self.genai.configure(api_key=api_key)
            model = self.genai.GenerativeModel('gemini-2.0-flash') 
            response = model.generate_content(contents_for_api)
            
            response_text = ""
            if response.parts:
                response_text = "".join(part.text for part in response.parts if hasattr(part, 'text'))
            elif hasattr(response, 'text') and response.text: 
                 response_text = response.text
            
            if not response_text: 
                if response.prompt_feedback and response.prompt_feedback.block_reason:
                    response_text = f"Blocked by API: {response.prompt_feedback.block_reason}"
                    if response.prompt_feedback.safety_ratings:
                         response_text += f" Safety Ratings: {response.prompt_feedback.safety_ratings}"
                else:
                    response_text = "Received a response, but no direct text part found. Full response might be complex."
                    print(f"Full Gemini Response: {response}")

            self.master.after(0, self._handle_llm_response, response_text, is_preset_prompt)
            self._log_api_status("API call successful.")

        except Exception as e:
            print(f"Gemini API Error: {e}")
            error_detail = str(e)
            if hasattr(e, 'message'): error_detail = e.message
            elif hasattr(e, 'args') and e.args: error_detail = str(e.args[0])
            self.master.after(0, self._handle_llm_response, None, is_preset_prompt, f"API Call Failed: {error_detail}")
            self._log_api_status(f"API call failed: {error_detail}")


    def send_chat_message_event(self, event=None):
        user_message = self.chat_input_var.get().strip()
        if not user_message: return
        self._append_to_chat_display("You", user_message)
        self.chat_input_var.set("")
        self.chat_history.append({"role": "user", "parts": [{"text": user_message}]})
        threading.Thread(target=self._make_gemini_api_call_threaded_target, 
                         args=(list(self.chat_history), False), daemon=True).start()


    def send_preset_alignment_prompt(self):
        alignment_data_str = self.alignment_data_display.get("1.0", tk.END).strip()
        if not self.calibration_points and not self.nodes:
            messagebox.showinfo("No Data", "No alignment data available to analyze.")
            return
        full_prompt = PRESET_ALIGNMENT_PROMPT + "\n" + alignment_data_str
        contents_for_preset_prompt = [{"role": "user", "parts": [{"text": full_prompt}]}]
        self._append_to_chat_display("System (Info)", f"Sending preset alignment analysis prompt...")
        threading.Thread(target=self._make_gemini_api_call_threaded_target, 
                         args=(contents_for_preset_prompt, True), daemon=True).start()

    def _export_llm_and_alignment_data(self):
        self._log_api_status("Preparing data for export...")
        alignment_data = self.alignment_data_display.get("1.0", tk.END).strip()
        chat_data = self.chat_display.get("1.0", tk.END).strip()

        if not alignment_data and not chat_data:
            messagebox.showinfo("No Data to Export", "There is no alignment data or chat history to export.")
            self._log_api_status("Export cancelled: No data.")
            return

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        default_filename = f"BioEntrainmentData_{timestamp}.txt"

        filepath = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=default_filename,
            title="Save Alignment and LLM Data"
        )

        if not filepath:
            self._log_api_status("Export cancelled by user.")
            return

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("=============== CURRENT ALIGNMENT DATA ===============\n")
                f.write(alignment_data)
                f.write("\n\n\n=============== DESIGN CHAT ASSISTANT LOG ===============\n")
                f.write(chat_data)
            messagebox.showinfo("Export Successful", f"Data exported successfully to:\n{filepath}")
            self._log_api_status(f"Data exported to {filepath}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not write to file:\n{e}")
            self._log_api_status(f"Export failed: {e}")

    def _parse_coords(self, line, label):
        match = re.search(rf"{re.escape(label)}.*?\(([\d\.-]+),\s*([\d\.-]+)\)\s*cm", line)
        if match:
            return float(match.group(1)), float(match.group(2))
        return None, None

    def _parse_target_spine_length(self, line):
        match = re.search(r"Target:\s*([\d\.-]+)\s*cm", line)
        if match:
            return float(match.group(1))
        return None
        
    def _load_and_update_from_imported_data(self):
        imported_text = self.import_data_text.get("1.0", tk.END).strip()
        if not imported_text:
            messagebox.showinfo("No Data", "Import data text box is empty.")
            return

        self._log_api_status("Attempting to parse and load imported alignment data...")
        
        new_calibration_points = []
        new_nodes = []
        parsed_target_spine_length = None
        
        try:
            lines = imported_text.splitlines()
            parsing_mode = None 
            current_node_data = {}

            for line in lines:
                line = line.strip()
                if not line: 
                    if parsing_mode == "NODES" and current_node_data.get('type'):
                        new_nodes.append(current_node_data)
                        current_node_data = {}
                    continue

                if "--- CALIBRATION POINTS ---" in line:
                    parsing_mode = "CALIBRATION"; continue
                if "--- PLACED NODES ---" in line:
                    parsing_mode = "NODES"
                    if current_node_data.get('type'): new_nodes.append(current_node_data) 
                    current_node_data = {}; continue

                if parsing_mode == "CALIBRATION":
                    cp_match = re.match(r"- (Head Center|Spine Start|Spine End):\s*\(([\d\.-]+),\s*([\d\.-]+)\)\s*cm", line)
                    if cp_match:
                        label_text, x_str, y_str = cp_match.groups()
                        label_map = {"Head Center": "head_center", "Spine Start": "spine_start", "Spine End": "spine_end"}
                        color_map = {"head_center": CALIBRATION_HEAD_COLOR, "spine_start": CALIBRATION_SPINE_COLOR, "spine_end": CALIBRATION_SPINE_COLOR}
                        new_calibration_points.append({
                            'label': label_map[label_text], 
                            'cm_x': float(x_str), 'cm_y': float(y_str), 
                            'color': color_map[label_map[label_text]]
                        })
                    else:
                        ts_match = re.search(r"Target:\s*([\d\.-]+)\s*cm", line)
                        if ts_match and parsed_target_spine_length is None:
                            parsed_target_spine_length = float(ts_match.group(1))
                
                elif parsing_mode == "NODES":
                    if not current_node_data.get('type'): 
                        nh_match = re.match(r"Node \d+ \('([^']*)'\):\s*(\w+)", line)
                        if nh_match:
                            current_node_data['label'] = nh_match.group(1)
                            node_type_str = nh_match.group(2).lower()
                            if node_type_str in self.node_images_pil:
                                current_node_data['type'] = node_type_str
                                current_node_data['original_pil_image'] = self.node_images_pil[node_type_str]
                            else:
                                print(f"Warning: Unknown node type '{node_type_str}' in import. Skipping node.")
                                current_node_data = {} 
                        continue 

                    if current_node_data.get('type'): 
                        pos_match = re.search(r"Pos:\s*\(([\d\.-]+),\s*([\d\.-]+)\)\s*cm", line)
                        if pos_match:
                            current_node_data['cm_x'] = float(pos_match.group(1))
                            current_node_data['cm_y'] = float(pos_match.group(2))
                            continue
                        
                        size_match = re.search(r"Size:\s*\((\d+\.?\d*)W x (\d+\.?\d*)H\)\s*cm", line)
                        if size_match:
                            current_node_data['symbol_cm_width'] = float(size_match.group(1))
                            current_node_data['symbol_cm_height'] = float(size_match.group(2))
                            continue

                        angle_match = re.search(r"Angle:\s*(\d+)", line)
                        if angle_match:
                            current_node_data['angle'] = int(angle_match.group(1))
                            new_nodes.append(current_node_data) # Angle is last property for a node
                            current_node_data = {} 
                            continue
            
            if parsing_mode == "NODES" and current_node_data.get('type'):
                new_nodes.append(current_node_data)

            self.calibration_points = new_calibration_points
            self.nodes = new_nodes
            self.node_id_counter = len(new_nodes) 

            if parsed_target_spine_length is not None:
                self.target_spine_length_cm_var.set(parsed_target_spine_length)
            elif not new_calibration_points: 
                 self.target_spine_length_cm_var.set(INITIAL_TARGET_SPINE_LENGTH_CM)
            
            self.select_node_by_index(None, source="import_data")
            self.redraw_canvas() 
            self.update_node_list_window_content()
            
            messagebox.showinfo("Import Complete", "Alignment data parsed and designer updated.")
            self._log_api_status("Alignment data imported and designer updated.")
            self.import_data_text.delete('1.0', tk.END) 

        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to parse or apply imported data.\nError: {e}\n\nPlease ensure data is in the correct format.")
            self._log_api_status(f"Import data failed: {e}")


    def load_assets(self): 
        image_files = {"speaker": "Speaker.png", "magnet": "bifiilar.png", "light": "LED.png"}
        for node_type, filename in image_files.items():
            try:
                path = os.path.join(self.symbol_folder, filename)
                img_pil = Image.open(path).convert("RGBA") if os.path.exists(path) else self._create_placeholder_image(node_type, f"Missing: {filename}")
                self.node_images_pil[node_type] = img_pil
            except Exception as e:
                print(f"Error loading node image {filename}: {e}")
                self.node_images_pil[node_type] = self._create_placeholder_image(node_type, "Load Error")
        try:
            body_path = os.path.join(self.symbol_folder, BODY_SYMBOL_FILENAME)
            if os.path.exists(body_path): self.body_symbol_pil = Image.open(body_path).convert("RGBA")
            else:
                print(f"Warning: Body symbol image '{BODY_SYMBOL_FILENAME}' not found.")
                self.body_symbol_pil = self._create_placeholder_image("Body", f"Missing: {BODY_SYMBOL_FILENAME}", 
                                                                    width=int(BODY_SYMBOL_OBJECT_CM_WIDTH), 
                                                                    height=int(BODY_SYMBOL_OBJECT_CM_HEIGHT))
        except Exception as e:
            print(f"Error loading body symbol image: {e}")
            self.body_symbol_pil = self._create_placeholder_image("Body", "Load Error", 
                                                                 width=int(BODY_SYMBOL_OBJECT_CM_WIDTH), 
                                                                 height=int(BODY_SYMBOL_OBJECT_CM_HEIGHT))

    def _create_placeholder_image(self, node_type_text, message, width=50, height=50):
        img = Image.new('RGBA', (width,height) , (200,200,200,100)) 
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img); draw.text((2,2), node_type_text[0].upper(), fill="black")
        return img

    def update_canvas_scrollregion(self):
        current_ppcm = max(0.01, self.pixels_per_cm.get())
        total_px_w = REAL_WORLD_WIDTH_CM*current_ppcm; total_px_h = REAL_WORLD_HEIGHT_CM*current_ppcm
        self.canvas.config(scrollregion=(0,0,max(total_px_w,CANVAS_VISIBLE_WIDTH),max(total_px_h,CANVAS_VISIBLE_HEIGHT)))

    def draw_grid(self):
        self.canvas.delete("grid_line", "world_boundary") 
        s_reg_str = self.canvas.cget("scrollregion")
        if not s_reg_str: return
        try: _,_,scroll_w,scroll_h = map(float,s_reg_str.split())
        except ValueError: print(f"Err parsing scrollregion: {s_reg_str}"); return
        curr_ppcm=max(0.01,self.pixels_per_cm.get())
        world_px_w=REAL_WORLD_WIDTH_CM*curr_ppcm; world_px_h=REAL_WORLD_HEIGHT_CM*curr_ppcm
        vis_grid_px=self.visual_grid_size_px.get()
        if vis_grid_px > 0:
            for i in range(0,int(scroll_w)+1,vis_grid_px): self.canvas.create_line(i,0,i,scroll_h,tag="grid_line",fill="#e0e0e0")
            for i in range(0,int(scroll_h)+1,vis_grid_px): self.canvas.create_line(0,i,scroll_w,i,tag="grid_line",fill="#e0e0e0")
        self.canvas.create_rectangle(0,0,world_px_w-1,world_px_h-1,outline="black",width=1,dash=(4,2),tags="world_boundary")

    def on_visual_grid_size_change(self, *args): self.update_visual_grid_size_display(); self.redraw_canvas() 
    def update_visual_grid_size_display(self, *args): self.grid_size_label_var.set(f"{self.visual_grid_size_px.get()}px")
    def on_pixel_scale_change_via_var(self, *args): self.update_canvas_scrollregion(); self.redraw_canvas()

    def update_pixel_scale(self):
        try:
            val = float(self.pixels_per_cm_entry.get())
            if val <= 0: 
                messagebox.showerror("Invalid Scale","px/cm must be > 0."); 
                self.pixels_per_cm.set(INITIAL_PIXELS_PER_CM); return
            if val > MAX_PIXELS_PER_CM:
                messagebox.showwarning("Scale Limit", f"Max scale is {MAX_PIXELS_PER_CM} px/cm. Setting to max.")
                val = MAX_PIXELS_PER_CM
            
            self.pixels_per_cm.set(val) 
            self.status_var.set(f"Scale: {val:.2f} px/cm. Area: {REAL_WORLD_WIDTH_FEET:.1f}ft x {REAL_WORLD_HEIGHT_FEET:.1f}ft")
        except ValueError: 
            messagebox.showerror("Invalid Input","Enter a valid number for px/cm."); 
            self.pixels_per_cm.set(INITIAL_PIXELS_PER_CM)
    
    def on_current_symbol_dim_change(self, *args): pass

    def update_selected_node_symbol_size(self):
        if self.selected_node_index is None: messagebox.showinfo("No Node Selected","Select node to update size."); return
        try:
            new_w_cm=self.current_symbol_width_cm_var.get(); new_h_cm=self.current_symbol_height_cm_var.get()
            if new_w_cm<=0 or new_h_cm<=0: messagebox.showerror("Invalid Size","Symbol dims > 0."); return
            self.nodes[self.selected_node_index]['symbol_cm_width']=new_w_cm
            self.nodes[self.selected_node_index]['symbol_cm_height']=new_h_cm
            self.redraw_canvas(); self.update_node_list_window_content() 
            self.status_var.set(f"Node {self.selected_node_index+1} size: {new_w_cm:.1f}x{new_h_cm:.1f} cm.")
        except ValueError: messagebox.showerror("Invalid Input","Valid numbers for symbol dims.")

    def select_tool(self, tool_type):
        self.selected_tool = tool_type
        self.select_node_by_index(None, source="tool_change") 
        self.status_var.set(f"{tool_type.capitalize()} selected. Angle: {int(self.angle_slider_var.get())}°")
        self._update_button_styles()

    def _update_button_styles(self):
        buttons = {"speaker":self.speaker_button, "magnet":self.magnet_button, "light":self.light_button}
        style = ttk.Style()
        try: style.layout("Selected.TButton") 
        except tk.TclError: style.configure("Selected.TButton",relief="sunken",background="lightblue"); style.configure("TButton",relief="raised")
        for tool, button in buttons.items(): button.config(style="Selected.TButton" if self.selected_tool == tool else "TButton")
        
    def update_angle_from_slider(self, value_str):
        new_angle = int(float(value_str))
        self.angle_label_var.set(f"{new_angle}°")
        if self.selected_node_index is not None and self.selected_node_index < len(self.nodes):
            self.nodes[self.selected_node_index]['angle'] = new_angle
            self.redraw_canvas(); self.update_node_list_window_content()

    def toggle_show_distances(self): self.redraw_canvas(); self._update_alignment_data_display()

    def on_canvas_click(self, event):
        canvas_px_x=self.canvas.canvasx(event.x); canvas_px_y=self.canvas.canvasy(event.y)
        curr_ppcm=max(0.01,self.pixels_per_cm.get()); vis_grid_px=max(1,self.visual_grid_size_px.get())
        snap_px_x=(canvas_px_x//vis_grid_px)*vis_grid_px+vis_grid_px//2
        snap_px_y=(canvas_px_y//vis_grid_px)*vis_grid_px+vis_grid_px//2
        node_cm_x=snap_px_x/curr_ppcm; node_cm_y=snap_px_y/curr_ppcm
        if not(0<=node_cm_x<=REAL_WORLD_WIDTH_CM and 0<=node_cm_y<=REAL_WORLD_HEIGHT_CM):
            self.status_var.set("Cannot place outside 6x4ft design area."); return
        if self.selected_tool: self.place_node(node_cm_x,node_cm_y)
        else: self.select_node_at_pixel_position(canvas_px_x,canvas_px_y)

    def place_node(self, cm_x, cm_y):
        if self.selected_tool and self.selected_tool in self.node_images_pil:
            self.node_id_counter+=1
            node_data = {
                'type':self.selected_tool,'cm_x':cm_x,'cm_y':cm_y,
                'angle':int(self.angle_slider_var.get()), 
                'original_pil_image':self.node_images_pil[self.selected_tool],
                'symbol_cm_width':self.current_symbol_width_cm_var.get(),
                'symbol_cm_height':self.current_symbol_height_cm_var.get(),
                'label':f"Node {self.node_id_counter}"}
            self.nodes.append(node_data)
            self.redraw_canvas(); self.update_node_list_window_content(); self._update_alignment_data_display()
            self.status_var.set(f"{self.selected_tool.capitalize()} placed. Nodes: {len(self.nodes)}")
        else: self.status_var.set("No tool or image missing.")

    def select_node_at_pixel_position(self, click_px_x, click_px_y):
        curr_ppcm=max(0.01,self.pixels_per_cm.get()); newly_selected_idx=None
        for i in reversed(range(len(self.nodes))):
            node=self.nodes[i]
            node_px_x=node['cm_x']*curr_ppcm; node_px_y=node['cm_y']*curr_ppcm
            node_sym_px_w=node['symbol_cm_width']*curr_ppcm; node_sym_px_h=node['symbol_cm_height']*curr_ppcm
            if (node_px_x-node_sym_px_w/2<=click_px_x<=node_px_x+node_sym_px_w/2 and
                node_px_y-node_sym_px_h/2<=click_px_y<=node_px_y+node_sym_px_h/2):
                newly_selected_idx=i; break
        self.select_node_by_index(newly_selected_idx, source="canvas")

    def select_node_by_index(self, node_idx, source="unknown"):
        if source=="canvas" and self.selected_node_index==node_idx and node_idx is not None: node_idx=None 
        self.selected_node_index=node_idx
        if node_idx is not None and 0<=node_idx<len(self.nodes):
            node=self.nodes[node_idx]; self.selected_tool=None 
            self.angle_slider_var.set(node['angle'])
            self.current_symbol_width_cm_var.set(node['symbol_cm_width'])
            self.current_symbol_height_cm_var.set(node['symbol_cm_height'])
            self.status_var.set(f"Node {node_idx+1} ('{node.get('label','')}') selected.")
            self.delete_node_button.config(state=tk.NORMAL)
        else: 
            self.selected_node_index=None
            self.status_var.set(f"Selection cleared. Area: {REAL_WORLD_WIDTH_FEET:.1f}ft x {REAL_WORLD_HEIGHT_FEET:.1f}ft")
            self.delete_node_button.config(state=tk.DISABLED)
        self._update_button_styles(); self.redraw_canvas()
        if self.node_list_window and self.node_list_window.winfo_exists():
            self.node_list_window.highlight_selected_node(self.selected_node_index)
        self._update_alignment_data_display()


    def on_canvas_right_click(self, event):
        self.selected_tool=None 
        self.select_node_by_index(None, source="right_click") # This will call _update_alignment_data_display
        self.status_var.set(f"Tool & selection cleared. Area: {REAL_WORLD_WIDTH_FEET:.1f}ft x {REAL_WORLD_HEIGHT_FEET:.1f}ft")

    def draw_distance_lines(self):
        if not self.show_distances_var.get(): return
        self.canvas.delete("distance_line","distance_text","distance_text_bg","calibration_distance","calibration_distance_text","calibration_distance_text_bg") 
        nodes_by_type={}; curr_ppcm=max(0.01,self.pixels_per_cm.get())
        for node_data in self.nodes: nodes_by_type.setdefault(node_data['type'],[]).append(node_data)
        for node_type,nodes_list in nodes_by_type.items():
            if len(nodes_list)<2: continue
            line_color=LINE_COLOR_MAP.get(node_type,"gray")
            for n1,n2 in itertools.combinations(nodes_list,2):
                px1,py1=n1['cm_x']*curr_ppcm,n1['cm_y']*curr_ppcm; px2,py2=n2['cm_x']*curr_ppcm,n2['cm_y']*curr_ppcm
                self.canvas.create_line(px1,py1,px2,py2,fill=line_color,width=1.5,tags="distance_line")
                dist_cm=math.sqrt((n2['cm_x']-n1['cm_x'])**2+(n2['cm_y']-n1['cm_y'])**2)
                txt=f"{dist_cm:.2f}cm"; mid_px,mid_py=(px1+px2)/2,(py1+py2)/2
                tid=self.canvas.create_text(mid_px+5,mid_py-5,text=txt,fill=DISTANCE_TEXT_COLOR,tags="distance_text",anchor=tk.SW)
                bbox=self.canvas.bbox(tid);
                if bbox: self.canvas.create_rectangle(bbox[0]-2,bbox[1]-2,bbox[2]+2,bbox[3]+2,fill="white",outline="white",tags="distance_text_bg"); self.canvas.tag_raise(tid)
        spine_points=[p for p in self.calibration_points if p['label'] in ['spine_start','spine_end']]
        if len(spine_points)==2:
            p1,p2=spine_points[0],spine_points[1]
            px1,py1=p1['cm_x']*curr_ppcm,p1['cm_y']*curr_ppcm; px2,py2=p2['cm_x']*curr_ppcm,p2['cm_y']*curr_ppcm
            self.canvas.create_line(px1,py1,px2,py2,fill=CALIBRATION_SPINE_COLOR,width=1.5,tags="calibration_distance",dash=(2,2))
            dist_cm=math.sqrt((p2['cm_x']-p1['cm_x'])**2+(p2['cm_y']-p1['cm_y'])**2)
            txt=f"Spine: {dist_cm:.2f}cm"; mid_px,mid_py=(px1+px2)/2,(py1+py2)/2
            tid=self.canvas.create_text(mid_px+5,mid_py-15,text=txt,fill=CALIBRATION_SPINE_COLOR,tags="calibration_distance_text",anchor=tk.SW,font=("TkDefaultFont",8))
            bbox=self.canvas.bbox(tid)
            if bbox: self.canvas.create_rectangle(bbox[0]-2,bbox[1]-2,bbox[2]+2,bbox[3]+2,fill="white",outline="white",tags="calibration_distance_text_bg"); self.canvas.tag_raise(tid)

    def redraw_canvas(self):
        self.canvas.delete("all")  
        self.draw_grid()
        curr_ppcm = max(0.01, self.pixels_per_cm.get())

        if self.show_body_symbol_var.get() and self.body_symbol_pil:
            body_obj_px_w = int(BODY_SYMBOL_OBJECT_CM_WIDTH * curr_ppcm)
            body_obj_px_h = int(BODY_SYMBOL_OBJECT_CM_HEIGHT * curr_ppcm)
            body_obj_px_w = max(1, body_obj_px_w); body_obj_px_h = max(1, body_obj_px_h)
            center_world_px_x = (REAL_WORLD_WIDTH_CM * curr_ppcm) / 2
            center_world_px_y = (REAL_WORLD_HEIGHT_CM * curr_ppcm) / 2
            try:
                resized_intrinsic_body_pil = self.body_symbol_pil.resize((body_obj_px_w, body_obj_px_h), Image.Resampling.LANCZOS)
                rotated_display_body_pil = resized_intrinsic_body_pil.rotate(BODY_SYMBOL_DISPLAY_ROTATION, expand=True, resample=Image.Resampling.BICUBIC)
                if self.flip_body_orientation_var.get():
                    rotated_display_body_pil = ImageOps.mirror(rotated_display_body_pil)
                self._body_symbol_tk_ref = ImageTk.PhotoImage(rotated_display_body_pil)
                self.canvas.create_image(center_world_px_x, center_world_px_y, image=self._body_symbol_tk_ref, tags="body_symbol")
            except Exception as e: print(f"Error resizing/drawing body symbol: {e}")

        for cp in self.calibration_points:
            cp_px_x = cp['cm_x']*curr_ppcm; cp_px_y = cp['cm_y']*curr_ppcm
            radius_px = CALIBRATION_POINT_RADIUS_CM*curr_ppcm
            self.canvas.create_oval(cp_px_x-radius_px,cp_px_y-radius_px,cp_px_x+radius_px,cp_px_y+radius_px,fill=cp['color'],outline=cp['color'],tags="calibration_point")
        
        for i,node_data in enumerate(self.nodes):
            original_pil=node_data['original_pil_image']
            target_px_w=max(1,int(node_data['symbol_cm_width']*curr_ppcm))
            target_px_h=max(1,int(node_data['symbol_cm_height']*curr_ppcm))
            resized_pil=original_pil.resize((target_px_w,target_px_h),Image.Resampling.LANCZOS)
            rotated_pil=resized_pil.rotate(-node_data['angle'],expand=False,resample=Image.Resampling.BICUBIC)
            node_data['_image_tk_ref']=ImageTk.PhotoImage(rotated_pil) 
            draw_px_x=node_data['cm_x']*curr_ppcm; draw_px_y=node_data['cm_y']*curr_ppcm
            self.canvas.create_image(draw_px_x,draw_px_y,image=node_data['_image_tk_ref'],tags=(f"node_{i}","node_item"))
            if self.selected_node_index==i:
                sel_x0,sel_y0=draw_px_x-target_px_w//2,draw_px_y-target_px_h//2
                sel_x1,sel_y1=draw_px_x+target_px_w//2,draw_px_y+target_px_h//2
                self.canvas.create_rectangle(sel_x0-3,sel_y0-3,sel_x1+3,sel_y1+3,outline="cyan",width=2,tags="selection_highlight")
        
        if self.show_distances_var.get(): self.draw_distance_lines()
        self._update_alignment_data_display() 

    def clear_canvas_nodes(self):
        self.nodes=[]; self.node_id_counter=0
        self.select_node_by_index(None, source="clear_nodes") 
        self.status_var.set(f"All nodes cleared. Area: {REAL_WORLD_WIDTH_FEET:.1f}ft x {REAL_WORLD_HEIGHT_FEET:.1f}ft")

    def delete_selected_node(self):
        if self.selected_node_index is not None and 0<=self.selected_node_index<len(self.nodes):
            orig_idx_disp=self.selected_node_index+1
            self.nodes.pop(self.selected_node_index)
            self.select_node_by_index(None, source="delete") 
            self.status_var.set(f"Node {orig_idx_disp} deleted. Nodes: {len(self.nodes)}")
        else: self.status_var.set("No node selected to delete.")

    def toggle_node_list_window(self):
        if self.node_list_window and self.node_list_window.winfo_exists():
            self.node_list_window.destroy(); self.node_list_window=None
            self.node_list_button.config(relief=tk.RAISED)
        else:
            self.node_list_window=NodeListWindow(self)
            self.node_list_button.config(relief=tk.SUNKEN)

    def update_node_list_window_content(self):
        if self.node_list_window and self.node_list_window.winfo_exists():
            self.node_list_window.populate_list()
            self.node_list_window.highlight_selected_node(self.selected_node_index)
        self._update_alignment_data_display()


    def update_node_label(self, node_idx, new_label):
        if 0<=node_idx<len(self.nodes):
            self.nodes[node_idx]['label']=new_label
            self.status_var.set(f"Node {node_idx+1} label updated to '{new_label}'.")
            self.update_node_list_window_content() 
        else: print(f"Error: Invalid node index {node_idx} for label update.")

    def _apply_target_spine_length(self):
        if not self.calibration_points:
            messagebox.showinfo("Set Calibration First", "Please set calibration points before adjusting spine length.")
            return
        try:
            new_target_spine_cm = self.target_spine_length_cm_var.get()
            if new_target_spine_cm <= 0:
                messagebox.showerror("Invalid Length", "Target spine length must be positive.")
                self.target_spine_length_cm_var.set(INITIAL_TARGET_SPINE_LENGTH_CM) 
                return

            head_point = next((p for p in self.calibration_points if p['label'] == 'head_center'), None)
            spine_start_point = next((p for p in self.calibration_points if p['label'] == 'spine_start'), None)

            if not head_point or not spine_start_point:
                messagebox.showerror("Error", "Calibration points (head/spine_start) not found. Please reset calibration.")
                self.calibration_points = [] 
                return

            fixed_head_cm_x = head_point['cm_x']
            fixed_head_cm_y = head_point['cm_y']
            fixed_spine_start_cm_x = spine_start_point['cm_x']
            fixed_spine_start_cm_y = spine_start_point['cm_y']

            if not self.flip_body_orientation_var.get(): 
                new_spine_end_cm_x = fixed_spine_start_cm_x + new_target_spine_cm
            else: 
                new_spine_end_cm_x = fixed_spine_start_cm_x - new_target_spine_cm
            
            self.calibration_points = [
                {'label':'head_center', 'cm_x': fixed_head_cm_x, 'cm_y': fixed_head_cm_y, 'color':CALIBRATION_HEAD_COLOR},
                {'label':'spine_start', 'cm_x': fixed_spine_start_cm_x, 'cm_y': fixed_spine_start_cm_y, 'color':CALIBRATION_SPINE_COLOR},
                {'label':'spine_end', 'cm_x': new_spine_end_cm_x, 'cm_y': fixed_spine_start_cm_y, 'color':CALIBRATION_SPINE_COLOR},
            ]
            
            self.redraw_canvas() 
            self.status_var.set(f"Spine length adjusted to {new_target_spine_cm:.1f} cm. Head/Start fixed.")

        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number for spine length.")


    def _recalculate_and_set_calibration_points(self): 
        center_design_x_cm = REAL_WORLD_WIDTH_CM / 2
        center_design_y_cm = REAL_WORLD_HEIGHT_CM / 2
        
        current_target_spine_cm = self.target_spine_length_cm_var.get()
        if current_target_spine_cm <= 0 : current_target_spine_cm = INITIAL_TARGET_SPINE_LENGTH_CM 

        # Displayed body width (after 90deg rotation) is the object's intrinsic height
        displayed_body_visual_width_cm = BODY_SYMBOL_OBJECT_CM_HEIGHT 
        
        if not self.flip_body_orientation_var.get(): # Standard: Head on visual left
            # Spine start is inset from the visual left edge of the body
            cp_spine_start_x = (center_design_x_cm - displayed_body_visual_width_cm / 2) + SPINE_START_INSET_FROM_BODY_VISUAL_EDGE_CM
            # Head is to the "left" (further along negative X from spine_start if spine_start is an anchor)
            cp_head_x = cp_spine_start_x - HEAD_OFFSET_FROM_SPINE_ANCHOR_CM
            # Spine end extends to the "right" from spine_start
            cp_spine_end_x = cp_spine_start_x + current_target_spine_cm
        else: # Flipped: Head on visual right
            # Spine start is inset from the visual right edge of the body
            cp_spine_start_x = (center_design_x_cm + displayed_body_visual_width_cm / 2) - SPINE_START_INSET_FROM_BODY_VISUAL_EDGE_CM
            # Head is to the "right" (further along positive X from spine_start)
            cp_head_x = cp_spine_start_x + HEAD_OFFSET_FROM_SPINE_ANCHOR_CM
            # Spine end extends to the "left" from spine_start
            cp_spine_end_x = cp_spine_start_x - current_target_spine_cm
            
        self.calibration_points = [
            {'label':'head_center', 'cm_x':cp_head_x, 'cm_y':center_design_y_cm, 'color':CALIBRATION_HEAD_COLOR},
            {'label':'spine_start', 'cm_x':cp_spine_start_x, 'cm_y':center_design_y_cm, 'color':CALIBRATION_SPINE_COLOR},
            {'label':'spine_end', 'cm_x':cp_spine_end_x, 'cm_y':center_design_y_cm, 'color':CALIBRATION_SPINE_COLOR},
        ]
        self.status_var.set(f"Calibration points (re)set. Spine: {current_target_spine_cm:.1f}cm. Flipped: {self.flip_body_orientation_var.get()}")
        self._update_alignment_data_display()


    def toggle_calibration_points(self):
        if self.calibration_points:
            self.calibration_points = []
            self.status_var.set("Calibration points cleared.")
        else:
            self._recalculate_and_set_calibration_points() # Initial set based on body edge and target spine length
        self.redraw_canvas() 

    def _handle_orientation_flip_trace(self, *args):
        if self.calibration_points: 
            self._recalculate_and_set_calibration_points() # Re-anchor to the new "front" of the body
        self.redraw_canvas() 
    
    def _update_alignment_data_display(self):
        if not hasattr(self, 'alignment_data_display'): 
            return

        self.alignment_data_display.config(state='normal')
        self.alignment_data_display.delete('1.0', tk.END)
        
        data_str = "--- CALIBRATION POINTS ---\n"
        if self.calibration_points:
            cp_display_order = ['head_center', 'spine_start', 'spine_end']
            cp_dict = {cp['label']: cp for cp in self.calibration_points}
            
            for label in cp_display_order:
                if label in cp_dict:
                    cp = cp_dict[label]
                    data_str += f"- {cp['label'].replace('_',' ').title()}: ({cp['cm_x']:.1f}, {cp['cm_y']:.1f}) cm\n"
            
            spine_points = [cp_dict.get('spine_start'), cp_dict.get('spine_end')]
            if all(spine_points): 
                p1, p2 = spine_points[0], spine_points[1]
                dist_cm = math.sqrt((p2['cm_x']-p1['cm_x'])**2 + (p2['cm_y']-p1['cm_y'])**2)
                data_str += f"  Actual Spine Length: {dist_cm:.2f} cm (Target: {self.target_spine_length_cm_var.get():.1f} cm)\n"
        else:
            data_str += "No calibration points set.\n"
        
        data_str += "\n--- PLACED NODES ---\n"
        if self.nodes:
            for idx, node in enumerate(self.nodes):
                data_str += (f"Node {idx+1} ('{node.get('label', '')}'): {node['type']}\n"
                             f"  Pos: ({node['cm_x']:.1f}, {node['cm_y']:.1f}) cm\n"
                             f"  Size: ({node['symbol_cm_width']:.1f}W x {node['symbol_cm_height']:.1f}H) cm\n"
                             f"  Angle: {node['angle']}°\n\n")
        else:
            data_str += "No nodes placed.\n"
            
        self.alignment_data_display.insert(tk.END, data_str)
        self.alignment_data_display.config(state='disabled')

    def _load_and_update_from_imported_data(self):
        imported_text = self.import_data_text.get("1.0", tk.END).strip()
        if not imported_text:
            messagebox.showinfo("No Data", "Import data text box is empty.")
            return

        self._log_api_status("Attempting to parse and load imported alignment data...")
        
        new_calibration_points = []
        new_nodes = []
        parsed_target_spine_length = None
        
        try:
            lines = imported_text.splitlines()
            parsing_mode = None 
            current_node_data = {}

            for line in lines:
                line = line.strip()
                if not line: 
                    if parsing_mode == "NODES" and current_node_data.get('type'):
                        new_nodes.append(current_node_data)
                        current_node_data = {}
                    continue

                if "--- CALIBRATION POINTS ---" in line:
                    parsing_mode = "CALIBRATION"; continue
                if "--- PLACED NODES ---" in line:
                    parsing_mode = "NODES"
                    if current_node_data.get('type'): new_nodes.append(current_node_data) 
                    current_node_data = {}; continue

                if parsing_mode == "CALIBRATION":
                    cp_match = re.match(r"- (Head Center|Spine Start|Spine End):\s*\(([\d\.-]+),\s*([\d\.-]+)\)\s*cm", line)
                    if cp_match:
                        label_text, x_str, y_str = cp_match.groups()
                        label_map = {"Head Center": "head_center", "Spine Start": "spine_start", "Spine End": "spine_end"}
                        color_map = {"head_center": CALIBRATION_HEAD_COLOR, "spine_start": CALIBRATION_SPINE_COLOR, "spine_end": CALIBRATION_SPINE_COLOR}
                        new_calibration_points.append({
                            'label': label_map[label_text], 
                            'cm_x': float(x_str), 'cm_y': float(y_str), 
                            'color': color_map[label_map[label_text]]
                        })
                    else:
                        ts_match = re.search(r"Target:\s*([\d\.-]+)\s*cm", line)
                        if ts_match and parsed_target_spine_length is None:
                            parsed_target_spine_length = float(ts_match.group(1))
                
                elif parsing_mode == "NODES":
                    if not current_node_data.get('type'): 
                        nh_match = re.match(r"Node \d+ \('([^']*)'\):\s*(\w+)", line)
                        if nh_match:
                            current_node_data['label'] = nh_match.group(1)
                            node_type_str = nh_match.group(2).lower()
                            if node_type_str in self.node_images_pil:
                                current_node_data['type'] = node_type_str
                                current_node_data['original_pil_image'] = self.node_images_pil[node_type_str]
                            else:
                                print(f"Warning: Unknown node type '{node_type_str}' in import. Skipping node.")
                                current_node_data = {} 
                        continue 

                    if current_node_data.get('type'): 
                        pos_match = re.search(r"Pos:\s*\(([\d\.-]+),\s*([\d\.-]+)\)\s*cm", line)
                        if pos_match:
                            current_node_data['cm_x'] = float(pos_match.group(1))
                            current_node_data['cm_y'] = float(pos_match.group(2))
                            continue
                        
                        size_match = re.search(r"Size:\s*\((\d+\.?\d*)W x (\d+\.?\d*)H\)\s*cm", line)
                        if size_match:
                            current_node_data['symbol_cm_width'] = float(size_match.group(1))
                            current_node_data['symbol_cm_height'] = float(size_match.group(2))
                            continue

                        angle_match = re.search(r"Angle:\s*(\d+)", line)
                        if angle_match:
                            current_node_data['angle'] = int(angle_match.group(1))
                            new_nodes.append(current_node_data) 
                            current_node_data = {} 
                            continue
            
            if parsing_mode == "NODES" and current_node_data.get('type'):
                new_nodes.append(current_node_data)

            self.calibration_points = new_calibration_points
            self.nodes = new_nodes
            self.node_id_counter = len(new_nodes) 

            if parsed_target_spine_length is not None:
                self.target_spine_length_cm_var.set(parsed_target_spine_length)
            elif not new_calibration_points: 
                 self.target_spine_length_cm_var.set(INITIAL_TARGET_SPINE_LENGTH_CM)
            
            self.select_node_by_index(None, source="import_data")
            self.redraw_canvas() 
            self.update_node_list_window_content()
            
            messagebox.showinfo("Import Complete", "Alignment data parsed and designer updated.")
            self._log_api_status("Alignment data imported and designer updated.")
            self.import_data_text.delete('1.0', tk.END) 

        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to parse or apply imported data.\nError: {e}\n\nPlease ensure data is in the correct format.")
            self._log_api_status(f"Import data failed: {e}")


# import asyncio 
if __name__ == "__main__":
    root = tk.Tk()
    try:
        style = ttk.Style(root)
        available_themes = style.theme_names()
        if 'clam' in available_themes: style.theme_use('clam')
        elif 'vista' in available_themes: style.theme_use('vista')
    except Exception as e: print(f"Could not set theme: {e}")
    app = EntrainmentDesignerApp(root)
    root.mainloop()
