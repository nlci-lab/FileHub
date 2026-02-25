import tkinter as tk
from tkinter import filedialog, messagebox
import zipfile
import os

def compress_files():
    """Opens a dialog to select files, then asks where to save the .zip archive."""
    # 1. Select files to compress
    files_to_zip = filedialog.askopenfilenames(
        title="Select files to compress"
    )
    
    if not files_to_zip:
        return # User cancelled the selection

    # 2. Choose where to save the .zip file
    save_path = filedialog.asksaveasfilename(
        title="Save compressed archive as",
        defaultextension=".zip",
        filetypes=[("ZIP Archive", "*.zip")]
    )
    
    if not save_path:
        return # User cancelled the save prompt

    # 3. Compress the files
    try:
        with zipfile.ZipFile(save_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file in files_to_zip:
                zipf.write(file, arcname=os.path.basename(file))
        
        # Show success message
        messagebox.showinfo("Success", f"Files successfully compressed to:\n{save_path}")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred during compression:\n{str(e)}")

def extract_files():
    """Opens a dialog to select a .zip file, then asks where to extract it."""
    # 1. Select the .zip file
    zip_path = filedialog.askopenfilename(
        title="Select archive to extract",
        filetypes=[("ZIP Archive", "*.zip")]
    )
    
    if not zip_path:
        return # User cancelled the selection

    # 2. Choose where to extract the files
    extract_folder = filedialog.askdirectory(
        title="Select folder to extract files into"
    )
    
    if not extract_folder:
        return # User cancelled the folder selection

    # 3. Extract the files
    try:
        with zipfile.ZipFile(zip_path, 'r') as zipf:
            zipf.extractall(extract_folder)
            
        # Show success message
        messagebox.showinfo("Success", f"Files successfully extracted to:\n{extract_folder}")
    except Exception as e:
        messagebox.showerror("Error", f"An error occurred during extraction:\n{str(e)}")

# ==========================================
# Application Window Setup
# ==========================================
# Initialize the main window
root = tk.Tk()
root.title("Python File Compressor")
root.geometry("350x200")
root.eval('tk::PlaceWindow . center') # Centers the window on the screen

# Add a title label
title_label = tk.Label(root, text="File Compressor & Extractor", font=("Helvetica", 14, "bold"))
title_label.pack(pady=20)

# Add the Compress button
btn_compress = tk.Button(root, text="Compress Files", width=20, command=compress_files, bg="#e0e0e0")
btn_compress.pack(pady=10)

# Add the Extract button
btn_extract = tk.Button(root, text="Extract Archive", width=20, command=extract_files, bg="#e0e0e0")
btn_extract.pack(pady=10)

# Run the application
if __name__ == "__main__":
    root.mainloop()