# pip install pymupdf docx2pdf pillow



from tkinter import *
from tkinter import filedialog, messagebox
import fitz  # PyMuPDF
from docx2pdf import convert as docx_convert
import os

root = Tk()
root.title("FileHub - NLCI")
root.geometry("400x250")

selected_file = ""

def select_file():
    global selected_file
    selected_file = filedialog.askopenfilename(
        filetypes=[("Documents", "*.pdf *.docx")]
    )
    status.set(selected_file)

def pdf_to_img(path):
    doc = fitz.open(path)
    base = os.path.splitext(path)[0]

    for i in range(len(doc)):
        page = doc.load_page(i)
        pix = page.get_pixmap()
        pix.save(f"{base}_page{i+1}.png")

def docx_to_img(path):
    pdf_path = path.replace(".docx", ".pdf")
    docx_convert(path, pdf_path)
    pdf_to_img(pdf_path)

def convert():
    if not selected_file:
        messagebox.showerror("Error", "Select a file first")
        return

    if selected_file.endswith(".pdf"):
        pdf_to_img(selected_file)

    elif selected_file.endswith(".docx"):
        docx_to_img(selected_file)

    else:
        messagebox.showerror("Error", "Unsupported file")
        return

    status.set("Conversion Completed!")

status = StringVar()

Button(root, text="Select Word/PDF", command=select_file).pack(pady=10)
Button(root, text="Convert to Image", command=convert).pack(pady=10)
Label(root, textvariable=status, wraplength=350).pack()

root.mainloop()