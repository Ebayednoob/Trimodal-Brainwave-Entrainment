# PDF Explorer & LLM Analyzer

## Tutorial Video

For a visual guide and walkthrough of the features, please check out our tutorial video:
[Watch the Tutorial](https://youtu.be/tbE6fdXtTW4) 

## Overview

The PDF Explorer & LLM Analyzer is a Python-based desktop application designed for researchers and analysts to efficiently view PDF documents, leverage Large Language Models (LLMs) for text summarization and chat-based analysis, and extract structured graph data from PDF content. The application features a multi-tab interface for easy navigation between PDF viewing, LLM interaction, and graph data management.

## Features

### 1. PDF Viewer Tab
* **Browse & Load PDFs**: Easily select a folder containing your research papers. All PDF files within the selected folder will be listed.
* **Document Display**: View PDF pages directly within the application.
* **Page Navigation**: Navigate through PDF pages using "Previous" and "Next" buttons.
* **Zoom Functionality**: Zoom in and out of PDF pages for better readability.

### 2. LLM Analyzer & Chat Tab
* **Selectable LLMs**: Choose between different Large Language Models for analysis:
    * `default-OpenAI` (e.g., GPT-4.1-turbo)
    * `Google Gemini` (e.g., gemini-1.5-flash-latest)
* **API Key Input**: Securely input your API key for the selected LLM service. The key is masked with asterisks.
* **PDF Summarization**:
    * Select a PDF from the loaded list.
    * Click "Summarize PDF" to generate a concise summary using the chosen LLM. The summary appears in a dedicated, persistent display area.
* **Chat with LLM**:
    * After summarizing a PDF, engage in a conversational chat with the LLM about the PDF's content.
    * The chat history is displayed in a separate, scrollable area.
* **Export Chat**: Save the entire chat conversation (User, Assistant, and System messages) to a PDF file for documentation or sharing.
* **LLM Operation Log**: View progress and log messages from LLM interactions.

### 3. Graph Database Tab
* **"Create Graph Data" from PDF**:
    * After a PDF's text has been loaded (via summarization), click this button to prompt the selected LLM.
    * The LLM is instructed to generate Cypher queries (using `MERGE` for idempotency) to create nodes and relationships based on the PDF content.
* **Display LLM-Generated Cypher**: The raw Cypher query returned by the LLM is displayed in a text area. This can be toggled on/off using a "Show/Hide" checkbox.
* **Custom Cypher Query Input**:
    * A dedicated text area allows users to manually write or paste their own Cypher queries.
    * The LLM-generated Cypher is also automatically populated here for review or modification.
* **"Run Custom Cypher"**:
    * Parses and applies `CREATE` or `MERGE` statements from the custom Cypher query input to an **in-memory graph representation**.
    * This feature allows users to build upon or modify the graph data derived from PDFs.
    * **Note**: This does *not* connect to an external Neo4j database. It simulates Cypher execution on the internal data structure.
* **Accumulative Graph Data**: Each "Create Graph Data" operation or "Run Custom Cypher" execution adds to or merges with the existing in-memory graph data, allowing for the aggregation of information from multiple PDFs or queries.
* **Save Graph to CSV**: Export the current in-memory graph (nodes and relationships with their attributes) to two CSV files: `nodes.csv` and `relationships.csv`.
* **Load Graph from CSV**: Load graph data from previously saved `nodes.csv` and `relationships.csv` files, overwriting the current in-memory graph.
* **Reset Graph Data**: Clears the current in-memory graph data, the LLM-generated Cypher display, and the custom Cypher input area.

### 4. General Features
* **Theme Customization**:
    * Choose between "Default" (light mode) and "Matrix" (dark mode with green text) themes via a "Themes" menu.
    * The application's appearance updates dynamically.
* **Obfuscated Path Display**: The selected PDF folder path in the UI is partially obfuscated for privacy (e.g., `C:\Users\...\research files`).
* **Cross-Platform Compatibility**: Built with Tkinter, aiming for compatibility across Windows, macOS, and Linux.

## Setup & Installation

1.  **Python**: Ensure you have Python 3.8 or newer installed.
2.  **Dependencies**: Install the required Python libraries using pip:
    ```bash
    pip install PyMuPDF openai google-generativeai reportlab
    ```
    *(Note: `networkx` and `matplotlib` were part of a previous visualization feature but are not currently required for the core functionality described here. If you re-enable visualization, they would be needed.)*

## How to Run

1.  Save the script as a Python file (e.g., `pdf_analyzer_app.py`).
2.  Open your terminal or command prompt.
3.  Navigate to the directory where you saved the file.
4.  Run the script using:
    ```bash
    python pdf_analyzer_app.py
    ```

## Usage Guide

1.  **PDF Viewer Tab**:
    * Click "Browse Research Folder" to select your PDF directory.
    * Select a PDF from the list on the left to view it on the right.
    * Use the navigation and zoom buttons as needed.
2.  **LLM Analyzer & Chat Tab**:
    * Choose your desired LLM (OpenAI or Google Gemini) from the "Select LLM" dropdown.
    * Enter your API key for the chosen service in the "API Key" field.
    * Select a PDF from the "PDF for Analysis" dropdown (this list is populated from the PDF Viewer tab).
    * Click "Summarize PDF". The summary will appear in the "PDF Summary" box.
    * Once a summary is generated, you can type questions or follow-up prompts related to the PDF in the chat input field at the bottom and click "Send" or press Enter.
    * To save the chat, click "Export Chat to PDF".
3.  **Graph Database Tab**:
    * Ensure a PDF has been processed (e.g., summarized) in the "LLM Analyzer & Chat" tab to load its text content.
    * Click "Create Graph Data". The LLM will generate Cypher queries.
        * The raw Cypher output will appear in the "LLM Generated Graph Data" text area (toggle visibility with the checkbox).
        * This Cypher will also populate the "Custom Cypher Query" box.
        * The application will automatically attempt to parse this Cypher and update its internal graph data structure.
    * You can manually edit the Cypher in the "Custom Cypher Query" box or paste your own `CREATE`/`MERGE` statements.
    * Click "Run Custom Cypher" to apply these changes to the in-memory graph.
    * Use "Save Graph to CSV" to export the current accumulated graph data.
    * Use "Load Graph from CSV" to load previously saved graph data.
    * Use "Reset Graph Data" (on this tab or the visualization tab) to clear the current in-memory graph.
4.  **Themes Menu**:
    * Click "Themes" in the menu bar and select "Default" or "Matrix" to change the application's appearance.



## Future Enhancements (Potential)

* Direct integration with Neo4j or other graph databases.
* Interactive graph visualization (re-integration of a more advanced visualization library).
* Advanced PDF processing, such as chunking for very long documents or section-specific analysis.
* Implementation of a GraphQL API layer for querying the graph data.

## Contributing

Contributions are welcome! Please feel free to fork the repository, make your changes, and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.

## License

(Specify your license here, e.g., MIT, Apache 2.0, etc.)
