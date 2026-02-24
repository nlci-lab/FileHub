import sys
import os
import fitz  # PyMuPDF
from PIL import Image  # Pillow for image conversion
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QPushButton, QLabel, QFileDialog, QMessageBox, QProgressBar, 
    QListWidget, QGroupBox, QComboBox, QSpinBox, QCheckBox, 
    QTextEdit, QSplitter, QAbstractItemView
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont, QColor, QPalette, QDragEnterEvent, QDropEvent

# --- WORKER THREAD FOR UNIVERSAL PROCESSING ---
class UniversalWorker(QThread):
    progress_signal = pyqtSignal(int)
    log_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()
    
    def __init__(self, file_list, output_folder, settings):
        super().__init__()
        self.file_list = file_list
        self.output_folder = output_folder
        self.fmt = settings['format'].lower()  # png, jpg, pdf, etc.
        self.dpi = settings['dpi']
        self.alpha = settings['alpha']
        self.grayscale = settings['grayscale']
        self.cancel_requested = False

    def run(self):
        total_files = len(self.file_list)
        if total_files == 0:
            self.finished_signal.emit()
            return

        # Estimate total work (just file count for simplicity in mixed batches)
        processed_count = 0
        
        for f_idx, input_path in enumerate(self.file_list):
            if self.cancel_requested:
                break
            
            filename = os.path.basename(input_path)
            self.log_signal.emit(f"Processing: {filename}...")
            
            try:
                # Detect Input Type
                ext = os.path.splitext(filename)[1].lower()
                is_pdf_input = ext == '.pdf'
                
                # --- LOGIC A: PDF INPUT ---
                if is_pdf_input:
                    self.process_pdf_input(input_path, filename)
                
                # --- LOGIC B: IMAGE INPUT ---
                else:
                    self.process_image_input(input_path, filename)

            except Exception as e:
                self.log_signal.emit(f"Error processing {filename}: {str(e)}")

            processed_count += 1
            percent = int((processed_count / total_files) * 100)
            self.progress_signal.emit(percent)

        self.finished_signal.emit()

    def process_pdf_input(self, input_path, filename):
        """ Handles PDF -> Image OR PDF -> PDF (Split/Refine) """
        doc = fitz.open(input_path)
        base_name = os.path.splitext(filename)[0]
        
        # Calculate Zoom for DPI
        zoom = self.dpi / 72.0
        mat = fitz.Matrix(zoom, zoom)

        for i in range(len(doc)):
            if self.cancel_requested: break
            
            page = doc.load_page(i)
            
            # If target is PDF (PDF -> PDF Split/Rasterize)
            if self.fmt == 'pdf':
                # This creates a new single-page PDF for every page in original
                new_doc = fitz.open()
                new_doc.insert_pdf(doc, from_page=i, to_page=i)
                out_name = f"{base_name}_page_{i+1:03d}.pdf"
                new_doc.save(os.path.join(self.output_folder, out_name))
                new_doc.close()
            
            else:
                # PDF -> Image
                pix = page.get_pixmap(matrix=mat, alpha=self.alpha)
                
                # Grayscale Handling
                if self.grayscale and self.fmt != "png":
                    pix = fitz.Pixmap(fitz.csGRAY, pix)
                
                out_name = f"{base_name}_page_{i+1:03d}.{self.fmt}"
                save_path = os.path.join(self.output_folder, out_name)
                pix.save(save_path)
        
        doc.close()
        self.log_signal.emit(f"Converted PDF: {filename}")

    def process_image_input(self, input_path, filename):
        """ Handles Image -> Image OR Image -> PDF """
        img = Image.open(input_path)
        base_name = os.path.splitext(filename)[0]
        
        # Apply Grayscale if requested
        if self.grayscale:
            img = img.convert("L") # L mode is grayscale

        # --- IMAGE -> PDF ---
        if self.fmt == 'pdf':
            # Save image as PDF
            save_path = os.path.join(self.output_folder, f"{base_name}.pdf")
            if img.mode == 'RGBA':
                img = img.convert('RGB') # PDF doesn't support transparency well in this method
            img.save(save_path, "PDF", resolution=self.dpi)
            self.log_signal.emit(f"Created PDF from Image: {filename}")
        
        # --- IMAGE -> IMAGE ---
        else:
            save_path = os.path.join(self.output_folder, f"{base_name}.{self.fmt}")
            
            # Handle JPG transparency issue (JPG supports no Alpha)
            if self.fmt in ['jpg', 'jpeg', 'bmp'] and img.mode in ('RGBA', 'LA'):
                # Paste on white background
                background = Image.new(img.mode[:-1], img.size, (255, 255, 255))
                background.paste(img, img.split()[-1])
                img = background.convert('RGB')
            
            img.save(save_path, quality=95, dpi=(self.dpi, self.dpi))
            self.log_signal.emit(f"Transcoded Image: {filename}")

    def stop(self):
        self.cancel_requested = True

# --- DRAG & DROP WIDGET ---
class FileListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setAlternatingRowColors(True)
        self.setStyleSheet("""
            QListWidget {
                border: 2px dashed #555;
                border-radius: 5px;
                background-color: #2b2b2b;
                color: #ddd;
                font-size: 13px;
                padding: 5px;
            }
            QListWidget::item { padding: 5px; }
            QListWidget::item:selected { background-color: #0078d7; }
        """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        valid_exts = ['.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.bmp', '.webp']
        for f in files:
            _, ext = os.path.splitext(f)
            if ext.lower() in valid_exts:
                self.addItem(f)

# --- MAIN APP ---
class UltimateConverterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ultimate Universal Converter")
        self.resize(1000, 650)
        self.setAcceptDrops(True)
        self.apply_dark_theme()
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        self.layout = QVBoxLayout(main_widget)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)
        self.init_ui()

    def apply_dark_theme(self):
        app.setStyle("Fusion")
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.ToolTipBase, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.ToolTipText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        palette.setColor(QPalette.ColorRole.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.black)
        app.setPalette(palette)

    def init_ui(self):
        # Header
        header = QLabel("Universal Batch Converter")
        header.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header.setStyleSheet("color: #00bcd4;")
        self.layout.addWidget(header)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # --- LEFT: FILES ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0,0,0,0)
        
        lbl_files = QLabel("Input Files (PDF, PNG, JPG, WEBP...):")
        lbl_files.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        left_layout.addWidget(lbl_files)

        self.file_list_widget = FileListWidget()
        left_layout.addWidget(self.file_list_widget)

        btn_layout = QHBoxLayout()
        self.btn_add = QPushButton("Add Files")
        self.btn_clear = QPushButton("Clear")
        self.btn_add.clicked.connect(self.add_files)
        self.btn_clear.clicked.connect(self.file_list_widget.clear)
        btn_layout.addWidget(self.btn_add)
        btn_layout.addWidget(self.btn_clear)
        left_layout.addLayout(btn_layout)
        splitter.addWidget(left_widget)

        # --- RIGHT: SETTINGS ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10,0,0,0)

        # Group Box
        grp = QGroupBox("Target Settings")
        grp.setStyleSheet("font-weight: bold; border: 1px solid #555; margin-top: 10px;")
        sets_layout = QVBoxLayout()

        # Format
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Output Format:"))
        self.combo_fmt = QComboBox()
        self.combo_fmt.addItems(["png", "jpg", "jpeg", "pdf", "tiff", "bmp", "webp"])
        row1.addWidget(self.combo_fmt)
        sets_layout.addLayout(row1)

        # DPI
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("DPI / Quality:"))
        self.spin_dpi = QSpinBox()
        self.spin_dpi.setRange(72, 1200)
        self.spin_dpi.setValue(150)
        self.spin_dpi.setSingleStep(72)
        row2.addWidget(self.spin_dpi)
        sets_layout.addLayout(row2)

        # Toggles
        self.chk_alpha = QCheckBox("Preserve Transparency (PNG/WEBP)")
        self.chk_alpha.setChecked(True)
        self.chk_gray = QCheckBox("Convert to Grayscale")
        sets_layout.addWidget(self.chk_alpha)
        sets_layout.addWidget(self.chk_gray)
        
        # Output Path
        sets_layout.addSpacing(10)
        path_layout = QHBoxLayout()
        self.txt_out = QLabel("Not Selected")
        self.txt_out.setStyleSheet("color: #aaa; border: 1px solid #444; padding: 5px;")
        self.btn_browse = QPushButton("Select Output Folder")
        self.btn_browse.clicked.connect(self.select_output)
        path_layout.addWidget(self.txt_out)
        path_layout.addWidget(self.btn_browse)
        sets_layout.addLayout(path_layout)
        
        grp.setLayout(sets_layout)
        right_layout.addWidget(grp)

        # Logs
        lbl_log = QLabel("Activity Log:")
        lbl_log.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        right_layout.addWidget(lbl_log)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setStyleSheet("background-color: #1e1e1e; color: #00ff00; font-family: Consolas;")
        right_layout.addWidget(self.log_box)

        splitter.addWidget(right_widget)
        splitter.setSizes([400, 500])
        self.layout.addWidget(splitter)

        # --- FOOTER ---
        self.progress = QProgressBar()
        self.progress.setStyleSheet("QProgressBar { border: 1px solid #555; text-align: center; height: 25px; } QProgressBar::chunk { background-color: #0078d7; }")
        self.layout.addWidget(self.progress)

        self.btn_start = QPushButton("START BATCH PROCESS")
        self.btn_start.setMinimumHeight(45)
        self.btn_start.setStyleSheet("QPushButton { background-color: #0078d7; color: white; font-weight: bold; border-radius: 5px; font-size: 14px; } QPushButton:hover { background-color: #0063b1; }")
        self.btn_start.clicked.connect(self.start_process)
        self.layout.addWidget(self.btn_start)

    # --- LOGIC ---
    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select Files", "", "All Supported (*.pdf *.png *.jpg *.jpeg *.tiff *.bmp *.webp)")
        if files:
            self.file_list_widget.addItems(files)

    def select_output(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            self.txt_out.setText(folder)

    def log(self, msg):
        self.log_box.append(f">> {msg}")
        self.log_box.verticalScrollBar().setValue(self.log_box.verticalScrollBar().maximum())

    def start_process(self):
        if self.file_list_widget.count() == 0:
            QMessageBox.warning(self, "Error", "No files added.")
            return
        if self.txt_out.text() == "Not Selected":
            QMessageBox.warning(self, "Error", "Select output folder.")
            return

        files = [self.file_list_widget.item(i).text() for i in range(self.file_list_widget.count())]
        settings = {
            'format': self.combo_fmt.currentText(),
            'dpi': self.spin_dpi.value(),
            'alpha': self.chk_alpha.isChecked(),
            'grayscale': self.chk_gray.isChecked()
        }

        self.btn_start.setEnabled(False)
        self.log("Starting universal batch...")
        self.progress.setValue(0)

        self.worker = UniversalWorker(files, self.txt_out.text(), settings)
        self.worker.progress_signal.connect(self.progress.setValue)
        self.worker.log_signal.connect(self.log)
        self.worker.finished_signal.connect(self.on_finished)
        self.worker.start()

    def on_finished(self):
        self.btn_start.setEnabled(True)
        self.progress.setValue(100)
        self.log("Process Complete.")
        QMessageBox.information(self, "Success", "All tasks finished!")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UltimateConverterApp()
    window.show()
    sys.exit(app.exec())