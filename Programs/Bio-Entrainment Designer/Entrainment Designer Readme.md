# Bio-Entrainment Therapeutics - Full Body Entrainment Designer

## Overview

The Bio-Entrainment Therapeutics - Full Body Entrainment Designer is a Python-based graphical application designed to help users plan and visualize the placement of entrainment nodes (speakers, magnets, lights) within a defined 3D space around a test subject. It includes features for precise positioning, orientation, sizing of nodes, calibration relative to a subject, and an integrated LLM (Large Language Model) control panel for design assistance and analysis.

The application provides a 2D top-down view of a 6ft x 4ft design area where a representation of a test subject can be displayed and nodes can be placed and configured.

## Features

### Designer Tab:

* **Grid-Based Design Area:**
    * A scrollable canvas representing a fixed real-world area of 6ft wide x 4ft deep.
    * A visual grid overlay whose cell size (in pixels) can be adjusted for visual guidance.
* **Node Placement & Configuration:**
    * Place three types of nodes: **Speakers**, **Magnets**, and **Lights**.
    * Custom images are used for each node type (requires `Speaker.png`, `bifiilar.png` for magnets, `LED.png`).
    * **Adjustable Symbol Size:** Define the width and height (in cm) for each node individually.
    * **Adjustable Angle:** Rotate each node from 0 to 359 degrees.
* **Test Subject Representation:**
    * Place a "Body symbol.png" (representing a 5ft tall x 2ft wide subject) onto the canvas.
    * The body symbol is displayed rotated 90 degrees (lying horizontally on the canvas).
    * **Toggle Visibility:** Show or hide the test subject symbol.
    * **Flip Orientation:** Flip the displayed subject symbol 180 degrees horizontally.
* **Calibration Points:**
    * Set three crucial calibration points:
        * **Head Center** (Orange)
        * **Spine Start** (Purple)
        * **Spine End** (Purple)
    * These points are initially placed relative to the (rotated and centered) body symbol.
    * **Adjustable Spine Length:** The target length of the spine (distance between Spine Start and Spine End) can be set in cm. When adjusting, the Head Center and Spine Start points remain fixed, and only the Spine End point moves.
* **Distance Measurement:**
    * Toggle display of distances (in cm) between nodes of the same type.
        * Speaker-to-Speaker: Blue lines
        * Magnet-to-Magnet: Yellow lines
        * Light-to-Light: Red lines
    * Displays the actual distance between the Spine Start and Spine End calibration points.
* **Scale and Zoom:**
    * Adjust the **pixel-to-cm scale** (default 4.0 px/cm, max 10.0 px/cm) to effectively zoom in/out of the design area.
* **Node Management:**
    * **Node List Window:** A separate window lists all placed nodes with their ID, user-editable Label, Type, Position (cm), Size (cm), and Angle. Selecting a node in the list also selects it on the canvas and populates its properties in the control panel.
    * **Delete Selected Node:** Remove the currently selected node from the canvas.
    * **Clear All Nodes:** Remove all placed nodes from the design.

### LLM Control Panel Tab:

* **Gemini API Integration:**
    * **API Key Configuration:** Input field for your Google Gemini API key.
    * **Test Connection:** Button to test if the API key and SDK are working correctly by making a simple call to the Gemini API.
    * **API Call Status Log:** A display area showing logs for API connection tests and LLM interactions (e.g., "Attempting to send...", "API call successful/failed").
* **Design Chat Assistant (Gemini):**
    * A chat interface to discuss and plan designs with a Gemini model (currently `gemini-2.0-flash`).
    * Chat history is maintained for contextual conversations.
* **Alignment Analysis:**
    * **Analyze Current Alignment Button:** Sends a detailed, preset prompt to the Gemini model.
    * The prompt includes the current calibration point data and all placed node data (from the "Current Alignment Data" display).
    * The LLM is tasked to analyze the layout for audio entrainment optimization based on spatial coherence, frequency mapping, wave interaction, and surround sound virtualization.
    * The LLM's analysis is displayed in the chat window.
* **Data Display & Management:**
    * **Current Alignment Data:** A read-only text box displaying a formatted summary of all current calibration points and placed nodes. This data is automatically updated.
    * **Import/Update Alignment Data:**
        * A text box to paste alignment data in the same format as the "Current Alignment Data" display.
        * A "Load Data & Update Designer" button to parse this text and update the entire designer canvas (calibration points and nodes). This allows for loading previously saved or externally generated configurations.
    * **Export Data Button:** Exports the content of the "Current Alignment Data" display and the "Design Chat Assistant" log to a single `.txt` file.

## Setup Instructions

1.  **Python:** Ensure you have Python installed (version 3.7 or newer recommended).
2.  **Libraries:** Install the required Python packages using pip:
    ```bash
    pip install Pillow google-generativeai
    ```
    * `Pillow` is used for image manipulation.
    * `google-generativeai` is required for the LLM features. If this package is not found in the Python environment running the script, LLM features will be simulated or unavailable, and a warning will be printed to the console.
3.  **Symbol Folder & Images:**
    * Create a folder named `Symbol-Folder` in the same directory as the main Python script (`Bio-Entrainment Designer.py`).
    * Place the following image files (PNG format recommended) into the `Symbol-Folder`:
        * `Speaker.png`
        * `bifiilar.png` (used for Magnet nodes)
        * `LED.png`
        * `Body symbol.png` (recommended dimensions for this image should visually match a 5ft tall, 2ft wide subject, e.g., 200x500 pixels if it were upright, though the program resizes it).
    * If images are not found, placeholders will be used.

## How to Run

1.  Navigate to the directory containing the `Bio-Entrainment Designer.py` script and the `Symbol-Folder`.
2.  Run the script from your terminal:
    ```bash
    python "Bio-Entrainment Designer.py"
    ```
    (Or `python3 "Bio-Entrainment Designer.py"` depending on your system's Python alias).

## Using the Application

### Designer Tab:

* **Node Selection:** Click a node type button (Speaker, Magnet, Light) to select the tool.
* **Placing Nodes:** Click on the canvas grid. Nodes snap to the center of the nearest visual grid cell.
* **Node Properties:**
    * **Angle:** Use the slider or input to set the angle (0-359°) for the next node or the currently selected node.
    * **Symbol Size:** Enter width and height in cm for new nodes. For an existing selected node, these fields show its size; modify and click "Update Selected Size" to apply changes.
* **Test Subject:**
    * Use the "Show Test Subject" checkbox to toggle its visibility. It appears centered and rotated 90°.
    * Use "Flip Subject 180°" to change its left-right orientation.
* **Calibration:**
    * Click "Set/Clear Calibration" to place/remove the Head Center, Spine Start, and Spine End points.
    * Enter a "Target Spine (cm)" value and click "Set Spine Length."
        * If calibration points are not set, this sets the target for when they *are* set.
        * If calibration points *are* set, this adjusts the `spine_end` point, keeping `head_center` and `spine_start` fixed.
* **Canvas Controls:**
    * **Visual Grid Size:** Adjust the slider to change the density of the visual grid lines.
    * **Scale (px/cm):** Enter a value (default 4.0, max 10.0) and click "Set" to change the zoom level of the design area.
* **Node List:** Click "Node List" to open/close a separate window detailing all placed nodes. You can select nodes from this list and edit their labels.

### LLM Control Panel Tab:

* **API Configuration:**
    * Enter your Google Gemini API Key in the "API Key" field.
    * Click "Test Connection" to verify the key and SDK setup. Status messages appear in the "API Call Status Log" below.
* **Design Chat Assistant:**
    * Type messages into the input field and press Enter or click "Send" to chat with the Gemini model.
    * The chat history is maintained for context.
* **Analyze Alignment:**
    * Click "Analyze Current Alignment" to send the current design data (from the "Current Alignment Data" display) along with a preset prompt to Gemini for analysis. The response appears in the chat window.
    * Ensure calibration points and/or nodes are placed for meaningful analysis.
* **Data Management:**
    * **Current Alignment Data:** This read-only box shows a live summary of your design.
    * **Import/Update Alignment Data:** Paste previously exported or manually formatted data into the text box and click "Load Data & Update Designer". This will clear the current design and load the new one.
    * **Export Data:** Click to save the content of the "Current Alignment Data" and the "Design Chat Assistant" log to a text file.

## Future Implementations (Potential)

* Functionality to upload and integrate data from other programs, possibly for generating specific cymatic patterns with speaker nodes.

## Troubleshooting

* **"Google Generative AI SDK (google-generativeai) not found" warning:** This means the Python environment running the script cannot find the `google-generativeai` library.
    * Ensure the package is installed in the correct Python environment (the one your script/IDE is using).
    * Try `python -m pip install google-generativeai` or `python3 -m pip install google-generativeai`.
    * If using a virtual environment, ensure it's activated before installing and running the script.
    * Restart your IDE if applicable.
* **Image Not Found:** If node or body symbols don't appear correctly, ensure the `Symbol-Folder` exists in the same directory as the script and contains the correctly named `.png` files.
