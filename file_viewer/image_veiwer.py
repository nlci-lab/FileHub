import sys
import fitz  # PyMuPDF for PDF rendering
from PyQt6.QtWidgets import (QApplication, QWidget, QLabel, QScrollArea,
                             QPushButton, QVBoxLayout, QHBoxLayout, 
                             QFileDialog, QMessageBox)
from PyQt6.QtGui import QPixmap, QImage
from PyQt6.QtCore import Qt

# --- Global State Variables ---
# We use globals so our functions can share data without a class
current_pdf = None
current_page = 0

# --- Global UI Elements ---
# These are initialized in main() so functions can modify them
window = None
image_label = None
prev_btn = None
next_btn = None

# --- Application Functions ---

def open_file():
    """Opens a file dialog to select an image or PDF."""
    global current_pdf
    
    file_name, _ = QFileDialog.getOpenFileName(
        window, "Open File", "", "Images/PDFs (*.png *.jpg *.jpeg *.bmp *.pdf)"
    )
    if not file_name:
        return

    if file_name.lower().endswith('.pdf'):
        load_pdf(file_name)
    else:
        load_image(file_name)

def load_image(path):
    """Loads and displays a standard image file."""
    global current_pdf
    current_pdf = None  # Reset PDF state
    
    # Disable pagination since it's a single image
    prev_btn.setEnabled(False)
    next_btn.setEnabled(False)
    window.setWindowTitle(f"Viewer - {path}")

    pixmap = QPixmap(path)
    if pixmap.isNull():
        QMessageBox.warning(window, "Error", "Failed to load image.")
        return

    display_pixmap(pixmap)

def load_pdf(path):
    """Loads a PDF document and displays the first page."""
    global current_pdf, current_page
    try:
        current_pdf = fitz.open(path)
        current_page = 0
        update_pdf_view()
        
        # Enable pagination buttons
        prev_btn.setEnabled(True)
        next_btn.setEnabled(True)
    except Exception as e:
        QMessageBox.warning(window, "Error", f"Failed to load PDF: {e}")

def update_pdf_view():
    """Renders the current PDF page into a QPixmap and displays it."""
    global current_pdf, current_page
    if not current_pdf:
        return

    # Load the specific page using PyMuPDF
    page = current_pdf.load_page(current_page)
    
    # Render page to an image
    pix = page.get_pixmap()
    fmt = QImage.Format.Format_RGBA8888 if pix.alpha else QImage.Format.Format_RGB888
    
    # Convert PyMuPDF pixmap to PyQt QImage, then to QPixmap
    qimg = QImage(pix.samples, pix.width, pix.height, pix.stride, fmt)
    pixmap = QPixmap.fromImage(qimg)
    
    display_pixmap(pixmap)
    window.setWindowTitle(f"Viewer - Page {current_page + 1} of {len(current_pdf)}")

def next_page():
    """Advances to the next PDF page."""
    global current_pdf, current_page
    if current_pdf and current_page < len(current_pdf) - 1:
        current_page += 1
        update_pdf_view()

def prev_page():
    """Goes back to the previous PDF page."""
    global current_pdf, current_page
    if current_pdf and current_page > 0:
        current_page -= 1
        update_pdf_view()

def display_pixmap(pixmap):
    """Sets the pixmap to the label and resizes it accordingly."""
    image_label.setPixmap(pixmap)
    image_label.resize(pixmap.size())

# --- Main Setup Function ---

def main():
    """Initializes the PyQt application and builds the UI."""
    global window, image_label, prev_btn, next_btn
    
    app = QApplication(sys.argv)
    
    # Main Window Setup
    window = QWidget()
    window.setWindowTitle("Basic Image and PDF Viewer (Procedural)")
    window.setGeometry(100, 100, 800, 600)
    
    # Main Layout
    layout = QVBoxLayout(window)
    
    # Controls Layout (Top bar)
    controls_layout = QHBoxLayout()
    
    open_btn = QPushButton("Open File")
    open_btn.clicked.connect(open_file)
    
    prev_btn = QPushButton("Previous Page")
    prev_btn.clicked.connect(prev_page)
    prev_btn.setEnabled(False)
    
    next_btn = QPushButton("Next Page")
    next_btn.clicked.connect(next_page)
    next_btn.setEnabled(False)
    
    controls_layout.addWidget(open_btn)
    controls_layout.addWidget(prev_btn)
    controls_layout.addWidget(next_btn)
    layout.addLayout(controls_layout)
    
    # Scroll Area and Image Label (Display area)
    scroll_area = QScrollArea()
    image_label = QLabel()
    image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    scroll_area.setWidget(image_label)
    scroll_area.setWidgetResizable(True)
    layout.addWidget(scroll_area)
    
    window.show()
    sys.exit(app.exec())

# --- Execution ---
if __name__ == '__main__':
    main()