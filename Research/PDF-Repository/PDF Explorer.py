import os
import tkinter as tk
from tkinter import filedialog, Listbox, Scrollbar
from PIL import Image, ImageTk
import fitz  # PyMuPDF

class PDFViewer:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple PDF Viewer")

        # Select folder button
        self.btn_load_folder = tk.Button(root, text="Load PDF Folder", command=self.load_folder)
        self.btn_load_folder.pack()

        # Listbox to show PDF files
        self.listbox = Listbox(root, width=50)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.listbox.bind("<<ListboxSelect>>", self.display_pdf)

        # Scrollbar for the listbox
        self.scrollbar = Scrollbar(root)
        self.scrollbar.pack(side=tk.LEFT, fill=tk.Y)
        self.listbox.config(yscrollcommand=self.scrollbar.set)
        self.scrollbar.config(command=self.listbox.yview)

        # Label to show PDF page
        self.pdf_canvas = tk.Label(root)
        self.pdf_canvas.pack(side=tk.RIGHT, expand=True)

        self.pdf_folder = ""
        self.pdf_files = []

    def load_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return
        self.pdf_folder = folder
        self.pdf_files = [f for f in os.listdir(folder) if f.lower().endswith(".pdf")]
        self.listbox.delete(0, tk.END)
        for file in self.pdf_files:
            self.listbox.insert(tk.END, file)

    def display_pdf(self, event):
        selection = event.widget.curselection()
        if not selection:
            return
        index = selection[0]
        pdf_path = os.path.join(self.pdf_folder, self.pdf_files[index])
        doc = fitz.open(pdf_path)

        # Get first page and render to an image
        page = doc.load_page(0)
        pix = page.get_pixmap()
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

        # Resize to fit window (optional)
        image.thumbnail((600, 800))

        self.tk_image = ImageTk.PhotoImage(image)
        self.pdf_canvas.config(image=self.tk_image)

if __name__ == "__main__":
    root = tk.Tk()
    viewer = PDFViewer(root)
    root.mainloop()
