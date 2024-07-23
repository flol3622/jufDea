import json
import os
import sys

import fitz
import pikepdf
from fpdf import FPDF
from PyQt6 import QtWidgets, uic
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QLineEdit,
    QMessageBox,
)

base_dir = os.path.dirname(os.path.abspath(__file__))

class Ui(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__()
        uic.loadUi(os.path.join(base_dir, "GUI/sidePicturesWidget.ui"), self)
        self.parent = parent
        self.updatePreviews()
    
    def updatePreviews(self):
        placeholders = [self.label_5, self.label_6, self.label_7, self.label_8]
        for i, path in enumerate(self.parent.sideImages):
            print(path)
            if path:
                image = QImage(path)
                pixmap = QPixmap.fromImage(image)
                placeholders[i].setPixmap(pixmap)
            else:
                placeholders[i].clear()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Ui()
    window.setWindowTitle("Upload new images")  # set the window title
    window.show()
    sys.exit(app.exec())
