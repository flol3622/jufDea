# Standard library imports
import datetime
import json
import os
import sys

# Third-party imports
import fitz  # PyMuPDF
import pandas as pd
import pikepdf
from PyQt6 import QtGui
from PyQt6.QtCore import QDate, Qt
from PyQt6.QtGui import QAction
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDateEdit,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

# Internal imports
from jufDea.pdf_utils import MyPDF
from jufDea.Settings import JsonModel


class MainWindow(QMainWindow):
    """Main window for the PDF Generator application."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎉 PDF Generator")  # changed window title with emoji
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
        self.addRowButton = QPushButton("➕ Add Row")  # emoji before text
        self.removeRowButton = QPushButton("➖ Remove Row")  # emoji before text
        self.clearButton = QPushButton("🧹 Clear")  # emoji before text
        btnLayout.addWidget(self.addRowButton)
        btnLayout.addWidget(self.removeRowButton)
        btnLayout.addWidget(self.clearButton)  # Add Clear button to layout
        dataLayout.addLayout(btnLayout)

        self.savePDFButton = QPushButton("💾 Save PDF")  # emoji before text
        dataLayout.addWidget(self.savePDFButton)
        mainLayout.addWidget(dataGroup)

        # Right side: Preview GroupBox
        previewGroup = QGroupBox("Preview")
        previewLayout = QVBoxLayout(previewGroup)
        self.previewLabel = QLabel("📄 PDF Preview")  # emoji before text
        self.previewLabel.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.previewLabel.setFixedSize(842, 595)
        previewLayout.addWidget(self.previewLabel)
        mainLayout.addWidget(previewGroup)

        # Menu for Settings
        settingsAction = QAction("⚙️ Settings", self)  # emoji before text
        settingsAction.triggered.connect(self.openSettings)
        menubar = self.menuBar()
        advancedMenu = menubar.addMenu("Advanced")
        advancedMenu.addAction(settingsAction)
        openPdfAction = QAction("📄 Open PDF", self)  # emoji before text
        openPdfAction.triggered.connect(self.open_pdf)
        menubar.insertAction(advancedMenu.menuAction(), openPdfAction)

        # Add Clear action next to Advanced
        clearAction = QAction("🧹 Clear", self)  # emoji before text
        clearAction.triggered.connect(self.clear_table)
        menubar.insertAction(advancedMenu.menuAction(), clearAction)

        # Connect signals
        self.addRowButton.clicked.connect(self.addRow)
        self.removeRowButton.clicked.connect(self.removeRow)
        # self.clearButton.clicked.connect(self.clear_table)  # Remove button connection, now in menu
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

        # Birth date column - use QDateEdit instead of QLineEdit
        birthEdit = QDateEdit()
        birthEdit.setDisplayFormat("dd-MM-yyyy")
        birthEdit.setCalendarPopup(True)
        birthEdit.setDate(datetime.date(2000, 1, 1))
        birthEdit.dateChanged.connect(self.update_preview)
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

    def validate_birthdate(self, date_str):
        """Validate birth date format: accepts DD-MM-YYYY or D-M-YYYY."""
        # No longer needed with QDateEdit, always valid
        return True

    def get_table_df(self, validate_birthdate=False):
        """Convert the table data to a pandas DataFrame. If validate_birthdate is True, returns (df, invalid_row_idx) if invalid birthdate found."""
        rows = []
        for row in range(self.tableWidget.rowCount()):
            name = self.tableWidget.cellWidget(row, 0).text()
            family_name = self.tableWidget.cellWidget(row, 1).text()
            color = self.tableWidget.cellWidget(row, 2).currentText()
            scene = self.tableWidget.cellWidget(row, 3).currentText()
            # Get date from QDateEdit and format as string
            birth_date_widget = self.tableWidget.cellWidget(row, 4)
            birth_date = birth_date_widget.date().toString("dd-MM-yyyy")
            group = int(self.tableWidget.cellWidget(row, 5).currentText())
            image_path = self._potloden_map.get((scene, color), "")
            # Validate birthdate only if requested (always valid now)
            if validate_birthdate and not self.validate_birthdate(birth_date):
                return None, row
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
        if validate_birthdate:
            return pd.DataFrame(rows), None
        else:
            return pd.DataFrame(rows)

    def update_preview(self):
        """Update the preview image using the selected row; fallback to first row if none selected."""
        df = self.get_table_df(validate_birthdate=False)
        if df is None or df.empty:
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
        df, invalid_row = self.get_table_df(validate_birthdate=True)
        if invalid_row is not None:
            QMessageBox.critical(
                self,
                "Error",
                f"Invalid birth date syntax in row {invalid_row + 1}. Please use DD-MM-YYYY.",
            )
            return
        if df is None or df.empty:
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

    def open_pdf(self):
        """Open a PDF and load its JSON attachment to populate the table."""
        filePath, _ = QFileDialog.getOpenFileName(
            self, "Open PDF", "", "PDF Files (*.pdf)"
        )
        if filePath:
            try:
                pdf = pikepdf.open(filePath)
                attachments = pdf.attachments
                if "dataframe.json" in attachments:
                    # Fix: use get_file().read_bytes() instead of read_bytes()
                    data_bytes = attachments["dataframe.json"].get_file().read_bytes()
                    records = json.loads(data_bytes.decode("utf-8"))
                    self.tableWidget.setRowCount(0)
                    for record in records:
                        self.newRow()
                        row_idx = self.tableWidget.rowCount() - 1
                        self.tableWidget.cellWidget(row_idx, 0).setText(
                            record.get("name", "")
                        )
                        self.tableWidget.cellWidget(row_idx, 1).setText(
                            record.get("family_name", "")
                        )
                        idx = self.tableWidget.cellWidget(row_idx, 2).findText(
                            record.get("color", "")
                        )
                        if idx >= 0:
                            self.tableWidget.cellWidget(row_idx, 2).setCurrentIndex(idx)
                        idx = self.tableWidget.cellWidget(row_idx, 3).findText(
                            record.get("scene", "")
                        )
                        if idx >= 0:
                            self.tableWidget.cellWidget(row_idx, 3).setCurrentIndex(idx)
                        # Set date in QDateEdit
                        birth_date_str = record.get("birth_date", "")
                        birth_date_widget = self.tableWidget.cellWidget(row_idx, 4)
                        try:
                            qdate = QDate.fromString(birth_date_str, "dd-MM-yyyy")
                            if qdate.isValid():
                                birth_date_widget.setDate(qdate)
                        except Exception:
                            pass
                        idx = self.tableWidget.cellWidget(row_idx, 5).findText(
                            str(record.get("group", ""))
                        )
                        if idx >= 0:
                            self.tableWidget.cellWidget(row_idx, 5).setCurrentIndex(idx)
                    self.update_preview()
                else:
                    QMessageBox.critical(
                        self, "Error", "No JSON attachment found in PDF."
                    )
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Error loading PDF: {e}")

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

    def clear_table(self):
        """Clear the table and add one default row, with confirmation."""
        reply = QMessageBox.question(
            self,
            "🧹 Confirm Clear",  # emoji before text
            "🧹 Are you sure you want to clear all data?",  # emoji before text
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.tableWidget.setRowCount(0)
            self.newRow()
            self.update_preview()
        # else: do nothing

    def closeEvent(self, event):
        """Prompt user to save before closing if there is unsaved data."""
        reply = QMessageBox.question(
            self,
            "🚪 Exit",  # emoji before text
            "🚪 Are you sure you want to exit?\nMake sure you have saved your work.",  # emoji before text
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            event.accept()
        else:
            event.ignore()


def main():
    """Main function to run the application."""
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
