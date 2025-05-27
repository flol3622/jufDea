import json
import os
import sys
import fitz  # PyMuPDF
from pdf_utils import addAttachments, MyPDF, GroupTablePDF
from PyQt6 import QtWidgets, uic
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QFileDialog,
    QLineEdit,
    QTreeView,
    QHeaderView,
)
import pandas as pd
from Settings import JsonModel


# get the base directory of the file, important for the packaging,
#  so that the program can find files in its package,
#  such as the layout.ui file
base_dir = os.path.dirname(os.path.abspath(__file__))


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(os.path.join(base_dir, "GUI/layout.ui"), self)
        self.backgroundImageFolder = os.path.join(base_dir, "GUI", "images", "potloden")
        self._scenes, self._colors, self._potloden_map = self._load_potloden_images()
        self.newRow()
        self.addRowButton.clicked.connect(self.addRow)
        self.removeRowButton.clicked.connect(self.removeRow)
        self.savePDFbutton.clicked.connect(self.save_pdf)
        self.actionSettings.triggered.connect(self.openSettings)
        self.backgroundImageFolder = os.path.join(base_dir, "GUI", "images", "potloden")

    def _load_potloden_images(self):
        scenes = set()
        colors = set()
        potloden_map = {}
        for f_name in os.listdir(self.backgroundImageFolder):
            if not f_name.endswith(".jpg"):
                continue
            scene, color = os.path.splitext(f_name)[0].split("-")
            scenes.add(scene)
            colors.add(color)
            potloden_map[(scene, color)] = os.path.join(
                self.backgroundImageFolder, f_name
            )
        return list(sorted(scenes)), list(sorted(colors)), potloden_map

    def newRow(self):
        class FLineEdit(QLineEdit):
            def focusInEvent(widget, event):
                super().focusInEvent(event)
                self.update_pdf_props()

        class FComboBox(QComboBox):
            def focusInEvent(widget, event):
                super().focusInEvent(event)
                self.update_pdf_props()

        rowPosition = self.tableWidget.rowCount()
        self.tableWidget.insertRow(rowPosition)
        name = FLineEdit("name")
        self.tableWidget.setCellWidget(rowPosition, 0, name)
        name.textChanged.connect(self.update_pdf_props)
        color = FComboBox()
        color.addItems(self._colors)
        self.tableWidget.setCellWidget(rowPosition, 1, color)
        color.currentIndexChanged.connect(self.update_pdf_props)
        scene = FComboBox()
        scene.addItems(self._scenes)
        self.tableWidget.setCellWidget(rowPosition, 2, scene)
        scene.currentIndexChanged.connect(self.update_pdf_props)
        # Add Birth date column (QLineEdit)
        birth_date = FLineEdit("1-1-2000")
        self.tableWidget.setCellWidget(rowPosition, 3, birth_date)
        birth_date.textChanged.connect(self.update_pdf_props)
        # Add Group column (QComboBox with values 1, 2, 3, default 1)
        group = FComboBox()
        group.addItems(["1", "2", "3"])
        group.setCurrentIndex(0)
        self.tableWidget.setCellWidget(rowPosition, 4, group)
        group.currentIndexChanged.connect(self.update_pdf_props)

    def get_table_df(self):
        rows = []
        for row in range(self.tableWidget.rowCount()):
            name = self.tableWidget.cellWidget(row, 0).text()
            color = self.tableWidget.cellWidget(row, 1).currentText()
            scene = self.tableWidget.cellWidget(row, 2).currentText()
            birth_date = self.tableWidget.cellWidget(row, 3).text()
            group = int(self.tableWidget.cellWidget(row, 4).currentText())
            image_path = self._potloden_map[(scene, color)]
            rows.append({
                "name": name,
                "scene": scene,
                "color": color,
                "birth_date": birth_date,
                "group": group,
                "image_path": image_path
            })
        return pd.DataFrame(rows)

    def update_pdf_props(self):
        row_idx = self.tableWidget.currentRow()
        df = self.get_table_df()
        if 0 <= row_idx < len(df):
            row = df.iloc[row_idx]
        else:
            row = df.iloc[0] if len(df) > 0 else None
        self.pdf = MyPDF(unit="mm", format="A4")
        if row is not None:
            self.pdf.new_page(row)
        self.update_pdf_view()

    def update_pdf_view(self):
        # Obtain PDF bytes as a string then encode to bytes
        pdf_bytes = self.pdf.output(dest="S").encode("latin1")
        # Open the PDF from bytes using PyMuPDF
        doc = fitz.open("pdf", pdf_bytes)
        page = doc.load_page(0)  # Load the first page
        pix = page.get_pixmap()
        img = QImage(
            pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888
        )
        self.previewWidget.setPixmap(QPixmap.fromImage(img))
        doc.close()

    def save_pdf(self):
        df = self.get_table_df()
        self.pdf = MyPDF(unit="mm", format="A4")
        for _, row in df.iterrows():
            self.pdf.new_page(row)
        # Add group table page
        group_table_pdf = GroupTablePDF()
        group_table_pdf.add_group_table_page(df)
        # Merge group table page into self.pdf (optional, or save separately)
        outPath, _ = QFileDialog.getSaveFileName(
            self, "Save PDF", "", "PDF Files (*.pdf)"
        )
        if outPath:
            self.pdf.output(outPath)
            self.collectAndAddAtt(outPath, df)

    def collectAndAddAtt(self, pdf_path, df):
        with open("layout.json", "r") as file:
            json_data = json.load(file)
        table_dataBytes = df.to_json(orient="records", indent=4).encode()
        json_dataBytes = json.dumps(json_data, indent=4).encode()
        image_path = df.iloc[0]["image_path"] if not df.empty else ""
        addAttachments(pdf_path, json_dataBytes, image_path, table_dataBytes)

    def addRow(self):
        self.newRow()
        self.update_pdf_props()

    def removeRow(self):
        if self.tableWidget.rowCount() > 1:
            self.tableWidget.removeRow(self.tableWidget.rowCount() - 1)
            self.update_pdf_props()

    def openSettings(self):
        self.tree_view = QTreeView()
        json_path = os.path.join(base_dir, "layout.json")
        self.model = JsonModel(json_path)

        # Load the JSON data into the model
        with open(json_path) as file:
            document = json.load(file)
            self.model.load(document)

        self.tree_view.setModel(self.model)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.resize(500, 300)
        self.tree_view.show()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Ui()
    window.setWindowTitle("DEMO")  # set the window title
    window.show()
    sys.exit(app.exec())
