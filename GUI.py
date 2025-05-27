# Standard library imports
import os
import sys
import json

# Third-party imports
import fitz  # PyMuPDF
import pandas as pd
from PyQt6 import QtGui
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QLineEdit,
    QComboBox,
    QPushButton,
    QLabel,
    QGroupBox,
    QHeaderView,
    QFileDialog,
    QTreeView,
    QMessageBox,
)

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

# Internal imports
from pdf_utils import MyPDF
from Settings import JsonModel


class MainWindow(QMainWindow):
    """Main window for the PDF Generator application."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PDF Generator")
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self._load_potloden_images()
        self.initUI()
        self.newRow()

    def _load_potloden_images(self):
        """Load images from the folder 'GUI/images/potloden'."""
        self.backgroundImageFolder = os.path.join(
            self.base_dir, "GUI", "images", "potloden"
        )
        self._scenes = []
        self._colors = []
        self._potloden_map = {}
        if os.path.exists(self.backgroundImageFolder):
            for f_name in os.listdir(self.backgroundImageFolder):
                if f_name.endswith(".jpg"):
                    try:
                        scene, color = os.path.splitext(f_name)[0].split("-")
                        if scene not in self._scenes:
                            self._scenes.append(scene)
                        if color not in self._colors:
                            self._colors.append(color)
                        self._potloden_map[(scene, color)] = os.path.join(
                            self.backgroundImageFolder, f_name
                        )
                    except Exception:
                        continue
        if not self._scenes:
            self._scenes = ["default"]
        if not self._colors:
            self._colors = ["default"]
        if not self._potloden_map:
            self._potloden_map = {
                ("default", "default"): os.path.join(
                    self.backgroundImageFolder, "default.jpg"
                )
            }

    def initUI(self):
        """Initialize the user interface components."""
        central = QWidget()
        self.setCentralWidget(central)
        mainLayout = QHBoxLayout(central)

        # Left side: Data GroupBox
        dataGroup = QGroupBox("Data")
        dataLayout = QVBoxLayout(dataGroup)

        # Increase column count to 6 with the new "Family Name" column
        self.tableWidget = QTableWidget(0, 6)
        self.tableWidget.setHorizontalHeaderLabels(
            ["Name", "Family Name", "Color", "Scene", "Birth date", "Group"]
        )
        self.tableWidget.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.tableWidget.setMinimumWidth(600)  # make table a bit wider
        dataLayout.addWidget(self.tableWidget)

        btnLayout = QHBoxLayout()
        self.addRowButton = QPushButton("Add Row")
        self.removeRowButton = QPushButton("Remove Row")
        btnLayout.addWidget(self.addRowButton)
        btnLayout.addWidget(self.removeRowButton)
        dataLayout.addLayout(btnLayout)

        self.savePDFButton = QPushButton("Save PDF")
        dataLayout.addWidget(self.savePDFButton)
        mainLayout.addWidget(dataGroup)

        # Right side: Preview GroupBox
        previewGroup = QGroupBox("Preview")
        previewLayout = QVBoxLayout(previewGroup)
        self.previewLabel = QLabel("PDF Preview")
        self.previewLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.previewLabel.setFixedSize(842, 595)
        previewLayout.addWidget(self.previewLabel)
        mainLayout.addWidget(previewGroup)

        # Menu for Settings
        settingsAction = QAction("Settings", self)
        settingsAction.triggered.connect(self.openSettings)
        menubar = self.menuBar()
        advancedMenu = menubar.addMenu("Advanced")
        advancedMenu.addAction(settingsAction)

        # Connect signals
        self.addRowButton.clicked.connect(self.addRow)
        self.removeRowButton.clicked.connect(self.removeRow)
        self.savePDFButton.clicked.connect(self.save_pdf)
        self.tableWidget.cellChanged.connect(self.update_preview)
        self.tableWidget.cellClicked.connect(
            self.update_preview
        )  # update preview when clicking a row

    def newRow(self):
        """Insert a new row with default values and setup event filters."""
        rowPosition = self.tableWidget.rowCount()
        self.tableWidget.insertRow(rowPosition)

        # Name column
        nameEdit = QLineEdit("name")
        nameEdit.textChanged.connect(self.update_preview)
        nameEdit.installEventFilter(self)
        self.tableWidget.setCellWidget(rowPosition, 0, nameEdit)

        # Family Name column
        familyEdit = QLineEdit("family")
        familyEdit.textChanged.connect(self.update_preview)
        familyEdit.installEventFilter(self)
        self.tableWidget.setCellWidget(rowPosition, 1, familyEdit)

        # Color column
        colorCombo = QComboBox()
        colorCombo.addItems(self._colors)
        colorCombo.currentIndexChanged.connect(self.update_preview)
        self.tableWidget.setCellWidget(rowPosition, 2, colorCombo)

        # Scene column
        sceneCombo = QComboBox()
        sceneCombo.addItems(self._scenes)
        sceneCombo.currentIndexChanged.connect(self.update_preview)
        self.tableWidget.setCellWidget(rowPosition, 3, sceneCombo)

        # Birth date column
        birthEdit = QLineEdit("1-1-2000")
        birthEdit.textChanged.connect(self.update_preview)
        self.tableWidget.setCellWidget(rowPosition, 4, birthEdit)

        # Group column
        groupCombo = QComboBox()
        groupCombo.addItems(["1", "2"])
        groupCombo.setCurrentIndex(0)
        groupCombo.currentIndexChanged.connect(self.update_preview)
        self.tableWidget.setCellWidget(rowPosition, 5, groupCombo)

    def addRow(self):
        """Add a new row and update the preview."""
        self.newRow()
        self.update_preview()

    def removeRow(self):
        """Remove the last row if there is more than one row."""
        count = self.tableWidget.rowCount()
        if count > 1:
            self.tableWidget.removeRow(count - 1)
            self.update_preview()

    def get_table_df(self):
        """Convert the table data to a pandas DataFrame."""
        rows = []
        for row in range(self.tableWidget.rowCount()):
            name = self.tableWidget.cellWidget(row, 0).text()
            family_name = self.tableWidget.cellWidget(row, 1).text()
            color = self.tableWidget.cellWidget(row, 2).currentText()
            scene = self.tableWidget.cellWidget(row, 3).currentText()
            birth_date = self.tableWidget.cellWidget(row, 4).text()
            group = int(self.tableWidget.cellWidget(row, 5).currentText())
            image_path = self._potloden_map.get((scene, color), "")
            rows.append(
                {
                    "name": name,
                    "family_name": family_name,
                    "color": color,
                    "scene": scene,
                    "birth_date": birth_date,
                    "group": group,
                    "image_path": image_path,
                }
            )
        return pd.DataFrame(rows)

    def update_preview(self):
        """Update the preview image using the selected row; fallback to first row if none selected."""
        df = self.get_table_df()
        if df.empty:
            return
        row_idx = self.tableWidget.currentRow()
        if not 0 <= row_idx < len(df):
            row_data = df.iloc[0]
        else:
            row_data = df.iloc[row_idx]

        pdf = MyPDF()
        pdf.add_person(row_data)
        pdf_bytes = pdf.output(dest="S").encode("latin1")
        doc = fitz.open("pdf", pdf_bytes)
        page = doc.load_page(0)
        pix = page.get_pixmap()
        img = QtGui.QImage(
            pix.samples,
            pix.width,
            pix.height,
            pix.stride,
            QtGui.QImage.Format.Format_RGB888,
        )
        self.previewLabel.setPixmap(QtGui.QPixmap.fromImage(img))
        doc.close()

    def save_pdf(self):
        """Save the current table data as a PDF file."""
        df = self.get_table_df()
        if df.empty:
            QMessageBox.critical(self, "Error", "No data available to save.")
            return
        try:
            out_pdf = MyPDF()
            outPath, _ = QFileDialog.getSaveFileName(
                self, "Save PDF", "", "PDF Files (*.pdf)"
            )
            if outPath:
                out_pdf.save_output(df, outPath)
                QMessageBox.information(self, "Success", "PDF successfully saved!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving PDF: {e}")

    def openSettings(self):
        """Open and display JSON layout settings."""
        json_path = os.path.join(self.base_dir, "layout.json")
        with open(json_path, "r") as file:
            document = json.load(file)
        self.model = JsonModel(json_path)
        self.model.load(document)
        self.tree_view = QTreeView()
        self.tree_view.setModel(self.model)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.resize(500, 300)
        self.tree_view.show()

    def eventFilter(self, source, event):
        """Watch for focus events on QLineEdit to update preview."""
        from PyQt6.QtCore import QEvent
        if event.type() == QEvent.Type.FocusIn:
            # Trigger update_preview when QLineEdit gains focus
            self.update_preview()
        return super().eventFilter(source, event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
