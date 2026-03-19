import sys
import os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QFormLayout, QLineEdit, QPushButton, QSpinBox, QDoubleSpinBox, 
    QCheckBox, QGroupBox, QFileDialog, QMessageBox, QLabel, QFontComboBox
)
from PySide6.QtCore import Qt
from DataConverter import DataConverter

class ConverterAppGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Generator Prac Dyplomowych (Excel -> Word/PDF)")
        self.resize(600, 650)
        
        self.converter = DataConverter('settings.json')
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)

        # Section Wybór Plików
        file_group = QGroupBox("Wybór plików")
        file_layout = QFormLayout()

        # Button wybór pliku Excel
        self.excel_path_edit = QLineEdit()
        self.btn_browse_excel = QPushButton("Przeglądaj...")
        self.btn_browse_excel.clicked.connect(self.browse_excel)
        excel_layout = QHBoxLayout()
        excel_layout.addWidget(self.excel_path_edit)
        excel_layout.addWidget(self.btn_browse_excel)
        file_layout.addRow("Plik Excel (.xlsx):", excel_layout)

        # Button wybór pliku Word
        self.word_path_edit = QLineEdit()
        self.btn_browse_word = QPushButton("Przeglądaj...")
        self.btn_browse_word.clicked.connect(self.browse_word)
        word_layout = QHBoxLayout()
        word_layout.addWidget(self.word_path_edit)
        word_layout.addWidget(self.btn_browse_word)
        file_layout.addRow("Zapisz Word jako (.docx):", word_layout)

        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)

        # Section Ustawienia Dokumentu
        settings_group = QGroupBox("Ustawienia Dokumentu")
        settings_layout = QFormLayout()

        self.title_edit = QLineEdit()
        self.font_combo = QFontComboBox()
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(5, 72)
        
        self.landscape_check = QCheckBox("Orientacja pozioma")
        
        self.line_spacing_spin = QDoubleSpinBox()
        self.line_spacing_spin.setRange(0.5, 3.0)
        self.line_spacing_spin.setSingleStep(0.1)

        self.columns_order_edit = QLineEdit()
        self.columns_order_edit.setPlaceholderText("np. Imię, Nazwisko, Temat (zostaw puste dla domyślnych)")

        settings_layout.addRow("Tytuł:", self.title_edit)
        settings_layout.addRow("Czcionka:", self.font_combo)
        settings_layout.addRow("Rozmiar czcionki:", self.font_size_spin)
        settings_layout.addRow("Interlinia:", self.line_spacing_spin)
        settings_layout.addRow("Kolejność kolumn:", self.columns_order_edit)
        settings_layout.addRow("", self.landscape_check)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        # Section Marginesy
        margins_group = QGroupBox("Marginesy (cm)")
        margins_layout = QHBoxLayout()

        self.margin_top = QDoubleSpinBox(); self.margin_top.setRange(0, 10)
        self.margin_bottom = QDoubleSpinBox(); self.margin_bottom.setRange(0, 10)
        self.margin_left = QDoubleSpinBox(); self.margin_left.setRange(0, 10)
        self.margin_right = QDoubleSpinBox(); self.margin_right.setRange(0, 10)

        margins_layout.addWidget(QLabel("Góra:"))
        margins_layout.addWidget(self.margin_top)
        margins_layout.addWidget(QLabel("Dół:"))
        margins_layout.addWidget(self.margin_bottom)
        margins_layout.addWidget(QLabel("Lewy:"))
        margins_layout.addWidget(self.margin_left)
        margins_layout.addWidget(QLabel("Prawy:"))
        margins_layout.addWidget(self.margin_right)

        margins_group.setLayout(margins_layout)
        main_layout.addWidget(margins_group)

        # Section Przyciski
        action_layout = QHBoxLayout()
        
        self.btn_save_settings = QPushButton("Zapisz Ustawienia")
        self.btn_save_settings.clicked.connect(self.save_current_settings)
        
        self.btn_convert_docx = QPushButton("Konwertuj do Word (DOCX)")
        self.btn_convert_docx.setStyleSheet("background-color: #2b579a; color: white; font-weight: bold; padding: 10px;")
        self.btn_convert_docx.clicked.connect(self.run_conversion_docx)

        self.btn_convert_pdf = QPushButton("Konwertuj DOCX do PDF")
        self.btn_convert_pdf.setStyleSheet("background-color: #b30b00; color: white; font-weight: bold; padding: 10px;")
        self.btn_convert_pdf.clicked.connect(self.run_conversion_pdf)

        action_layout.addWidget(self.btn_save_settings)
        action_layout.addWidget(self.btn_convert_docx)
        action_layout.addWidget(self.btn_convert_pdf)
        
        main_layout.addLayout(action_layout)

        # GUI loading settin
        self.load_settings_to_gui()

    def browse_excel(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik Excel", "", "Excel Files (*.xlsx *.xls)")
        if file_path:
            self.excel_path_edit.setText(file_path)
            # Auto fill word path if empty
            if not self.word_path_edit.text():
                word_path = os.path.splitext(file_path)[0] + ".docx"
                self.word_path_edit.setText(word_path)

    def browse_word(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Zapisz jako Word", "", "Word Files (*.docx)")
        if file_path:
            self.word_path_edit.setText(file_path)

    def load_settings_to_gui(self):
        """Pobiera dane z self.converter.settings i wrzuca do interfejsu."""
        s = self.converter.settings
        
        self.title_edit.setText(s.get("title", ""))
        self.font_combo.setCurrentText(s.get("font_name", "Courier New"))
        self.font_size_spin.setValue(s.get("font_size", 9))
        self.line_spacing_spin.setValue(s.get("line_spacing", 1.0))
        self.landscape_check.setChecked(s.get("landscape", True))
        
        cols = s.get("columns_order", [])
        self.columns_order_edit.setText(", ".join(cols))

        margins = s.get("margins_cm", {})
        self.margin_top.setValue(margins.get("top", 1.5))
        self.margin_bottom.setValue(margins.get("bottom", 1.5))
        self.margin_left.setValue(margins.get("left", 1.5))
        self.margin_right.setValue(margins.get("right", 1.5))

    def collect_settings_from_gui(self):
        """Zbiera dane z interfejsu i formatuje je pod JSON/klasę."""
        cols_text = self.columns_order_edit.text().strip()
        columns_order = [c.strip() for c in cols_text.split(",")] if cols_text else []

        return {
            "title": self.title_edit.text(),
            "font_name": self.font_combo.currentText(),
            "font_size": self.font_size_spin.value(),
            "page_size": "A4", # hardcoded rght now, but can be implemented in GUI
            "landscape": self.landscape_check.isChecked(),
            "columns_order": columns_order,
            "margins_cm": {
                "top": self.margin_top.value(),
                "bottom": self.margin_bottom.value(),
                "left": self.margin_left.value(),
                "right": self.margin_right.value()
            },
            "line_spacing": self.line_spacing_spin.value()
        }

    def save_current_settings(self):
        new_settings = self.collect_settings_from_gui()
        self.converter.save_settings(new_settings)
        QMessageBox.information(self, "Sukces", "Ustawienia zostały zapisane do pliku konfiguracyjnego.")

    def run_conversion_docx(self):
        excel_path = self.excel_path_edit.text()
        word_path = self.word_path_edit.text()

        if not os.path.exists(excel_path):
            QMessageBox.warning(self, "Błąd", "Wybierz poprawny plik Excel!")
            return
        if not word_path:
            QMessageBox.warning(self, "Błąd", "Podaj ścieżkę zapisu pliku Word!")
            return

        # Setting update before generate
        self.converter.settings = self.collect_settings_from_gui()
        self.converter.save_settings(self.converter.settings) # Option save

        try:
            self.converter.convert_excel_to_docx(excel_path, word_path)
            QMessageBox.information(self, "Sukces", f"Utworzono plik DOCX:\n{word_path}")
        except Exception as e:
            QMessageBox.critical(self, "Błąd krytyczny", f"Wystąpił błąd podczas konwersji:\n{str(e)}")

    def run_conversion_pdf(self):
        word_path = self.word_path_edit.text()
        
        if not os.path.exists(word_path):
            QMessageBox.warning(self, "Błąd", "Nie znaleziono pliku Word! Zrób najpierw konwersję do DOCX lub wybierz istniejący plik.")
            return

        pdf_path = os.path.splitext(word_path)[0] + ".pdf"

        try:
            self.converter.convert_docx_to_pdf(word_path, pdf_path)
            QMessageBox.information(self, "Sukces", f"Utworzono plik PDF:\n{pdf_path}")
        except Exception as e:
            QMessageBox.critical(self, "Błąd krytyczny", f"Wystąpił błąd podczas konwersji PDF:\n{str(e)}")
