import json
import os
import sys

import pymupdf
from pdf_utils import addAttachments, MyPDF
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

import tempfile
from Settings import JsonModel


# get the base directory of the file, important for the packaging,
#  so that the program can find files in its package,
#  such as the layout.ui file
base_dir = os.path.dirname(os.path.abspath(__file__))


class NameLineEdit(QLineEdit):
    def focusInEvent(self, event):
        super().focusInEvent(
            event
        )  # Call the base class method to ensure normal focus behavior
        print("This QLineEdit has received focus!")  # Replace with your custom action


class Ui(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi(os.path.join(base_dir, "GUI/layout.ui"), self)
        self.newRow()
        self.addRowButton.clicked.connect(self.addRow)
        self.removeRowButton.clicked.connect(self.removeRow)
        self.savePDFbutton.clicked.connect(self.save_pdf)
        self.actionSide.triggered.connect(self.openSideImages)
        self.actionSettings.triggered.connect(self.openSettings)

        self.colors = {
            "red": [255, 0, 0],
            "green": [0, 255, 0],
            "blue": [0, 0, 255],
            "yellow": [255, 255, 0],
            "purple": [255, 0, 255],
            "orange": [255, 165, 0],
        }

        self.sideImages = [
            "./GUI/images/side1.png",
            "./GUI/images/side2.png",
            "./GUI/images/side3.png",
            "./GUI/images/side4.png",
        ]

        self.backgroundImage = "./GUI/images/bird.jpg"
        self.updateTempImages()

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

        # add text input and wait for change to trigger update_pdf_text
        name = FLineEdit("name")
        self.tableWidget.setCellWidget(rowPosition, 0, name)
        name.textChanged.connect(self.update_pdf_props)

        color = FComboBox()
        color.addItems(["red", "green", "blue", "yellow", "purple", "orange"])
        self.tableWidget.setCellWidget(rowPosition, 1, color)
        color.currentIndexChanged.connect(self.update_pdf_props)

        item = FComboBox()
        item.addItems(["Square", "Circle"])
        self.tableWidget.setCellWidget(rowPosition, 2, item)
        item.currentIndexChanged.connect(self.update_pdf_props)

    def update_pdf_props(self):
        row = self.tableWidget.currentRow()
        name = self.tableWidget.cellWidget(row, 0).text()
        color = self.tableWidget.cellWidget(row, 1).currentText()
        item = self.tableWidget.cellWidget(row, 2).currentText()

        self.pdf = MyPDF(unit="mm", format="A4")
        self.pdf.new_page("./GUI/images/bird.jpg", name, self.colors[color], item)
        self.update_pdf_view()

    def update_pdf_view(self):
        # Obtain PDF bytes as a string then encode to bytes
        pdf_bytes = self.pdf.output(dest="S").encode("latin1")
        # Open the PDF from bytes using pymupdf
        doc = pymupdf.open("pdf", pdf_bytes)
        page = doc.load_page(0)  # Load the first page
        pix = page.get_pixmap()
        img = QImage(
            pix.samples, pix.width, pix.height, pix.stride, QImage.Format.Format_RGB888
        )
        self.previewWidget.setPixmap(QPixmap.fromImage(img))
        doc.close()

    def save_pdf(self):
        for row in range(self.tableWidget.rowCount()):
            name = self.tableWidget.cellWidget(row, 0).text()
            color = self.tableWidget.cellWidget(row, 1).currentText()
            item = self.tableWidget.cellWidget(row, 2).currentText()
            if row == 0:
                self.pdf = MyPDF(unit="mm", format="A4")

            self.pdf.new_page("./GUI/images/bird.jpg", name, self.colors[color], item)

        outPath, _ = QFileDialog.getSaveFileName(
            self, "Save PDF", "", "PDF Files (*.pdf)"
        )

        if outPath:
            self.pdf.output(outPath)
            self.collectAndAddAtt(outPath)

    def addRow(self):
        self.newRow()
        self.update_pdf_props()

    def collectAndAddAtt(self, pdf_path):
        with open("layout.json", "r") as file:
            json_data = json.load(file)

        table_data = []
        for row in range(self.tableWidget.rowCount()):
            name = self.tableWidget.cellWidget(row, 0).text()
            color = self.tableWidget.cellWidget(row, 1).currentText()
            item = self.tableWidget.cellWidget(row, 2).currentText()
            table_data.append([name, color, item])

        table_dataBytes = json.dumps(table_data, indent=4).encode()
        json_dataBytes = json.dumps(json_data, indent=4).encode()

        addAttachments(
            pdf_path, json_dataBytes, "./GUI/images/bird.jpg", table_dataBytes
        )

    def removeRow(self):
        if self.tableWidget.rowCount() > 1:
            self.tableWidget.removeRow(self.tableWidget.rowCount() - 1)
            self.update_pdf_props()

    def openSideImages(self):
        from SideImages import Ui as SideImages

        self.sideImages = SideImages(self)
        self.sideImages.show()

    def updateTempImages(self):
        # save self.sideImages to a temporary file
        # get suffix from the file name
        for i, path in enumerate(self.sideImages):
            if path:
                suffix = os.path.splitext(path)[1]
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
                    temp.write(open(path, "rb").read())
                    self.sideImages[i] = temp.name
                    temp.flush()

        suffix = os.path.splitext(self.backgroundImage)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp:
            temp.write(open(self.backgroundImage, "rb").read())
            self.backgroundImage = temp.name
            temp.flush()

        print(self.sideImages, self.backgroundImage)

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
