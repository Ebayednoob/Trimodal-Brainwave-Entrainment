# 3D Audio Entrainment Platform

## 1. Introduction

Welcome to the 3D Audio Entrainment Platform! This Python application is designed for generating and experiencing complex audio environments, primarily for brainwave entrainment and sound therapy experimentation. It allows users to control multiple audio channels, each with adjustable frequencies, amplitudes, isochronic modulation, and 3D spatial positioning. The platform also includes features for recording sessions with volume automation, saving and loading configurations, and interacting with AI language models for potential future integration.

[A Youtube Tutorial is located here](https://youtu.be/sWEl70FGCJo)

## 2. Features

* **Multi-Channel Control:** Manage up to 12 independent audio channels.
* **Adjustable Parameters per Channel:**
    * **Active State:** Toggle channels on/off.
    * **Carrier Frequency:** 20 Hz to an adjustable maximum (up to 20,000 Hz), with slider and direct entry.
    * **Amplitude:** 0% to 100%.
    * **Isochronic Modulation:** Apply a pulsing effect with adjustable frequency (0-50 Hz).
    * **3D Spatialization:** Control X (left/right), Y (front/back), and Z (up/down - primarily affects volume/distance perception) coordinates for each channel's perceived position.
    * **Individual Waveform Preview:** See a live preview of each channel's source waveform.
* **Global Controls:**
    * **Play/Stop:** Live playback of the mixed audio output.
    * **Display Waveform:** Shows a plot of the combined stereo output (averaged for display).
    * **Reset All:** Reverts all channel settings and recording automation to defaults.
    * **Number of Channels:** Dynamically select how many channels (1-12) are displayed and active.
    * **Max Frequency:** Adjust the maximum frequency for channel sliders (5kHz, 10kHz, 15kHz, 20kHz).
    * **Frequency Presets:** Quickly apply predefined frequency sets (Solfeggio Harmonics, Angel Frequencies, Phi Ratio Frequencies) to active channels.
* **Visualizations:**
    * **3D Spatial Preview:** A top-down (X-Y) graph showing the positions of active channels relative to a central listener. Point size indicates Z-position.
    * **Combined Output Waveform:** Displays the overall mixed audio signal.
* **Configuration Management (Data I/O & Setup Tab):**
    * Save and load entire application setups (channel settings, displayed channels, recording duration, volume automation keyframes, selected presets) as JSON files.
    * View and directly edit the current configuration in JSON format.
    * Apply changes made in the JSON text area back to the application.
* **Recording with Volume Automation (Recording Tab):**
    * Set a total recording duration.
    * Dedicated Start, Pause/Resume, and Stop recording controls.
    * Progress bar and status display.
    * **Volume Automation Graph:** Click to add keyframes to create a custom volume envelope for the duration of the recording. This automation is applied only to the recorded WAV file.
    * Save recordings as stereo WAV files.
* **AI Agent Interface (AI Agent Tab):**
    * Select between LLM providers (currently Gemini and OpenAI).
    * Enter an API key (required for OpenAI, optional for Gemini if environment handles it).
    * Test LLM connection.
    * Chat interface (status window, chat history, message input) for text-based interaction with the selected LLM.

## 3. Requirements

* Python 3.7+
* **Libraries:**
    * `numpy`
    * `sounddevice`
    * `matplotlib`
    * `soundfile` (for saving recordings)
    * `tkinter` (usually included with Python standard library)

## 4. Installation

1.  **Ensure Python is installed.**
2.  **Install the required libraries using pip:**
    Open your terminal or command prompt and run:
    ```bash
    pip install numpy sounddevice matplotlib soundfile
    ```

## 5. Running the Application

1.  Save the application code as a Python file (e.g., `audio_entrainment_gui.py`).
2.  Open your terminal or command prompt, navigate to the directory where you saved the file.
3.  Run the script:
    ```bash
    python audio_entrainment_gui.py
    ```

## 6. User Interface Overview

The application is organized into several tabs for different functionalities.

### 6.1. Tab 1: Controls & Visualization

This is the main operational tab.

* **Top Control Bar:**
    * **Play/Stop:** Start or stop live audio playback of the combined channels.
    * **Display Waveform:** Updates the "Combined Output Waveform" plot at the bottom with the current mix (best used when playback is stopped).
    * **Reset All:** Resets all channel parameters, recording automation, and presets to their default values.
    * **Channels:** Dropdown to select the number of channel control panels to display (1-12).
    * **Max Freq:** Dropdown to set the maximum frequency for the channel frequency sliders (5000, 10000, 15000, 20000 Hz).
    * **Preset:** Dropdown to apply predefined frequency sets to the displayed channels. Selecting "Custom/Manual" means no preset is active.

* **Channel Controls Area (Scrollable, Left Panel):**
    * Contains individual control panels for each active channel (up to 12).
    * **Per Channel:**
        * **Active (Checkbox):** Enables or disables the channel.
        * **Freq (Hz):** Slider and direct entry field to set the channel's carrier frequency. Range: 20 Hz to the selected "Max Freq".
        * **Amp:** Slider to set the channel's amplitude (0-100%).
        * **Enable Iso (Checkbox):** Activates isochronic modulation for this channel.
        * **Iso Freq (Hz):** Entry field for the isochronic modulation frequency (0-50 Hz). Active only if "Enable Iso" is checked.
        * **X Pos (L/R):** Slider for Left/Right spatial positioning (-1.0 to +1.0).
        * **Y Pos (F/B):** Slider for Front/Back spatial positioning (-1.0 to +1.0).
        * **Z Pos (U/D):** Slider for Up/Down spatial positioning (-1.0 to +1.0). Primarily affects perceived distance/volume in the current simplified 3D model.
        * **Waveform Preview:** A small, live plot showing the channel's individual waveform based on its frequency, amplitude, and isochronic settings.

* **3D Spatial Preview (Right Panel):**
    * A top-down (X-Y plane) graph.
    * A central gray circle represents the listener.
    * Each active channel is shown as a colored point. Its X and Y coordinates determine its position.
    * The size of the point indicates its Z-coordinate (larger for more positive/higher Z).
    * Points are labeled with their channel number.
    * Updates when channel positions change or when the number of active channels changes.

* **Combined Output Waveform (Bottom Panel):**
    * Displays a plot of the mixed stereo output, averaged into a single waveform for visualization. Updated by the "Display Waveform" button or when parameters change while not playing.

### 6.2. Tab 2: Data I/O & Setup

This tab allows you to save and load your entire application configuration.

* **Save Configuration Button:** Opens a file dialog to save the current state of all channel parameters, the number of displayed channels, the selected max frequency, the active frequency preset, the recording duration, and any volume automation keyframes to a JSON file.
* **Load Configuration Button:** Opens a file dialog to load a previously saved JSON configuration file. All settings and UI elements will update to match the loaded file.
* **Current Configuration (JSON) - Editable (Text Area):**
    * Displays the current application configuration in a human-readable and LLM-friendly JSON format.
    * **You can directly edit this JSON text.**
* **Apply JSON from Text Button:** Parses the JSON content from the text area and applies it to the application, updating all settings and UI elements. Useful for making precise adjustments or for programmatic/AI-driven changes to the setup.

### 6.3. Tab 3: Recording

This tab is dedicated to creating audio files from your sound setup.

* **Total Recording Time (seconds) Entry:** Specify the desired length of the audio file to be recorded.
* **Recording Controls:**
    * **Start Recording:** Begins the recording process. You will be prompted to choose a file name and location for the WAV file.
    * **Pause/Resume Recording:** Toggles pausing and resuming the recording.
    * **Stop Recording:** Stops the recording process and finalizes the WAV file.
    * **Clear Keyframes:** Removes all volume automation keyframes from the graph below.
* **Progress Bar & Status Label:** Shows the progress of the current recording and its status (e.g., "Recording...", "Paused", "Idle", "Complete").
* **Volume Automation Graph:**
    * **X-axis (Time):** Scales automatically based on the "Total Recording Time" you enter.
    * **Y-axis (Volume):** Represents volume from 0% to 100%.
    * **Adding Keyframes:** Click directly on the graph to add a volume keyframe at that specific time and volume level. The graph will update to show the new point and the interpolated volume curve.
    * **Effect:** This volume automation is applied *only* to the audio being recorded to the WAV file. It does not affect live playback from the "Controls & Visualization" tab.

### 6.4. Tab 4: AI Agent

This tab provides an interface to interact with Large Language Models.

* **LLM Configuration:**
    * **Select LLM:** Dropdown to choose between "Gemini" (uses `gemini-2.0-flash`) and "OpenAI" (uses `gpt-3.5-turbo` by default).
    * **API Key Entry:** A field to enter your API key.
        * For **OpenAI**, this key is **required**.
        * For **Gemini**, if you have a specific Gemini API key you want to use, enter it here. If left blank, the application attempts to use an environment-provided key for `gemini-2.0-flash` (this may depend on the execution environment, like Google's Canvas).
    * **Test Connection Button:** Sends a simple test prompt to the selected LLM to verify connectivity and API key validity.
* **AI Status Window:** A read-only text area displaying status messages from the AI interaction (e.g., "Sending...", "Response received.", error messages).
* **Chat History:** A scrollable, read-only text area showing the conversation history with the AI. User messages are typically styled differently from AI responses.
* **Message Input & Controls:**
    * **Message Entry:** Type your prompts or messages to the AI here. Pressing Enter also sends the message.
    * **Send Button:** Sends the typed message to the selected LLM.
    * **Clear Chat Button:** Clears the chat history and resets the AI status.

## 7. How to Use Specific Features

* **Setting Channel Parameters:** Use the sliders or type directly into the entry fields for frequency, amplitude, etc., within each channel's panel.
* **Frequency Presets:** Select a preset from the "Preset:" dropdown in the top control bar. The frequencies of the displayed channels will update. If you then manually change a channel's frequency, the preset dropdown will revert to "Custom/Manual."
* **Adjusting Max Frequency:** Use the "Max Freq:" dropdown to change the upper limit of the frequency sliders for all channels.
* **Spatial Audio:** Use the X, Y, and Z sliders for each channel. Observe the changes in the "3D Spatial Preview" graph.
* **Saving Configurations:**
    1.  Go to the "Data I/O & Setup" tab.
    2.  Click "Save Configuration."
    3.  Choose a file name and location.
* **Loading Configurations:**
    1.  Go to the "Data I/O & Setup" tab.
    2.  Click "Load Configuration."
    3.  Select your saved `.json` file.
* **Editing JSON Directly:**
    1.  Go to the "Data I/O & Setup" tab.
    2.  The "Current Configuration (JSON)" text area is editable. Make your changes directly to the JSON text.
    3.  Click "Apply JSON from Text" to update the application with your textual edits.
* **Recording Audio:**
    1.  Go to the "Recording" tab.
    2.  Enter your desired "Total Recording Time" in seconds.
    3.  (Optional) Create a volume automation curve by clicking on the "Volume Automation" graph to add keyframes. Use "Clear Keyframes" to start over.
    4.  Click "Start Recording." You'll be prompted to save the WAV file.
    5.  Use "Pause/Resume Recording" and "Stop Recording" as needed.
* **Interacting with AI Agent:**
    1.  Go to the "AI Agent" tab.
    2.  Select your desired LLM (Gemini or OpenAI).
    3.  Enter your API key in the "API Key" field.
    4.  Click "Test Connection" to verify.
    5.  Type your message in the input field at the bottom and click "Send" or press Enter.
    6.  View the conversation in the "Chat History" and status updates in the "AI Status" window.

## 8. Tips & Troubleshooting

* **Audio Output:** Ensure you have a working audio output device selected in your operating system. The application uses your system's default audio output.
* **No Sound (Playback/Recording):**
    * Check if channels are "Active."
    * Ensure channel "Amplitude" is above 0%.
    * If recording with volume automation, make sure your automation curve isn't at 0% volume for the entire duration.
* **API Keys:**
    * **OpenAI:** A valid API key with available credits is required.
    * **Gemini:** If using your own key, ensure it's correctly entered. If relying on an environment-provided key (by leaving the field blank), ensure the environment is configured correctly. `403 Forbidden` errors often relate to API key issues or service enablement on the cloud project.
* **Performance:** With many channels active and all plots updating, the GUI might become less responsive on older hardware. The individual channel waveform previews update on parameter changes, not continuously, to help mitigate this.
* **JSON Editing:** Be careful when editing the JSON directly. An invalid JSON structure will prevent the "Apply JSON from Text" button from working correctly, and an error message will be shown.

## 9. Future Enhancements (Potential)

* More sophisticated 3D audio rendering (e.g., HRTF-based).
* Ability for the AI Agent to directly manipulate the JSON configuration based on natural language commands.
* Support for more LLM providers.
* Advanced keyframe editing (e.g., dragging, deleting individual keyframes).
* Saving/loading individual channel presets.
* Visual feedback for isochronic pulse timing.

We hope you find this platform useful for your audio explorations!
