import tkinter as tk
from tkinter import filedialog, ttk, messagebox
import fitz  # PyMuPDF
import os
import json # For LLM API payload
import asyncio # For running async operations and async sleep
import threading
import re # For parsing LLM graph output and Cypher
import csv # For saving/loading graph data
import uuid # For generating unique IDs if needed

# Attempt to import OpenAI; provide guidance if not found
try:
    from openai import AsyncOpenAI, APIError as OpenAIApiError
except ImportError:
    messagebox.showerror(
        "Missing Dependency",
        "The 'openai' library is not installed. Please install it by running: \n\n"
        "pip install openai\n\n"
        "The OpenAI functionality will not work without it."
    )
    class AsyncOpenAI: # pylint: disable=all
        def __init__(self, *args, **kwargs): pass
        class chat: # pylint: disable=all
            class completions: # pylint: disable=all
                @staticmethod
                async def create(*args, **kwargs):
                    return type('obj', (object,), {
                        'choices': [type('obj', (object,), {
                            'message': type('obj', (object,), {'role': 'assistant', 'content': 'OpenAI library not found.'})
                        })]
                    })()
        class responses: # pylint: disable=all 
             async def create(self, *args, **kwargs):
                return type('obj', (object,), {'output_text': 'OpenAI library not found (responses API).'})()
    class OpenAIApiError(Exception): pass # pylint: disable=all

# Attempt to import Google Generative AI; provide guidance if not found
try:
    import google.generativeai as genai
except ImportError:
    messagebox.showerror(
        "Missing Dependency",
        "The 'google-generativeai' library is not installed. Please install it by running: \n\n"
        "pip install google-generativeai\n\n"
        "The Google Gemini functionality will not work without it."
    )
    class genai: # pylint: disable=all
        @staticmethod
        def configure(*args, **kwargs): pass
        class GenerativeModel:
            def __init__(self, *args, **kwargs): pass
            async def generate_content_async(self, *args, **kwargs):
                if isinstance(kwargs.get('contents', ''), list): 
                     return type('obj', (object,), {'text': 'Google Generative AI library not found (chat).'})
                return type('obj', (object,), {'text': 'Google Generative AI library not found.'})()
        class types:
            @staticmethod
            def Content(parts=None, role=None): return {"parts": parts or [], "role": role or "user"}
            @staticmethod
            def Part(text=None): return {"text": text or ""}

# Attempt to import ReportLab for PDF export
try:
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# Attempt to import NetworkX and Matplotlib for graph visualization
try:
    import networkx as nx
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    GRAPH_LIBS_AVAILABLE = True
except ImportError:
    GRAPH_LIBS_AVAILABLE = False
    # Messagebox shown in __init__ if libs are needed and not found.


# --- Theme Definitions ---
THEMES = {
    "Default": {
        "root_bg": "SystemButtonFace", 
        "text_fg": "black",
        "text_bg": "white",
        "text_insert_bg": "black",
        "listbox_bg": "white",
        "listbox_fg": "black",
        "listbox_select_bg": "#0078D7", 
        "listbox_select_fg": "white",
        "canvas_bg": "lightgrey", 
        "graph_canvas_bg": "white", 
        "ttk_theme": "clam", 
        "TFrame.background": "SystemButtonFace",
        "TLabel.foreground": "black",
        "TLabel.background": "SystemButtonFace",
        "TButton.foreground": "black",
        "TButton.background": "SystemButtonFace", 
        "TCheckbutton.foreground": "black",
        "TCheckbutton.background": "SystemButtonFace",
        "TCombobox.fieldbackground": "white",
        "TCombobox.foreground": "black",
        "TEntry.fieldbackground": "white",
        "TEntry.foreground": "black",
        "TNotebook.background": "SystemButtonFace",
        "TNotebook.Tab.foreground": "black",
        "TNotebook.Tab.background": "SystemButtonFace", 
        "TNotebook.Tab.selectedbackground": "#DDEEFF",
        "TScrollbar.background": "#F0F0F0", 
        "TScrollbar.troughcolor": "#E1E1E1", 
        "TScrollbar.bordercolor": "#C0C0C0",
        "TScrollbar.arrowcolor": "black",
        "Toolbar.background": "SystemButtonFace", # For Matplotlib toolbar
    },
    "Matrix": {
        "root_bg": "black",
        "text_fg": "#33FF33", 
        "text_bg": "#0A0A0A", 
        "text_insert_bg": "#33FF33", 
        "listbox_bg": "#050505",
        "listbox_fg": "#33FF33",
        "listbox_select_bg": "#005500", 
        "listbox_select_fg": "#CCFFCC", 
        "canvas_bg": "black", 
        "graph_canvas_bg": "#050505", 
        "ttk_theme": "clam", 
        "TFrame.background": "black",
        "TLabel.foreground": "#33FF33",
        "TLabel.background": "black",
        "TButton.foreground": "#33FF33",
        "TButton.background": "#002200", 
        "TCheckbutton.foreground": "#33FF33",
        "TCheckbutton.background": "black",
        "TCheckbutton.indicatorcolor": "#0A0A0A", 
        "TCheckbutton.selectcolor": "#33FF33", 
        "TCombobox.fieldbackground": "#0A0A0A",
        "TCombobox.foreground": "#33FF33",
        "TCombobox.selectbackground": "#005500", 
        "TCombobox.arrowcolor": "#33FF33",
        "TEntry.fieldbackground": "#0A0A0A",
        "TEntry.foreground": "#33FF33",
        "TNotebook.background": "black",
        "TNotebook.Tab.foreground": "#33FF33",
        "TNotebook.Tab.background": "#001100", 
        "TNotebook.Tab.selectedbackground": "#003300", 
        "TScrollbar.background": "#002200", 
        "TScrollbar.troughcolor": "#0A0A0A", 
        "TScrollbar.bordercolor": "black",
        "TScrollbar.arrowcolor": "#33FF33", 
        "Toolbar.background": "black", # For Matplotlib toolbar
    }
}

# --- LLM Integration ---
async def process_llm_request(api_key, messages_or_prompt, selected_llm, is_chat_completion=False, progress_callback=None): # pylint: disable=unused-argument
    if progress_callback:
        progress_callback(f"Processing LLM request with {selected_llm}...\n")

    if selected_llm == "default-OpenAI":
        if not api_key:
            if progress_callback: progress_callback("Error: OpenAI API Key is required.\n")
            return "Error: OpenAI API Key is missing."
        try:
            if progress_callback: progress_callback("Initializing AsyncOpenAI client...\n")
            async_client = AsyncOpenAI(api_key=api_key)
            
            # Ensure messages_or_prompt is a list for chat.completions.create
            if not isinstance(messages_or_prompt, list):
                messages_for_api = [{"role": "user", "content": str(messages_or_prompt)}] # Ensure content is string
            else:
                messages_for_api = messages_or_prompt

            if progress_callback: progress_callback(f"Sending request to OpenAI (model: gpt-4.1-turbo). Messages: {len(messages_for_api)}\n")
            response = await async_client.chat.completions.create(model="gpt-4.1-turbo", messages=messages_for_api)
            llm_response_text = response.choices[0].message.content
            
            if progress_callback: progress_callback("OpenAI request successful.\n")
            return llm_response_text
        except OpenAIApiError as e:
            error_message = f"OpenAI API Error: {e}\n"
            if hasattr(e, 'status_code'): error_message += f"Status Code: {e.status_code}\n"
            if hasattr(e, 'response') and e.response:
                try: error_message += f"Details: {json.dumps(e.response.json(), indent=2)}\n"
                except json.JSONDecodeError: error_message += f"Details (raw): {e.response.text}\n"
            if progress_callback: progress_callback(error_message)
            return error_message
        except Exception as e:
            error_message = f"An unexpected error occurred with OpenAI: {e}\n"
            if progress_callback: progress_callback(error_message)
            return error_message

    elif selected_llm == "Google Gemini":
        if not api_key:
            if progress_callback: progress_callback("Error: Google API Key is required for Gemini.\n")
            return "Error: Google API Key is missing for Gemini."
        try:
            if progress_callback: progress_callback("Configuring Google Generative AI API...\n")
            genai.configure(api_key=api_key)
            model_name = "gemini-1.5-flash-latest" 
            model = genai.GenerativeModel(model_name)
            
            # Convert OpenAI-formatted history (messages_or_prompt) to Gemini's format
            if isinstance(messages_or_prompt, list) and all(isinstance(m, dict) and "role" in m and "content" in m for m in messages_or_prompt):
                gemini_contents = []
                for msg in messages_or_prompt:
                    # Gemini uses 'model' for assistant responses
                    role = "user" if msg["role"] == "user" else "model" 
                    
                    # Handle system prompts: Prepend to the next user message or treat as a separate user turn if it's the first/only one.
                    if msg["role"] == "system":
                        # If there's a subsequent user message, prepend system prompt to it.
                        # This is a basic way; more complex logic might be needed for multiple system prompts or different orderings.
                        current_content = str(msg.get("content", "")) # Ensure content is string
                        
                        # Find if next message is user to prepend
                        msg_idx = messages_or_prompt.index(msg)
                        if msg_idx + 1 < len(messages_or_prompt) and messages_or_prompt[msg_idx+1]["role"] == "user":
                            # This modification of messages_or_prompt here might be tricky if it's iterated over again.
                            # A safer way is to build a new list for Gemini.
                            # For now, let's assume simple system prompt at the beginning.
                             pass # System prompt will be handled by adding it as a user turn if no user message follows
                        
                        # If system prompt is first, or not followed by user, treat as a user turn for Gemini
                        # Or, if it's the only message.
                        is_first_message = not gemini_contents
                        is_last_system_message_in_sequence = True
                        if msg_idx + 1 < len(messages_or_prompt):
                            if messages_or_prompt[msg_idx+1]["role"] != "user":
                                is_last_system_message_in_sequence = True
                            else: # Next is user, system prompt should be prepended by OpenAI logic or handled by Gemini if it supports system role
                                is_last_system_message_in_sequence = False


                        if is_first_message or is_last_system_message_in_sequence :
                             gemini_contents.append({"role": "user", "parts": [{"text": current_content}]})
                        # If it's to be prepended, the OpenAI logic for messages_for_api should handle it,
                        # or Gemini API itself might handle system role if supported directly.
                        # For now, we assume system prompts are best converted to user prompts for Gemini if they stand alone.
                        continue # Skip adding this system message as its own turn after processing

                    gemini_contents.append({"role": role, "parts": [{"text": str(msg.get("content",""))}]}) # Ensure content is string
                contents_for_api = gemini_contents
            else: # Assume it's a single string prompt
                contents_for_api = str(messages_or_prompt) # Ensure it's a string

            if progress_callback:
                log_message = f"Sending request to Google Gemini (model: {model_name}). "
                if isinstance(contents_for_api, list): log_message += f"Messages: {len(contents_for_api)}"
                else: log_message += f"Prompt length: {len(contents_for_api)} chars."
                progress_callback(log_message + "\n")

            response = await model.generate_content_async(contents=contents_for_api)
            llm_response_text = response.text if hasattr(response, 'text') and response.text else "Gemini returned an empty response."
            if progress_callback: progress_callback("Google Gemini request successful.\n")
            return llm_response_text
        except AttributeError as e: 
            if "dummy" in str(e).lower() or "GenerativeModel" in str(e):
                 error_message = "Google Generative AI library not found or not properly installed.\nPlease ensure 'pip install google-generativeai' was successful."
            else:
                error_message = f"Attribute error with Google Gemini: {e}\nLikely an issue with the library or response structure."
            if progress_callback: progress_callback(error_message + "\n")
            return error_message
        except Exception as e:
            error_message = f"An unexpected error occurred with Google Gemini: {e}\n"
            if progress_callback: progress_callback(error_message)
            return error_message
    else:
        if progress_callback: progress_callback(f"Error: LLM '{selected_llm}' is not implemented.\n")
        return f"Error: LLM '{selected_llm}' is not supported/implemented."

class PDFAnalyzerApp:
    def __init__(self, root_window):
        self.root = root_window
        self.root.title("PDF Viewer & LLM Analyzer")
        self.root.geometry("1100x850") 

        self.style = ttk.Style()

        self.pdf_folder_path = tk.StringVar() 
        self.actual_pdf_folder_path = None    
        self.pdf_files = []
        self.current_pdf_document = None
        self.current_pdf_page_num = 0
        self.pdf_page_image = None 
        self.current_zoom_factor = 1.0
        self.current_pdf_text_for_chat = "" 
        self.llm_chat_history = [] # Standardized to OpenAI format: [{"role": ..., "content": ...}]
        self.current_graph_data_structure = {"nodes": [], "relationships": []} 
        
        self.current_theme = tk.StringVar(value="Default")
        self.current_theme.trace_add("write", self.on_theme_change)
        self.show_generated_graph_data = tk.BooleanVar(value=True) 
        self.show_generated_graph_data.trace_add("write", self.toggle_generated_graph_data_visibility)


        self.setup_menubar() 

        self.notebook = ttk.Notebook(self.root, style='App.TNotebook') 
        
        self.pdf_viewer_tab = ttk.Frame(self.notebook, style='App.TFrame')
        self.folder_frame = ttk.Frame(self.pdf_viewer_tab, style='App.TFrame')
        self.browse_folder_button = ttk.Button(self.folder_frame, text="Browse Research Folder", command=self.browse_folder, style='App.TButton')
        self.pdf_path_entry = ttk.Entry(self.folder_frame, textvariable=self.pdf_folder_path, width=60, state='readonly', style='App.TEntry')
        self.content_frame_pdf = ttk.Frame(self.pdf_viewer_tab, style='App.TFrame')
        self.paned_window_pdf = ttk.PanedWindow(self.content_frame_pdf, orient=tk.HORIZONTAL) 
        self.list_frame_pdf = ttk.Frame(self.paned_window_pdf, style='App.TFrame')
        self.pdf_files_label = ttk.Label(self.list_frame_pdf, text="PDF Files:", style='App.TLabel')
        self.pdf_listbox = tk.Listbox(self.list_frame_pdf, exportselection=False, selectmode=tk.EXTENDED) 
        self.viewer_frame_pdf = ttk.Frame(self.paned_window_pdf, style='App.TFrame')
        self.pdf_canvas = tk.Canvas(self.viewer_frame_pdf, relief=tk.SUNKEN, borderwidth=1) 
        self.nav_frame_pdf = ttk.Frame(self.viewer_frame_pdf, style='App.TFrame')
        self.prev_page_button = ttk.Button(self.nav_frame_pdf, text="<< Previous", command=self.prev_page, state=tk.DISABLED, style='App.TButton')
        self.page_label = ttk.Label(self.nav_frame_pdf, text="Page: -/-", style='App.TLabel')
        self.next_page_button = ttk.Button(self.nav_frame_pdf, text="Next >>", command=self.next_page, state=tk.DISABLED, style='App.TButton')
        self.zoom_in_button = ttk.Button(self.nav_frame_pdf, text="Zoom +", command=lambda: self.zoom(1.1), style='App.TButton')
        self.zoom_out_button = ttk.Button(self.nav_frame_pdf, text="Zoom -", command=lambda: self.zoom(0.9), style='App.TButton')
        
        self.notebook.add(self.pdf_viewer_tab, text='PDF Viewer')
        self.setup_pdf_viewer_tab()

        self.llm_analyzer_tab = ttk.Frame(self.notebook, style='App.TFrame')
        self.main_config_frame_llm = ttk.Frame(self.llm_analyzer_tab, style='App.TFrame')
        self.llm_api_key_frame_llm = ttk.Frame(self.main_config_frame_llm, style='App.TFrame')
        self.select_llm_label = ttk.Label(self.llm_api_key_frame_llm, text="Select LLM:", style='App.TLabel')
        self.llm_selection_combo = ttk.Combobox(self.llm_api_key_frame_llm, state="readonly", width=18, style='App.TCombobox')
        self.api_key_label = ttk.Label(self.llm_api_key_frame_llm, text="API Key:", style='App.TLabel')
        self.llm_api_key_entry = ttk.Entry(self.llm_api_key_frame_llm, width=30, style='App.TEntry', show="*") 
        self.pdf_action_frame_llm = ttk.Frame(self.main_config_frame_llm, style='App.TFrame')
        self.pdf_for_summary_label = ttk.Label(self.pdf_action_frame_llm, text="PDF for Analysis:", style='App.TLabel') 
        self.llm_pdf_combobox = ttk.Combobox(self.pdf_action_frame_llm, state="readonly", width=30, style='App.TCombobox') 
        self.summarize_button = ttk.Button(self.pdf_action_frame_llm, text="Summarize PDF", command=self.summarize_selected_pdf, style='App.TButton')
        self.create_graph_node_button = ttk.Button(self.pdf_action_frame_llm, text="Create Graph Data", command=self.create_graph_data_from_pdf, style='App.TButton') 

        self.progress_frame_llm = ttk.Frame(self.llm_analyzer_tab, style='App.TFrame')
        self.llm_op_log_label = ttk.Label(self.progress_frame_llm, text="LLM Operation Log:", style='App.TLabel')
        self.llm_progress_text = tk.Text(self.progress_frame_llm, height=3, width=80, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1) 
        self.llm_progress_text_scrollbar = ttk.Scrollbar(self.progress_frame_llm, orient='vertical', command=self.llm_progress_text.yview, style='App.Vertical.TScrollbar')
        self.llm_progress_text['yscrollcommand'] = self.llm_progress_text_scrollbar.set
        self.summary_outer_frame_llm = ttk.Frame(self.llm_analyzer_tab, style='App.TFrame')
        self.pdf_summary_label = ttk.Label(self.summary_outer_frame_llm, text="PDF Summary:", style='App.TLabel')
        self.summary_display_area = tk.Text(self.summary_outer_frame_llm, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1, state=tk.DISABLED, height=7) 
        self.summary_display_scrollbar = ttk.Scrollbar(self.summary_outer_frame_llm, orient='vertical', command=self.summary_display_area.yview, style='App.Vertical.TScrollbar')
        self.summary_display_area['yscrollcommand'] = self.summary_display_scrollbar.set
        self.chat_display_outer_frame_llm = ttk.Frame(self.llm_analyzer_tab, style='App.TFrame')
        self.chat_with_llm_label = ttk.Label(self.chat_display_outer_frame_llm, text="Chat with LLM about PDF:", style='App.TLabel')
        self.chat_conversation_area = tk.Text(self.chat_display_outer_frame_llm, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1, state=tk.DISABLED, height=8) 
        self.chat_conversation_scrollbar = ttk.Scrollbar(self.chat_display_outer_frame_llm, orient='vertical', command=self.chat_conversation_area.yview, style='App.Vertical.TScrollbar')
        self.chat_conversation_area['yscrollcommand'] = self.chat_conversation_scrollbar.set
        self.export_button_frame_llm = ttk.Frame(self.llm_analyzer_tab, style='App.TFrame')
        self.export_chat_button = ttk.Button(self.export_button_frame_llm, text="Export Chat to PDF", command=self.export_chat_to_pdf, style='App.TButton')
        self.chat_input_frame_llm = ttk.Frame(self.llm_analyzer_tab, style='App.TFrame')
        self.chat_input_entry = ttk.Entry(self.chat_input_frame_llm, width=70, style='App.TEntry')
        self.send_chat_button = ttk.Button(self.chat_input_frame_llm, text="Send", command=self.handle_chat_submission, style='App.TButton')
        
        self.notebook.add(self.llm_analyzer_tab, text='LLM Analyzer & Chat')
        self.setup_llm_analyzer_tab()

        self.graph_db_tab = ttk.Frame(self.notebook, style='App.TFrame')
        self.graph_header_frame = ttk.Frame(self.graph_db_tab, style='App.TFrame')
        self.graph_data_label = ttk.Label(self.graph_header_frame, text="LLM Generated Graph Data:", style='App.TLabel') 
        self.toggle_graph_data_checkbox = ttk.Checkbutton(
            self.graph_header_frame, text="Show/Hide", variable=self.show_generated_graph_data, 
            onvalue=True, offvalue=False, style='App.TCheckbutton'
        )
        self.generated_graph_data_frame = ttk.Frame(self.graph_db_tab, style='App.TFrame') 
        self.graph_data_text_area = tk.Text(self.generated_graph_data_frame, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1, state=tk.DISABLED, height=10) 
        self.graph_data_text_scrollbar = ttk.Scrollbar(self.generated_graph_data_frame, orient='vertical', command=self.graph_data_text_area.yview, style='App.Vertical.TScrollbar')
        self.graph_data_text_area['yscrollcommand'] = self.graph_data_text_scrollbar.set
        
        self.custom_cypher_frame = ttk.Frame(self.graph_db_tab, style='App.TFrame')
        self.custom_cypher_label = ttk.Label(self.custom_cypher_frame, text="Custom Cypher Query:", style='App.TLabel')
        self.custom_cypher_text_area_frame = ttk.Frame(self.custom_cypher_frame, style='App.TFrame') 
        self.custom_cypher_text_area = tk.Text(self.custom_cypher_text_area_frame, wrap=tk.WORD, relief=tk.SUNKEN, borderwidth=1, height=5) 
        self.custom_cypher_text_scrollbar = ttk.Scrollbar(self.custom_cypher_text_area_frame, orient='vertical', command=self.custom_cypher_text_area.yview, style='App.Vertical.TScrollbar')
        self.custom_cypher_text_area['yscrollcommand'] = self.custom_cypher_text_scrollbar.set
        self.run_cypher_button = ttk.Button(self.custom_cypher_frame, text="Run Custom Cypher", command=self.run_custom_cypher, style='App.TButton') 
        
        self.graph_db_io_frame = ttk.Frame(self.graph_db_tab, style='App.TFrame') 
        self.save_graph_csv_button = ttk.Button(self.graph_db_io_frame, text="Save Graph to CSV", command=self.save_graph_to_csv, style='App.TButton')
        self.load_graph_csv_button = ttk.Button(self.graph_db_io_frame, text="Load Graph from CSV", command=self.load_graph_from_csv, style='App.TButton')

        self.notebook.add(self.graph_db_tab, text='Graph Database')
        self.setup_graph_database_tab()

        self.graph_viz_tab = ttk.Frame(self.notebook, style='App.TFrame')
        self.graph_viz_controls_frame = ttk.Frame(self.graph_viz_tab, style='App.TFrame') 
        self.visualize_graph_button = ttk.Button(self.graph_viz_controls_frame, text="Visualize Graph", command=self.visualize_current_graph, style='App.TButton')
        self.reset_graph_button = ttk.Button(self.graph_viz_controls_frame, text="Reset Graph Data & View", command=self.reset_graph_data_and_visualization, style='App.TButton')
        self.graph_viz_canvas_frame = ttk.Frame(self.graph_viz_tab, style='App.TFrame') 
        self.mpl_canvas = None 
        self.mpl_toolbar = None 

        self.notebook.add(self.graph_viz_tab, text='Graph Visualization')
        self.setup_graph_visualization_tab()
        
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        self.apply_theme() 

    def setup_menubar(self):
        menubar = tk.Menu(self.root)
        theme_menu = tk.Menu(menubar, tearoff=0)
        theme_menu.add_radiobutton(label="Default", variable=self.current_theme, value="Default")
        theme_menu.add_radiobutton(label="Matrix", variable=self.current_theme, value="Matrix")
        menubar.add_cascade(label="Themes", menu=theme_menu)
        self.root.config(menu=menubar)

    def on_theme_change(self, *args): # pylint: disable=unused-argument
        self.apply_theme()
        if GRAPH_LIBS_AVAILABLE and self.mpl_canvas: 
            self.visualize_current_graph(force_redraw=True)


    def apply_theme(self):
        theme_name = self.current_theme.get()
        theme_settings = THEMES.get(theme_name, THEMES["Default"])

        self.style.theme_use(theme_settings["ttk_theme"])
        self.root.configure(bg=theme_settings["root_bg"])

        self.style.configure('App.TFrame', background=theme_settings.get("TFrame.background", theme_settings["root_bg"]))
        self.style.configure('App.TLabel', 
                             foreground=theme_settings.get("TLabel.foreground", theme_settings["text_fg"]), 
                             background=theme_settings.get("TLabel.background", theme_settings["root_bg"]))
        self.style.configure('App.TButton', 
                             foreground=theme_settings.get("TButton.foreground", theme_settings["text_fg"]), 
                             background=theme_settings.get("TButton.background", theme_settings["root_bg"]))
        self.style.configure('App.TCheckbutton', 
                             foreground=theme_settings.get("TCheckbutton.foreground", theme_settings["text_fg"]),
                             background=theme_settings.get("TCheckbutton.background", theme_settings["root_bg"]),
                             indicatorcolor=theme_settings.get("TCheckbutton.indicatorcolor", theme_settings["text_bg"])) 
        self.style.map('App.TCheckbutton', 
                       selectcolor=[('!disabled', theme_settings.get("TCheckbutton.selectcolor", theme_settings["text_fg"]))]) 

        self.style.configure('App.TCombobox', 
                             fieldbackground=theme_settings.get("TCombobox.fieldbackground", theme_settings["text_bg"]),
                             foreground=theme_settings.get("TCombobox.foreground", theme_settings["text_fg"]),
                             selectbackground=theme_settings.get("TCombobox.selectbackground", theme_settings["listbox_select_bg"]),
                             arrowcolor=theme_settings.get("TCombobox.arrowcolor", theme_settings["text_fg"]))
        self.root.option_add('*TCombobox*Listbox.background', theme_settings.get("TCombobox.fieldbackground", theme_settings["text_bg"]))
        self.root.option_add('*TCombobox*Listbox.foreground', theme_settings.get("TCombobox.foreground", theme_settings["text_fg"]))
        self.root.option_add('*TCombobox*Listbox.selectBackground', theme_settings.get("TCombobox.selectbackground", theme_settings["listbox_select_bg"]))
        self.root.option_add('*TCombobox*Listbox.selectForeground', theme_settings.get("listbox_select_fg", "white"))
        self.style.configure('App.TEntry', 
                             fieldbackground=theme_settings.get("TEntry.fieldbackground", theme_settings["text_bg"]), 
                             foreground=theme_settings.get("TEntry.foreground", theme_settings["text_fg"]),
                             insertcolor=theme_settings.get("text_insert_bg", theme_settings["text_fg"])) 
        self.style.configure('App.TNotebook', background=theme_settings.get("TNotebook.background", theme_settings["root_bg"]))
        self.style.configure('App.TNotebook.Tab', 
                             foreground=theme_settings.get("TNotebook.Tab.foreground", theme_settings["text_fg"]),
                             background=theme_settings.get("TNotebook.Tab.background", theme_settings["root_bg"]))
        self.style.map('App.TNotebook.Tab', 
                       background=[('selected', theme_settings.get("TNotebook.Tab.selectedbackground", theme_settings["listbox_select_bg"]))])
        self.style.configure('App.Vertical.TScrollbar',
                             background=theme_settings.get("TScrollbar.background"),
                             troughcolor=theme_settings.get("TScrollbar.troughcolor"),
                             bordercolor=theme_settings.get("TScrollbar.bordercolor"),
                             arrowcolor=theme_settings.get("TScrollbar.arrowcolor"))
        self.style.configure('App.Horizontal.TScrollbar', 
                             background=theme_settings.get("TScrollbar.background"),
                             troughcolor=theme_settings.get("TScrollbar.troughcolor"),
                             bordercolor=theme_settings.get("TScrollbar.bordercolor"),
                             arrowcolor=theme_settings.get("TScrollbar.arrowcolor"))
        self.style.configure('Toolbar', background=theme_settings.get("Toolbar.background", theme_settings["root_bg"]))


        self.pdf_listbox.config(bg=theme_settings["listbox_bg"], fg=theme_settings["listbox_fg"],
                                selectbackground=theme_settings["listbox_select_bg"], selectforeground=theme_settings["listbox_select_fg"])
        self.pdf_canvas.config(bg=theme_settings["canvas_bg"])
        
        text_widgets_to_theme = [self.llm_progress_text, self.summary_display_area, self.chat_conversation_area, self.graph_data_text_area, self.custom_cypher_text_area]
        for widget in text_widgets_to_theme:
            if hasattr(widget, 'config'): 
                widget.config(bg=theme_settings["text_bg"], fg=theme_settings["text_fg"], 
                              insertbackground=theme_settings["text_insert_bg"])
        
        if hasattr(self, 'graph_viz_canvas_frame') and self.graph_viz_canvas_frame.winfo_exists():
            self.graph_viz_canvas_frame.configure(style='App.TFrame') 
            if self.mpl_canvas:
                self.mpl_canvas.get_tk_widget().configure(bg=theme_settings["graph_canvas_bg"])
                self.mpl_canvas.figure.set_facecolor(theme_settings["graph_canvas_bg"])
            if self.mpl_toolbar: 
                self.mpl_toolbar.config(background=theme_settings.get("Toolbar.background", theme_settings["root_bg"]))
                for child in self.mpl_toolbar.winfo_children():
                    if isinstance(child, (ttk.Button, tk.Button)):
                        try: child.configure(style='App.TButton') 
                        except tk.TclError: 
                            child.configure(bg=theme_settings.get("TButton.background", theme_settings["root_bg"]), 
                                            fg=theme_settings.get("TButton.foreground", theme_settings["text_fg"]))


    def setup_pdf_viewer_tab(self):
        self.folder_frame.pack(fill='x', pady=5)
        self.browse_folder_button.pack(side=tk.LEFT, padx=5)
        self.pdf_path_entry.pack(side=tk.LEFT, expand=True, fill='x', padx=5)
        self.content_frame_pdf.pack(expand=True, fill='both', pady=5)
        self.paned_window_pdf.pack(expand=True, fill='both')
        self.paned_window_pdf.add(self.list_frame_pdf, weight=1) 
        self.pdf_files_label.pack(anchor='w')
        self.pdf_listbox.pack(expand=True, fill='both', pady=5)
        self.pdf_listbox.bind('<<ListboxSelect>>', self.on_pdf_select)
        self.paned_window_pdf.add(self.viewer_frame_pdf, weight=3) 
        self.pdf_canvas.pack(expand=True, fill='both', pady=5)
        self.pdf_canvas.bind("<Configure>", self.on_canvas_resize)
        self.nav_frame_pdf.pack(fill='x', pady=5)
        self.prev_page_button.pack(side=tk.LEFT, padx=5)
        self.page_label.pack(side=tk.LEFT, padx=10)
        self.next_page_button.pack(side=tk.LEFT, padx=5)
        self.zoom_in_button.pack(side=tk.LEFT, padx=5)
        self.zoom_out_button.pack(side=tk.LEFT, padx=5)

    def setup_llm_analyzer_tab(self):
        self.main_config_frame_llm.pack(fill='x', pady=(0, 10))
        self.llm_api_key_frame_llm.pack(fill='x', pady=(0, 5))
        self.select_llm_label.pack(side=tk.LEFT, padx=(0,5))
        self.llm_selection_combo['values'] = ["default-OpenAI", "Google Gemini"] 
        self.llm_selection_combo.current(0) 
        self.llm_selection_combo.pack(side=tk.LEFT, padx=(0,10))
        self.api_key_label.pack(side=tk.LEFT, padx=(0,5))
        self.llm_api_key_entry.pack(side=tk.LEFT, expand=True, fill='x', padx=(0,5))
        
        self.pdf_action_frame_llm.pack(fill='x', pady=(5,0)) 
        self.pdf_for_summary_label.pack(side=tk.LEFT, padx=(0,5))
        self.llm_pdf_combobox.pack(side=tk.LEFT, expand=True, fill='x', padx=(0,10))
        self.summarize_button.pack(side=tk.LEFT, padx=(0,5)) 
        self.create_graph_node_button.pack(side=tk.LEFT, padx=5) 

        self.progress_frame_llm.pack(fill='x', pady=5)
        self.llm_op_log_label.pack(anchor='w')
        self.llm_progress_text.pack(side=tk.LEFT, expand=True, fill='x', pady=2) 
        self.llm_progress_text_scrollbar.pack(side=tk.RIGHT, fill='y') 
        
        self.summary_outer_frame_llm.pack(fill='x', pady=5) 
        self.pdf_summary_label.pack(anchor='w')
        self.summary_display_area.pack(side=tk.LEFT, expand=True, fill='x', pady=(2,0)) 
        self.summary_display_scrollbar.pack(side=tk.RIGHT, fill='y') 
        
        self.chat_display_outer_frame_llm.pack(expand=True, fill='both', pady=5) 
        self.chat_with_llm_label.pack(anchor='w')
        self.chat_conversation_area.pack(side=tk.LEFT, expand=True, fill='both', pady=(2,0)) 
        self.chat_conversation_scrollbar.pack(side=tk.RIGHT, fill='y') 
        
        self.export_button_frame_llm.pack(fill='x', pady=(0,5)) 
        self.export_chat_button.pack(side=tk.RIGHT, padx=5) 
        
        self.chat_input_frame_llm.pack(fill='x', pady=(0,0)) 
        self.chat_input_entry.pack(side=tk.LEFT, expand=True, fill='x', padx=(0,5))
        self.chat_input_entry.bind("<Return>", self.handle_chat_submission_event)
        self.send_chat_button.pack(side=tk.LEFT)

    def setup_graph_database_tab(self):
        self.graph_header_frame.pack(fill='x', pady=(5,0))
        self.graph_data_label.pack(side=tk.LEFT, padx=5, pady=(0,2))
        self.toggle_graph_data_checkbox.pack(side=tk.LEFT, padx=5, pady=(0,2))

        self.graph_data_text_area.pack(side=tk.LEFT, expand=True, fill='both') 
        self.graph_data_text_scrollbar.pack(side=tk.RIGHT, fill='y')
        
        self.custom_cypher_frame.pack(fill='x', pady=5, expand=False) 
        self.custom_cypher_label.pack(anchor='w', padx=5, pady=(5,2))
        
        self.custom_cypher_text_area_frame.pack(fill='x', expand=True, pady=(0,5))
        self.custom_cypher_text_area.pack(side=tk.LEFT, expand=True, fill='both')
        self.custom_cypher_text_scrollbar.pack(side=tk.RIGHT, fill='y')
        
        self.run_cypher_button.pack(anchor='e', padx=5, pady=(0,5))

        self.graph_db_io_frame.pack(fill='x', pady=5)
        self.save_graph_csv_button.pack(side=tk.LEFT, padx=5)
        self.load_graph_csv_button.pack(side=tk.LEFT, padx=5)

        self.toggle_generated_graph_data_visibility() 
    
    def setup_graph_visualization_tab(self):
        self.graph_viz_controls_frame.pack(fill='x', pady=(5,0))
        self.visualize_graph_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.reset_graph_button.pack(side=tk.LEFT, padx=5, pady=5)
        self.graph_viz_canvas_frame.pack(expand=True, fill='both', padx=5, pady=(0,5))
    
    def toggle_generated_graph_data_visibility(self, *args): # pylint: disable=unused-argument
        if self.show_generated_graph_data.get():
            if self.custom_cypher_frame.winfo_manager(): 
                 self.generated_graph_data_frame.pack(fill='x', pady=(0,5), before=self.custom_cypher_frame)
            else: 
                 self.generated_graph_data_frame.pack(fill='x', pady=(0,5))
        else:
            self.generated_graph_data_frame.pack_forget()

    def run_custom_cypher(self): # Renamed from placeholder
        cypher_query_text = self.custom_cypher_text_area.get("1.0", tk.END).strip()
        if not cypher_query_text:
            messagebox.showinfo("No Query", "Please enter a Cypher query to run.")
            return
        
        self.add_log_message(f"Attempting to parse and apply Cypher:\n{cypher_query_text[:200]}...\n")
        
        # Reset graph structure before applying new Cypher from custom input
        # Or, decide if it should be additive. For now, let's make it overwrite for simplicity from custom input.
        # If called from LLM generation, create_graph_data_async_wrapper already resets.
        # self.current_graph_data_structure = {"nodes": [], "relationships": []} # Optional: uncomment to make "Run Custom Cypher" always overwrite

        statements = [s.strip() for s in cypher_query_text.split(';') if s.strip()]
        
        node_pattern = re.compile(r"^(CREATE|MERGE)\s*\(([\w\d]*):?([\w\d_]+)?\s*(\{.*?\})\)", re.IGNORECASE)
        rel_pattern = re.compile(r"^(CREATE|MERGE)\s*\(([\w\d]+)\)\s*-\s*\[([\w\d]*):?([\w\d_]+)?\]\s*->\s*\(([\w\d]+)\)", re.IGNORECASE)

        node_vars_map = {} 

        for stmt in statements:
            node_match = node_pattern.match(stmt)
            rel_match = rel_pattern.match(stmt)

            if node_match:
                op_type = node_match.group(1).upper()
                node_var = node_match.group(2) if node_match.group(2) else None
                label = node_match.group(3) if node_match.group(3) else "Unknown"
                props_str = node_match.group(4)
                
                try:
                    attributes = {}
                    prop_matches = re.findall(r'([\w\d_]+)\s*:\s*(".*?"|\'.*?\'|[\w\d\.-]+|true|false)', props_str.strip("{}"))
                    for key, value in prop_matches:
                        value = value.strip()
                        if (value.startswith('"') and value.endswith('"')) or \
                           (value.startswith("'") and value.endswith("'")):
                            attributes[key] = value[1:-1] 
                        elif value.lower() == 'true':
                            attributes[key] = True
                        elif value.lower() == 'false':
                            attributes[key] = False
                        else:
                            try: 
                                if '.' in value: attributes[key] = float(value)
                                else: attributes[key] = int(value)
                            except ValueError:
                                attributes[key] = value 
                    
                    node_id_val = attributes.get("id", attributes.get("name", str(uuid.uuid4().hex[:8]))) # Shorter UUID

                    existing_node_idx = -1
                    if op_type == "MERGE":
                        for i, n in enumerate(self.current_graph_data_structure["nodes"]):
                            if n.get("id") == node_id_val: existing_node_idx = i; break
                            if "name" in attributes and n.get("attributes", {}).get("name") == attributes["name"] and n.get("label") == label: existing_node_idx = i; break
                            if "title" in attributes and n.get("attributes", {}).get("title") == attributes["title"] and n.get("label") == label: existing_node_idx = i; break
                    
                    if existing_node_idx != -1: 
                        self.current_graph_data_structure["nodes"][existing_node_idx]["attributes"].update(attributes)
                        self.current_graph_data_structure["nodes"][existing_node_idx]["label"] = label 
                        self.add_log_message(f"Merged/Updated node: {node_id_val}\n")
                    else: 
                        if "id" not in attributes: attributes["id"] = node_id_val 
                        new_node = {"id": node_id_val, "label": label, "attributes": attributes}
                        self.current_graph_data_structure["nodes"].append(new_node)
                        self.add_log_message(f"Created node: {node_id_val} ({label})\n")
                    
                    if node_var: node_vars_map[node_var] = node_id_val

                except Exception as e: # Catch broader errors during node processing
                    self.add_log_message(f"Cypher Parser Error (Node): {e} for props '{props_str}' in statement: {stmt}\n")


            elif rel_match:
                op_type = rel_match.group(1).upper()
                source_var = rel_match.group(2)
                rel_label = rel_match.group(4) if rel_match.group(4) else "RELATED_TO"
                target_var = rel_match.group(5)

                source_id = node_vars_map.get(source_var, source_var) 
                target_id = node_vars_map.get(target_var, target_var) 

                rel_exists = False
                if op_type == "MERGE":
                    for rel in self.current_graph_data_structure["relationships"]:
                        if rel["source"] == source_id and rel["target"] == target_id and rel["type"] == rel_label:
                            rel_exists = True; break
                
                if not rel_exists: 
                    self.current_graph_data_structure["relationships"].append(
                        {"source": source_id, "target": target_id, "type": rel_label}
                    )
                    self.add_log_message(f"Created relationship: ({source_id})-[:{rel_label}]->({target_id})\n")
                else:
                    self.add_log_message(f"Merged/Existing relationship: ({source_id})-[:{rel_label}]->({target_id})\n")
            
            elif stmt: 
                self.add_log_message(f"Cypher Parser Warning: Unsupported or malformed statement skipped: {stmt}\n")

        self.add_log_message("Custom Cypher processing finished.\n")
        self.visualize_current_graph(force_redraw=True) 


    def _obfuscate_path(self, full_path):
        if not full_path: return ""
        try:
            path_parts = [p for p in full_path.split(os.sep) if p] 
            if not path_parts: return full_path 
            if len(path_parts) > 3: 
                if ":" in path_parts[0] and len(path_parts) > 3: 
                    if len(path_parts) > 4: 
                        return os.path.join(path_parts[0] + os.sep, path_parts[1], "...", *path_parts[-2:])
                    return os.path.join(path_parts[0] + os.sep, "...", *path_parts[-2:])
                return os.path.join(path_parts[0], "...", *path_parts[-2:])
            else: return full_path
        except Exception: return full_path 

    def browse_folder(self):
        initial_dir = self.actual_pdf_folder_path or r"C:\Users\Ghoar\Desktop\research files"
        if not os.path.isdir(initial_dir): initial_dir = os.path.expanduser("~")
        folder_selected = filedialog.askdirectory(initialdir=initial_dir, title="Select Research Folder")
        if folder_selected:
            self.actual_pdf_folder_path = folder_selected 
            obfuscated_display_path = self._obfuscate_path(folder_selected)
            self.pdf_folder_path.set(obfuscated_display_path) 
            self.load_pdf_files(self.actual_pdf_folder_path) 
            self.update_llm_pdf_combobox()

    def load_pdf_files(self, folder_path): 
        self.pdf_files = []
        self.pdf_listbox.delete(0, tk.END)
        if not folder_path or not os.path.isdir(folder_path): 
            self.pdf_folder_path.set("") 
            return
        try:
            for item in os.listdir(folder_path):
                if item.lower().endswith(".pdf"):
                    full_path = os.path.join(folder_path, item)
                    self.pdf_files.append({"name": item, "path": full_path})
                    self.pdf_listbox.insert(tk.END, item)
            if not self.pdf_files: messagebox.showinfo("No PDFs", "No PDF files found.")
        except Exception as e: 
            messagebox.showerror("Error Loading PDFs", f"Failed to load PDFs: {e}")
            self.pdf_folder_path.set(self._obfuscate_path(folder_path)) 
        self.clear_pdf_viewer()

    def on_pdf_select(self, event=None): # pylint: disable=unused-argument
        selected_indices = self.pdf_listbox.curselection()
        if not selected_indices: return
        pdf_info = self.pdf_files[selected_indices[0]] 
        try:
            if self.current_pdf_document: self.current_pdf_document.close()
            self.current_pdf_document = fitz.open(pdf_info["path"])
            self.current_pdf_page_num = 0; self.current_zoom_factor = 1.0
            self.display_page(); self.update_page_nav_buttons()
        except Exception as e:
            messagebox.showerror("Error Opening PDF", f"Failed to open {pdf_info['name']}: {e}")
            self.clear_pdf_viewer()

    def display_page(self):
        if not self.current_pdf_document or self.current_pdf_document.page_count == 0:
            self.clear_pdf_viewer(); return
        try:
            page = self.current_pdf_document.load_page(self.current_pdf_page_num)
            canvas_width = self.pdf_canvas.winfo_width()
            canvas_height = self.pdf_canvas.winfo_height()
            if canvas_width <= 1 or canvas_height <= 1: 
                self.pdf_canvas.after(100, self.display_page); return
            mat = fitz.Matrix(self.current_zoom_factor, self.current_zoom_factor)
            pix = page.get_pixmap(matrix=mat)
            img_data = pix.tobytes("ppm")
            self.pdf_page_image = tk.PhotoImage(data=img_data)
            self.pdf_canvas.delete("all") 
            self.pdf_canvas.config(scrollregion=(0, 0, pix.width, pix.height)) 
            self.pdf_canvas.create_image(0, 0, anchor=tk.NW, image=self.pdf_page_image)
            self.page_label.config(text=f"Page: {self.current_pdf_page_num + 1}/{self.current_pdf_document.page_count}")
        except Exception as e:
            print(f"Error displaying page {self.current_pdf_page_num}: {e}") 
            self.clear_pdf_viewer()

    def on_canvas_resize(self, event=None): # pylint: disable=unused-argument
        if self.current_pdf_document: self.display_page()

    def prev_page(self):
        if self.current_pdf_document and self.current_pdf_page_num > 0:
            self.current_pdf_page_num -= 1; self.display_page(); self.update_page_nav_buttons()

    def next_page(self):
        if self.current_pdf_document and self.current_pdf_page_num < self.current_pdf_document.page_count - 1:
            self.current_pdf_page_num += 1; self.display_page(); self.update_page_nav_buttons()
            
    def zoom(self, factor):
        self.current_zoom_factor *= factor;
        if self.current_pdf_document: self.display_page()

    def update_page_nav_buttons(self):
        has_doc = self.current_pdf_document and self.current_pdf_document.page_count > 0
        self.prev_page_button.config(state=tk.NORMAL if has_doc and self.current_pdf_page_num > 0 else tk.DISABLED)
        self.next_page_button.config(state=tk.NORMAL if has_doc and self.current_pdf_page_num < self.current_pdf_document.page_count - 1 else tk.DISABLED)
        self.page_label.config(text=f"Page: {self.current_pdf_page_num + 1}/{self.current_pdf_document.page_count}" if has_doc else "Page: -/-")
            
    def clear_pdf_viewer(self):
        self.pdf_canvas.delete("all")
        if self.current_pdf_document: self.current_pdf_document.close(); self.current_pdf_document = None
        self.current_pdf_page_num = 0; self.pdf_page_image = None; self.update_page_nav_buttons()

    def update_llm_pdf_combobox(self):
        pdf_names = [pdf_info["name"] for pdf_info in self.pdf_files]
        self.llm_pdf_combobox['values'] = pdf_names
        if pdf_names: self.llm_pdf_combobox.current(0)
        else: self.llm_pdf_combobox.set('')

    def add_log_message(self, message):
        if hasattr(self, 'llm_progress_text') and self.llm_progress_text.winfo_exists(): 
            self.llm_progress_text.insert(tk.END, message)
            self.llm_progress_text.see(tk.END); self.root.update_idletasks()

    def _append_to_chat_conversation_display(self, role, content): 
        if hasattr(self, 'chat_conversation_area') and self.chat_conversation_area.winfo_exists():
            self.chat_conversation_area.config(state=tk.NORMAL)
            self.chat_conversation_area.insert(tk.END, f"{role.capitalize()}: {content}\n\n")
            self.chat_conversation_area.config(state=tk.DISABLED)
            self.chat_conversation_area.see(tk.END)

    def _set_summary_display(self, summary_content):
        if hasattr(self, 'summary_display_area') and self.summary_display_area.winfo_exists():
            self.summary_display_area.config(state=tk.NORMAL)
            self.summary_display_area.delete('1.0', tk.END)
            self.summary_display_area.insert(tk.END, summary_content)
            self.summary_display_area.config(state=tk.DISABLED)
            self.summary_display_area.see(tk.END)

    def _set_graph_data_display(self, graph_data_content):
        if hasattr(self, 'graph_data_text_area') and self.graph_data_text_area.winfo_exists():
            self.graph_data_text_area.config(state=tk.NORMAL)
            self.graph_data_text_area.delete('1.0', tk.END)
            self.graph_data_text_area.insert(tk.END, graph_data_content)
            self.graph_data_text_area.config(state=tk.DISABLED)
            self.graph_data_text_area.see(tk.END)

    def _parse_llm_graph_output(self, llm_output_text):
        # This parser is now more of a fallback or for CSV loading, 
        # as the primary graph creation path expects direct Cypher from the LLM.
        parsed_data = {"nodes": [], "relationships": []}
        try:
            nodes_section_match = re.search(r"NODES:(.*?)(RELATIONSHIPS:|CYPHER QUERY:|$)", llm_output_text, re.IGNORECASE | re.DOTALL)
            relationships_section_match = re.search(r"RELATIONSHIPS:(.*?)(CYPHER QUERY:|$)", llm_output_text, re.IGNORECASE | re.DOTALL)
            node_map = {} 

            if nodes_section_match:
                nodes_text = nodes_section_match.group(1).strip()
                node_pattern = re.compile(r"-\s*\((.*?):?(\w+)?\s*(\{.*?\})\)")
                for i, line in enumerate(nodes_text.split('\n')):
                    line = line.strip()
                    if not line.startswith("- ("): continue
                    match = node_pattern.match(line)
                    if match:
                        node_variable = match.group(1).strip() if match.group(1) else None
                        node_type = match.group(2) if  match.group(2) else "Unknown"
                        if not node_variable and ":" in node_type : 
                            node_variable = node_type.split(":")[0] if ":" in node_type else None
                            node_type = node_type.split(":")[1] if ":" in node_type else node_type
                        props_str = match.group(3)
                        try:
                            props_str_json_like = props_str
                            props_str_json_like = re.sub(r'([{,]\s*)(\w+)(\s*:)', r'\1"\2"\3', props_str_json_like)
                            props_str_json_like = re.sub(r'(:\s*)(?!["\d\[{])([^,}]+)(?=[,}])', r'\1"\2"', props_str_json_like)
                            props_str_json_like = re.sub(r'(:\s*)(?!["\d\[{])([^}]+)(?=\s*})', r'\1"\2"', props_str_json_like)
                            attributes = json.loads(props_str_json_like)
                            node_id_val = attributes.get("id", attributes.get("name", attributes.get("title", f"{node_type}_{i}_{uuid.uuid4().hex[:6]}")))
                            if node_variable and node_variable != node_type: 
                                node_map[node_variable] = node_id_val
                            parsed_data["nodes"].append({"id": node_id_val, "label": node_type, "attributes": attributes})
                        except json.JSONDecodeError as e:
                            self.add_log_message(f"Warning: Could not parse node properties: {props_str} due to {e}\n")
                            parsed_data["nodes"].append({"id": f"error_node_{i}", "label": node_type or "Unknown", "attributes": {"raw": props_str, "error": "parsing_failed"}})
            
            if relationships_section_match:
                relationships_text = relationships_section_match.group(1).strip()
                rel_pattern = re.compile(r"-\s*\((.*?)\)\s*-\s*\[:(.*?)\]\s*->\s*\((.*?)\)")
                for line in relationships_text.split('\n'):
                    line = line.strip()
                    if not line.startswith("- ("): continue
                    match = rel_pattern.match(line)
                    if match:
                        source_ref = match.group(1).strip() 
                        rel_type = match.group(2).strip()
                        target_ref = match.group(3).strip()
                        def resolve_node_id(ref_str, nodes_list, local_node_map):
                            if ref_str in local_node_map: return local_node_map[ref_str]
                            for node in nodes_list: 
                                if node["id"] == ref_str: return node["id"]
                                if node["attributes"].get("name") == ref_str: return node["id"]
                                if node["attributes"].get("title") == ref_str: return node["id"]
                            return ref_str 
                        source_id = resolve_node_id(source_ref, parsed_data["nodes"], node_map)
                        target_id = resolve_node_id(target_ref, parsed_data["nodes"], node_map)
                        parsed_data["relationships"].append({"source": source_id, "target": target_id, "type": rel_type})
        except Exception as e:
            self.add_log_message(f"Error parsing LLM graph output: {e}\n")
        return parsed_data


    async def summarize_pdf_async_wrapper(self):
        self._set_summary_display("") 
        if hasattr(self, 'chat_conversation_area') and self.chat_conversation_area.winfo_exists():
            self.chat_conversation_area.config(state=tk.NORMAL)
            self.chat_conversation_area.delete('1.0', tk.END) 
            self.chat_conversation_area.config(state=tk.DISABLED)
        
        if hasattr(self, 'llm_progress_text') and self.llm_progress_text.winfo_exists():
            self.llm_progress_text.delete('1.0', tk.END)
        self.add_log_message("Starting summarization process...\n")

        api_key = self.llm_api_key_entry.get()
        selected_pdf_name = self.llm_pdf_combobox.get()
        selected_llm_type = self.llm_selection_combo.get() 

        if not selected_pdf_name:
            messagebox.showwarning("No PDF Selected", "Please select a PDF to summarize."); self.add_log_message("Error: No PDF selected.\n"); return

        pdf_to_analyze = next((pdf for pdf in self.pdf_files if pdf["name"] == selected_pdf_name), None)
        if not pdf_to_analyze:
            messagebox.showerror("Error", "Selected PDF not found."); self.add_log_message(f"Error: PDF '{selected_pdf_name}' not found.\n"); return

        self.add_log_message(f"Selected PDF: {pdf_to_analyze['name']} for summarization and chat.\n")
        self.add_log_message(f"Selected LLM: {selected_llm_type}\n")

        try:
            self.add_log_message("Extracting text from PDF...\n")
            doc = fitz.open(pdf_to_analyze["path"])
            self.current_pdf_text_for_chat = "".join(doc.load_page(i).get_text("text") for i in range(doc.page_count))
            doc.close()
            
            if not self.current_pdf_text_for_chat.strip():
                messagebox.showwarning("Empty PDF", "Selected PDF contains no extractable text.")
                self.add_log_message("Error: PDF contains no extractable text.\n"); self.current_pdf_text_for_chat = ""; return

            self.add_log_message(f"PDF text extraction complete. Total chars: {len(self.current_pdf_text_for_chat)}\n")
            
            initial_prompt_content = f"Please provide a concise summary of the following text:\n\n{self.current_pdf_text_for_chat}"
            
            if selected_llm_type == "default-OpenAI":
                messages_for_summary = [
                    {"role": "system", "content": "You are an expert assistant that summarizes documents and then discusses them, drawing information primarily from the provided document text."},
                    {"role": "user", "content": initial_prompt_content}
                ]
            else: 
                messages_for_summary = initial_prompt_content 

            self.add_log_message(f"Calling {selected_llm_type} for initial summary...\n")
            summary_text = await process_llm_request(api_key, messages_for_summary, selected_llm_type, 
                                                     is_chat_completion=(selected_llm_type == "default-OpenAI"),
                                                     progress_callback=self.add_log_message)
            
            self._set_summary_display(summary_text) 
            
            self.llm_chat_history = [] 
            if selected_llm_type == "default-OpenAI":
                self.llm_chat_history.extend(messages_for_summary) 
                self.llm_chat_history.append({"role": "assistant", "content": summary_text})
            elif selected_llm_type == "Google Gemini":
                self.llm_chat_history.append({"role": "user", "content": initial_prompt_content}) 
                self.llm_chat_history.append({"role": "assistant", "content": summary_text})

            self.add_log_message("Summarization complete. Ready for chat.\n")
            self._append_to_chat_conversation_display("System", "Summary generated. You can now ask questions about the PDF content.")

        except Exception as e:
            error_msg = f"Error during summarization: {e}"; messagebox.showerror("Summarization Error", error_msg)
            self.add_log_message(f"Error: {error_msg}\n"); self.current_pdf_text_for_chat = ""
        finally:
            if self.current_pdf_text_for_chat:
                self.chat_input_entry.config(state=tk.NORMAL); self.send_chat_button.config(state=tk.NORMAL)
            else:
                self.chat_input_entry.config(state=tk.DISABLED); self.send_chat_button.config(state=tk.DISABLED)

    async def create_graph_data_async_wrapper(self):
        self.add_log_message("Starting graph data creation process...\n")
        self._set_graph_data_display("Processing... Please wait.") 
        self.current_graph_data_structure = {"nodes": [], "relationships": []} # Explicitly reset here

        api_key = self.llm_api_key_entry.get()
        selected_llm_type = self.llm_selection_combo.get()

        if not self.current_pdf_text_for_chat:
            messagebox.showwarning("No PDF Content", "Please summarize a PDF first to provide content for graph data extraction.")
            self.add_log_message("Error: No PDF content available for graph data extraction.\n")
            self._set_graph_data_display("Error: No PDF content. Please summarize a PDF first.")
            return

        # Updated prompt to request ONLY Cypher
        graph_prompt_template = """You are an expert knowledge graph engineer. Given the research paper content below, generate ONLY the Cypher queries needed to create the nodes and relationships representing the key structured data from the paper. Do not include any other text, explanations, or section headers like "NODES:", "RELATIONSHIPS:", or "CYPHER QUERY:". Output only the Cypher statements.

## Example of desired Cypher output format:
MERGE (p:Paper {{id: "doi:1234", title: "Example Paper Title", year: 2021}})
MERGE (a:Author {{name: "Jane Doe"}})
MERGE (i:Institution {{name: "MIT"}})
MERGE (c:Concept {{name: "Quantum Entanglement"}})
MERGE (a)-[:AUTHORED]->(p)
MERGE (a)-[:AFFILIATED_WITH]->(i)
MERGE (p)-[:MENTIONS]->(c)

## Research Paper:
{pdf_content}
"""
        
        full_graph_prompt = graph_prompt_template.format(pdf_content=self.current_pdf_text_for_chat)
        
        messages_for_graph_request = full_graph_prompt 
        if selected_llm_type == "default-OpenAI": 
             messages_for_graph_request = [
                {"role": "system", "content": "You are an expert knowledge graph engineer. Output ONLY Cypher queries."}, 
                {"role": "user", "content": full_graph_prompt}
            ]

        self.add_log_message(f"Calling {selected_llm_type} for Cypher query generation...\n")
        try:
            cypher_query_response = await process_llm_request(api_key, messages_for_graph_request, selected_llm_type, 
                                                            is_chat_completion=(selected_llm_type == "default-OpenAI"), 
                                                            progress_callback=self.add_log_message)
            
            self._set_graph_data_display(cypher_query_response) 
            self.custom_cypher_text_area.delete("1.0", tk.END)
            self.custom_cypher_text_area.insert("1.0", cypher_query_response) 
            
            self.add_log_message("Cypher query generation complete. Attempting to parse and visualize...\n")
            self.run_custom_cypher() 

            if hasattr(self, 'graph_db_tab') and self.graph_db_tab.winfo_exists(): 
                 self.notebook.select(self.graph_viz_tab) 
        except Exception as e:
            error_msg = f"Error during graph data extraction or processing: {e}"
            messagebox.showerror("Graph Data Error", error_msg)
            self.add_log_message(f"Graph Data Error: {error_msg}\n")
            self._set_graph_data_display(f"Error generating or processing graph data:\n{error_msg}")


    async def chat_message_async_wrapper(self):
        user_message_text = self.chat_input_entry.get().strip()
        if not user_message_text: return
        if not self.current_pdf_text_for_chat: 
            messagebox.showwarning("No Context", "Please summarize a PDF first to chat about it."); return

        self.chat_input_entry.delete(0, tk.END)
        self._append_to_chat_conversation_display("User", user_message_text) 
        self.add_log_message(f"User asked: {user_message_text}\n")

        api_key = self.llm_api_key_entry.get()
        selected_llm_type = self.llm_selection_combo.get()

        self.llm_chat_history.append({"role": "user", "content": user_message_text})
        messages_to_send = self.llm_chat_history 

        if selected_llm_type == "default-OpenAI":
            has_system_prompt = any(msg.get("role") == "system" for msg in self.llm_chat_history)
            if not has_system_prompt:
                 self.llm_chat_history.insert(0, {"role": "system", "content": f"You are discussing a document. The document's content was previously summarized and the summary is part of this conversation. Base your answers on the document's content. The full document text is:\n\n{self.current_pdf_text_for_chat}"})
                 messages_to_send = self.llm_chat_history 

        self.add_log_message(f"Sending chat message to {selected_llm_type}...\n")
        
        try:
            llm_response_text = await process_llm_request(api_key, messages_to_send, selected_llm_type, 
                                                            is_chat_completion=True, 
                                                            progress_callback=self.add_log_message)
            self._append_to_chat_conversation_display("Assistant", llm_response_text) 

            self.llm_chat_history.append({"role": "assistant", "content": llm_response_text}) 

            self.add_log_message("LLM response received.\n")
        except Exception as e:
            error_msg = f"Error during chat: {e}"; messagebox.showerror("Chat Error", error_msg)
            self.add_log_message(f"Chat Error: {error_msg}\n"); self._append_to_chat_conversation_display("System Error", str(e))

    def summarize_selected_pdf(self): 
        threading.Thread(target=self.run_async_task, args=(self.summarize_pdf_async_wrapper(),), daemon=True).start()

    def create_graph_data_from_pdf(self):
        threading.Thread(target=self.run_async_task, args=(self.create_graph_data_async_wrapper(),), daemon=True).start()

    def handle_chat_submission(self):
        threading.Thread(target=self.run_async_task, args=(self.chat_message_async_wrapper(),), daemon=True).start()
        
    def handle_chat_submission_event(self, event): 
        self.handle_chat_submission(); return "break" 

    def run_async_task(self, coro):
        try: loop = asyncio.get_running_loop()
        except RuntimeError: loop = asyncio.new_event_loop(); asyncio.set_event_loop(loop)
        try: loop.run_until_complete(coro)
        finally: pass

    def export_chat_to_pdf(self):
        if not REPORTLAB_AVAILABLE:
            messagebox.showerror("Missing Daependency",
                                 "The 'reportlab' library is not installed. "
                                 "Please install it to use PDF export:\n\n"
                                 "pip install reportlab")
            return

        chat_content = self.chat_conversation_area.get("1.0", tk.END).strip() 
        if not chat_content:
            messagebox.showinfo("Empty Chat", "There is no chat conversation to export.")
            return

        filepath = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Documents", "*.pdf"), ("All Files", "*.*")],
            title="Save Chat Conversation As PDF"
        )

        if not filepath: return 

        try:
            self.add_log_message(f"Exporting chat conversation to PDF: {filepath}\n")
            doc = SimpleDocTemplate(filepath)
            styles = getSampleStyleSheet()
            story = []
            
            lines = chat_content.split('\n')
            for line in lines:
                if line.strip(): 
                    if line.lower().startswith("user:"):
                        p = Paragraph(line, styles['Normal']) 
                    elif line.lower().startswith("assistant:") or line.lower().startswith("system:"): 
                        p = Paragraph(line, styles['Italic']) 
                    else:
                        p = Paragraph(line, styles['Normal'])
                    story.append(p)
                else: 
                    story.append(Spacer(1, 0.1 * inch))
            
            doc.build(story)
            messagebox.showinfo("Export Successful", f"Chat conversation successfully exported to\n{filepath}")
            self.add_log_message("Chat conversation export successful.\n")
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export chat conversation to PDF: {e}")
            self.add_log_message(f"Error exporting chat conversation: {e}\n")
    
    def visualize_current_graph(self, force_redraw=False): # pylint: disable=unused-argument
        if not GRAPH_LIBS_AVAILABLE:
            self.add_log_message("Graph libraries (NetworkX/Matplotlib) not available.\n")
            return

        if not self.current_graph_data_structure or \
           (not self.current_graph_data_structure.get("nodes") and not self.current_graph_data_structure.get("relationships")):
            if self.mpl_canvas:
                self.mpl_canvas.get_tk_widget().destroy()
                self.mpl_canvas = None
            if self.mpl_toolbar:
                self.mpl_toolbar.destroy()
                self.mpl_toolbar = None
            for widget in self.graph_viz_canvas_frame.winfo_children(): widget.destroy() 
            no_data_label = ttk.Label(self.graph_viz_canvas_frame, text="No graph data to visualize.", style="App.TLabel")
            no_data_label.pack(expand=True)
            # No messagebox here as it's a visual update, not necessarily an error.
            self.add_log_message("Attempted to visualize an empty graph.\n")
            return

        try:
            if self.mpl_canvas: 
                self.mpl_canvas.get_tk_widget().destroy()
                self.mpl_canvas = None
            if self.mpl_toolbar: 
                self.mpl_toolbar.destroy()
                self.mpl_toolbar = None
            for widget in self.graph_viz_canvas_frame.winfo_children(): widget.destroy() 
            
            theme_name = self.current_theme.get()
            theme_settings = THEMES.get(theme_name, THEMES["Default"])
            fig_bg_color = theme_settings.get("graph_canvas_bg", "white")
            node_color = "#33FF33" if theme_name == "Matrix" else "#1f78b4"
            edge_color = "#AAAAAA" if theme_name == "Matrix" else "gray" 
            label_color = theme_settings.get("text_fg", "black")

            fig, ax = plt.subplots(facecolor=fig_bg_color) 
            ax.set_facecolor(fig_bg_color) 

            G = nx.DiGraph() 

            node_labels = {}
            all_node_ids_in_rels = set()
            for rel_data in self.current_graph_data_structure.get("relationships", []):
                if rel_data.get("source"): all_node_ids_in_rels.add(rel_data["source"])
                if rel_data.get("target"): all_node_ids_in_rels.add(rel_data["target"])
            
            current_node_ids = set()
            for node_data in self.current_graph_data_structure.get("nodes", []):
                node_id = node_data.get("id", str(uuid.uuid4())) 
                node_data["id"] = node_id 
                G.add_node(node_id, **node_data.get("attributes", {}))
                label_text = node_data.get("attributes", {}).get("name", 
                               node_data.get("attributes", {}).get("title", 
                               node_data.get("id", node_id)))
                node_labels[node_id] = f"{node_data.get('label', '')}\n({str(label_text)[:20]})" 
                current_node_ids.add(node_id)

            for node_id in all_node_ids_in_rels:
                if node_id not in current_node_ids:
                    G.add_node(node_id) 
                    node_labels[node_id] = str(node_id)[:20] 
                    current_node_ids.add(node_id)


            for rel_data in self.current_graph_data_structure.get("relationships", []):
                source = rel_data.get("source")
                target = rel_data.get("target")
                if source and target and source in G and target in G: 
                    G.add_edge(source, target, type=rel_data.get("type", ""))
            
            if not G.nodes():
                self.add_log_message("No nodes to visualize after processing.\n")
                ax.text(0.5, 0.5, "No graph data to display.", horizontalalignment='center', verticalalignment='center', transform=ax.transAxes, color=label_color)
            else:
                pos = nx.spring_layout(G, k=0.7, iterations=50, seed=42)  
                nx.draw_networkx_nodes(G, pos, ax=ax, node_size=2000, node_color=node_color, alpha=0.9, edgecolors=label_color) 
                nx.draw_networkx_edges(G, pos, ax=ax, edge_color=edge_color, arrowstyle='-|>', arrowsize=15, alpha=0.7, node_size=2000, connectionstyle='arc3,rad=0.1') 
                nx.draw_networkx_labels(G, pos, labels=node_labels, ax=ax, font_size=7, font_color=label_color, font_weight='bold')
                
                edge_labels = {(u, v): d.get('type', '') for u, v, d in G.edges(data=True)}
                nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, ax=ax, font_size=6, font_color=label_color)

            ax.axis('off') 
            fig.tight_layout() 

            self.mpl_canvas = FigureCanvasTkAgg(fig, master=self.graph_viz_canvas_frame)
            self.mpl_canvas.draw()
            
            self.mpl_toolbar = NavigationToolbar2Tk(self.mpl_canvas, self.graph_viz_canvas_frame, pack_toolbar=False)
            self.mpl_toolbar.update()
            self.mpl_toolbar.pack(side=tk.BOTTOM, fill=tk.X)
            self.mpl_toolbar.config(background=theme_settings.get("Toolbar.background", theme_settings["root_bg"]))
            for child in self.mpl_toolbar.winfo_children():
                try:
                    child.configure(bg=theme_settings.get("Toolbar.background", theme_settings["root_bg"]),
                                    fg=theme_settings.get("text_fg", "black")) 
                except tk.TclError: pass 


            self.mpl_canvas.get_tk_widget().configure(bg=theme_settings["graph_canvas_bg"])
            self.mpl_canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=True)
            
            self.add_log_message("Graph visualized.\n")

        except Exception as e:
            messagebox.showerror("Graph Visualization Error", f"Could not visualize graph: {e}")
            self.add_log_message(f"Error visualizing graph: {e}\n")

    def reset_graph_data_and_visualization(self):
        self.current_graph_data_structure = {"nodes": [], "relationships": []}
        self._set_graph_data_display("") 
        if hasattr(self, 'custom_cypher_text_area') and self.custom_cypher_text_area.winfo_exists():
            self.custom_cypher_text_area.delete("1.0", tk.END) 

        if self.mpl_canvas:
            self.mpl_canvas.get_tk_widget().destroy()
            self.mpl_canvas = None
        if self.mpl_toolbar:
            self.mpl_toolbar.destroy()
            self.mpl_toolbar = None
        
        for widget in self.graph_viz_canvas_frame.winfo_children():
            widget.destroy()
        
        no_data_label = ttk.Label(self.graph_viz_canvas_frame, text="Graph has been reset. Visualize new data.", style="App.TLabel")
        no_data_label.pack(expand=True)


        self.add_log_message("Graph data and visualization have been reset.\n")


    def save_graph_to_csv(self):
        if not self.current_graph_data_structure or \
           (not self.current_graph_data_structure.get("nodes") and not self.current_graph_data_structure.get("relationships")):
            messagebox.showinfo("No Graph Data", "No graph data to save. Please use 'Create Graph Data' first.")
            return

        directory = filedialog.askdirectory(title="Select Directory to Save CSV Files")
        if not directory:
            return

        nodes_filepath = os.path.join(directory, "nodes.csv")
        rels_filepath = os.path.join(directory, "relationships.csv")

        try:
            with open(nodes_filepath, 'w', newline='', encoding='utf-8') as f_nodes:
                if not self.current_graph_data_structure["nodes"]:
                    f_nodes.write("") 
                else:
                    all_node_attr_keys = set()
                    for node in self.current_graph_data_structure["nodes"]:
                        all_node_attr_keys.update(node.get("attributes", {}).keys())
                    
                    fieldnames_nodes = ['id', 'label'] + sorted(list(all_node_attr_keys))
                    writer_nodes = csv.DictWriter(f_nodes, fieldnames=fieldnames_nodes, extrasaction='ignore')
                    writer_nodes.writeheader()
                    for node_data in self.current_graph_data_structure["nodes"]:
                        row = {"id": node_data.get("id"), "label": node_data.get("label")}
                        row.update(node_data.get("attributes", {}))
                        writer_nodes.writerow(row)
            
            with open(rels_filepath, 'w', newline='', encoding='utf-8') as f_rels:
                if not self.current_graph_data_structure["relationships"]:
                     f_rels.write("") 
                else:
                    fieldnames_rels = ['source', 'target', 'type']
                    writer_rels = csv.DictWriter(f_rels, fieldnames=fieldnames_rels)
                    writer_rels.writeheader()
                    for rel_data in self.current_graph_data_structure["relationships"]:
                        writer_rels.writerow(rel_data)
            
            messagebox.showinfo("Save Successful", f"Graph data saved to:\n{nodes_filepath}\n{rels_filepath}")
            self.add_log_message(f"Graph data saved to CSV files in {directory}\n")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save graph data to CSV: {e}")
            self.add_log_message(f"Error saving graph data to CSV: {e}\n")

    def load_graph_from_csv(self):
        nodes_filepath = filedialog.askopenfilename(
            title="Select Nodes CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not nodes_filepath: return

        rels_filepath = filedialog.askopenfilename(
            title="Select Relationships CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if not rels_filepath: return

        loaded_nodes = []
        loaded_rels = []
        try:
            with open(nodes_filepath, 'r', newline='', encoding='utf-8') as f_nodes:
                reader_nodes = csv.DictReader(f_nodes)
                for row in reader_nodes:
                    node_id = row.pop('id', None)
                    label = row.pop('label', None)
                    if node_id and label: 
                        loaded_nodes.append({"id": node_id, "label": label, "attributes": row})
            
            with open(rels_filepath, 'r', newline='', encoding='utf-8') as f_rels:
                reader_rels = csv.DictReader(f_rels)
                for row in reader_rels:
                    if 'source' in row and 'target' in row and 'type' in row: 
                        loaded_rels.append({"source": row['source'], "target": row['target'], "type": row['type']})
            
            self.current_graph_data_structure = {"nodes": loaded_nodes, "relationships": loaded_rels}
            self._set_graph_data_display(
                f"Loaded from CSV:\n\nNODES ({len(loaded_nodes)}):\n" + 
                "\n".join([f"- (:{n.get('label')} {{id: \"{n.get('id')}\", ...}})" for n in loaded_nodes[:5]]) + 
                ("\n..." if len(loaded_nodes) > 5 else "") +
                f"\n\nRELATIONSHIPS ({len(loaded_rels)}):\n" +
                "\n".join([f"- ({r.get('source')})-[:{r.get('type')}]->({r.get('target')})" for r in loaded_rels[:5]]) + 
                ("\n..." if len(loaded_rels) > 5 else "")
            )
            messagebox.showinfo("Load Successful", "Graph data loaded from CSV files. You can now visualize it.")
            self.add_log_message(f"Graph data loaded from {nodes_filepath} and {rels_filepath}\n")
            self.notebook.select(self.graph_viz_tab)
            self.visualize_current_graph()


        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load graph data from CSV: {e}")
            self.add_log_message(f"Error loading graph data from CSV: {e}\n")
            self.current_graph_data_structure = {"nodes": [], "relationships": []} 


if __name__ == '__main__':
    main_window = tk.Tk()
    app = PDFAnalyzerApp(main_window)
    main_window.mainloop()
