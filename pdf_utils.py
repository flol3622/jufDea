import json
import pikepdf
from fpdf import FPDF


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


class MyPDF(FPDF):
    def draw(self, image_path, name, birth_date):
        try:
            with open("layout.json", "r") as file:
                json_data = json.load(file)

            self.add_font(
                "SchoolKX_new_SB",
                fname=r"GUI/assets/SchoolKX_new_SemiBold.ttf",
                uni=True,
            )

            for type, details in json_data["Types"].items():
                width = details["Size & positions"]["width (mm)"]
                height = details["Size & positions"]["height (mm)"]
                portrait = details["Size & positions"].get("portrait", False)
                tops = details["Size & positions"]["top (mm)"]
                lefts = details["Size & positions"]["left (mm)"]
                margin = int(details["Background"]["margin (mm)"])
                top_offset = int(details["Background"].get("top offset (mm)", 0))
                font_size = int(details["Text"]["font-size"])
                text_margin = int(details["Text"]["margin (mm)"])
                text_bottomOffset = int(details["Text"].get("margin-bottom (mm)", 0))

                for top, left in zip(tops, lefts):
                    #  Rectangle
                    x = left
                    y = top
                    self.rect(x, y, width, height, "D")

                    # Image
                    sizeImg = (
                        height - 2 * margin if not portrait else width - 2 * margin
                    )

                    # Text position logic
                    font_box = font_size * 0.352778 * 1.3
                    if type == "Fest":
                        # Place text above the image for Fest
                        txtX = x + text_margin
                        txtY = y + text_margin
                        txtW = width - 2 * text_margin
                        imgX = x + margin
                        imgY = (
                            y
                            + font_box
                            + 2 * text_margin
                            + top_offset
                            - text_bottomOffset
                        )
                        # Position for bottom text (Placeholder)
                        bottom_txtX = txtX
                        bottom_txtY = imgY + sizeImg + text_margin
                        bottom_txtW = txtW
                    elif portrait:
                        txtX = x + text_margin
                        txtY = y + height - font_box - text_margin - text_bottomOffset
                        txtW = width - 2 * text_margin
                        imgX = x + margin
                        imgY = y + margin + top_offset
                    else:
                        txtX = x + sizeImg + margin + text_margin
                        txtY = y + (height - font_box) / 2
                        txtW = width - sizeImg - margin - 2 * text_margin
                        imgX = x + margin
                        imgY = y + margin + top_offset

                    # Write the text
                    self.set_font("SchoolKX_new_SB", size=font_size)
                    p_name = name + "fest" if type == "Fest" else name 

                    # Reduce font size if text is too wide
                    while self.get_string_width(p_name) > txtW and font_size > 1:
                        font_size -= 1  # Decrease font size by 1
                        self.set_font("SchoolKX_new_SB", size=font_size)

                    # Center the text
                    first_letter = p_name[0] if p_name else ""
                    remaining_text = p_name[1:] if len(p_name) > 1 else ""

                    self.set_xy(txtX + (txtW - self.get_string_width(p_name)) / 2, txtY)

                    self.set_text_color(0, 128, 0)  # RGB for green
                    self.cell(
                        w=self.get_string_width(first_letter),
                        h=font_box,
                        txt=first_letter,
                        border=0,
                        align="C",
                        ln=0,
                    )
                    self.set_text_color(0, 0, 0)  # Reset to default color
                    self.cell(
                        w=self.get_string_width(remaining_text),
                        h=font_box,
                        txt=remaining_text,
                        border=0,
                        align="C",
                    )

                    # Draw the image (after text for Fest, otherwise as before)
                    self.image(image_path, imgX, imgY, 0, sizeImg)

                    # For Fest, add another text under the image
                    if type == "Fest":
                        self.set_font("SchoolKX_new_SB", size=font_size)
                        self.set_text_color(0, 0, 0)  # Black
                        self.set_xy(
                            bottom_txtX
                            + (bottom_txtW - self.get_string_width(birth_date)) / 2,
                            bottom_txtY,
                        )
                        self.cell(
                            w=self.get_string_width(birth_date),
                            h=font_box,
                            txt=birth_date,
                            border=0,
                            align="C",
                        )

        except Exception:
            pass  # Removed QMessageBox.critical (no GUI dependency)

    def new_page(self, image_path, name, birth_date):
        self.add_page(orientation="L")
        self.draw(image_path, name, birth_date)

    def add_special_page(self, image_path, name, birth_date, special_text=None):
        """
        Adds a special page at the end of the PDF with optional special text.
        """
        self.add_page(orientation="L")
        self.draw(image_path, name, birth_date)
        if special_text:
            self.set_font("SchoolKX_new_SB", size=24)
            self.set_text_color(255, 0, 0)  # Red for special
            self.set_xy(10, 10)
            self.cell(0, 20, special_text, align="C")


if __name__ == "__main__":
    # Simple test script for MyPDF
    import os
    test_pdf = MyPDF()
    test_imageA = os.path.join("GUI", "images", "potloden", "blij-blauw.jpg")
    test_imageB = os.path.join("GUI", "images", "potloden", "bril-rood.jpg")
    test_name = "Test Name"
    test_birth = "01-01-2000"
    test_pdf.new_page(test_imageA, "philippe", "25-08-1999")
    test_pdf.new_page(test_imageB, "hanne", "lalalala")

    test_pdf.add_special_page(test_imageA, test_name, test_birth, special_text="SPECIAL PAGE!")
    test_pdf.output("output.pdf")
    print("Test PDF generated as output.pdf")
