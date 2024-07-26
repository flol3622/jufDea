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
    QTreeView,
    QHeaderView,
)

import tempfile
from Settings import JsonModel


def addAttachments(pdf_path, jsonBytes, image_path, tableBytes):
    with pikepdf.open(pdf_path, allow_overwriting_input=True) as pdf:
        jsonAtt = pikepdf.AttachedFileSpec(pdf, jsonBytes, mime_type="application/json")
        imageAtt = pikepdf.AttachedFileSpec.from_filepath(pdf, image_path)
        tableAtt = pikepdf.AttachedFileSpec(
            pdf, tableBytes, mime_type="application/json"
        )
        pdf.attachments["layout.json"] = jsonAtt
        pdf.attachments["bird.jpg"] = imageAtt
        pdf.attachments["table.json"] = tableAtt
        pdf.save()


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
        pdf_bytes = self.pdf.output()  # Obtain PDF bytes
        doc = fitz.open("pdf", pdf_bytes)
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
        self.model = JsonModel()
        
        # Load the JSON data into the model
        json_path = os.path.join(base_dir, "layout.json")
        with open(json_path) as file:
            document = json.load(file)
            self.model.load(document)
        
        self.tree_view.setModel(self.model)
        self.tree_view.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree_view.setAlternatingRowColors(True)
        self.tree_view.resize(500, 300)
        self.tree_view.show()


        


class MyPDF(FPDF):
    def draw(self, image_path, name, color, item):
        try:
            with open("layout.json", "r") as file:
                json_data = json.load(file)

            iWidth = float(json_data["Background-item"]["width (%)"])
            iHeight = float(json_data["Background-item"]["height (%)"])
            iTop = float(json_data["Background-item"]["top (%)"])
            iLeft = float(json_data["Background-item"]["left (%)"])

            self.add_font(
                "SchoolKX_new_SB",
                fname=r"GUI\assets\SchoolKX_new_SemiBold.ttf",
                uni=True,
            )

            for type, details in json_data["Types"].items():
                width = details["Size & positions"]["width (mm)"]
                height = details["Size & positions"]["height (mm)"]
                tops = details["Size & positions"]["top (mm)"]
                lefts = details["Size & positions"]["left (mm)"]
                margin = int(details["Background"]["margin (mm)"])
                top_offset = int(details["Background"].get("top offset (mm)", 0))
                font_size = int(details["Text"]["font-size"])
                text_margin = int(details["Text"]["margin (mm)"])
                text_bottomOffset = int(details["Text"].get("margin-bottom (mm)", 0))

                for top, left in zip(tops, lefts):
                    # Main rectangle
                    x = left
                    y = top
                    self.rect(x, y, width, height, "D")

                    # Image
                    sizeImg = height - 2 * margin
                    self.image(
                        image_path, x + margin, y + margin + top_offset, 0, sizeImg
                    )

                    # Item
                    if item == "Square":
                        self.set_fill_color(color[0], color[1], color[2])
                        self.rect(
                            x + sizeImg * iLeft / 100 + margin,
                            y + sizeImg * iTop / 100 + margin + top_offset,
                            sizeImg * iWidth / 100,
                            sizeImg * iHeight / 100,
                            "F",
                        )

                    elif item == "Circle":
                        self.set_fill_color(color[0], color[1], color[2])
                        self.ellipse(
                            x + sizeImg * iLeft / 100 + margin,
                            y + sizeImg * iTop / 100 + margin + top_offset,
                            sizeImg * iWidth / 100,
                            sizeImg * iHeight / 100,
                            "F",
                        )

                    # Name
                    font_box = font_size * 0.352778 * 1.3

                    if type != "Large":
                        txtX = x + sizeImg + margin + text_margin
                        txtY = y + (height - font_box) / 2
                        txtW = width - sizeImg - margin - 2 * text_margin
                    else:
                        txtX = x + text_margin
                        txtY = y + height - font_box - text_margin - text_bottomOffset
                        txtW = width - 2 * text_margin

                    self.set_font("SchoolKX_new_SB", size=font_size)
                    while self.get_string_width(name) > txtW and font_size > 1:
                        font_size -= 1  # Decrease font size by 1
                        self.set_font("SchoolKX_new_SB", size=font_size)

                    # Set the first letter in green
                    first_letter = name[0] if name else ""
                    remaining_text = name[1:] if len(name) > 1 else ""

                    self.set_xy(txtX + (txtW - self.get_string_width(name)) / 2, txtY)

                    self.set_text_color(0, 128, 0)  # RGB for green
                    self.cell(
                        w=self.get_string_width(first_letter),
                        h=font_box,
                        text=first_letter,
                        border=0,
                        align="C",
                        ln=0,
                    )
                    self.set_text_color(0, 0, 0)  # Reset to default color
                    self.cell(
                        w=self.get_string_width(remaining_text),
                        h=font_box,
                        text=remaining_text,
                        border=0,
                        align="C",
                    )

        except Exception as e:
            # pop up a message box with the error message
            QMessageBox.critical(None, "Error", str(e))

    def new_page(self, image_path, name, color, item):
        self.add_page(orientation="L")
        self.draw(image_path, name, color, item)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = Ui()
    window.setWindowTitle("DEMO")  # set the window title
    window.show()
    sys.exit(app.exec())
