from ConverterAppGUI import ConverterAppGUI
from PySide6.QtWidgets import QApplication
import sys


if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Options - ["windows", "windowsvista", "fusion", "macos"]
    app.setStyle("fusion") 
    
    window = ConverterAppGUI()
    window.show()
    sys.exit(app.exec())