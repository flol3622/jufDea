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
        with open("layout.json", "r") as file:
            layout = json.load(file)

        font_name = "SchoolKX_new_SB"
        self.add_font(
            font_name, fname=r"GUI/assets/SchoolKX_new_SemiBold.ttf", uni=True
        )

        for layout_type, details in layout.get("Types", {}).items():
            pos = details.get("Size & positions", {})
            width = pos.get("width (mm)")
            height = pos.get("height (mm)")
            portrait = pos.get("portrait", False)
            tops = pos.get("top (mm)", [])
            lefts = pos.get("left (mm)", [])
            margin = int(details.get("Background", {}).get("margin (mm)"))
            top_offset = int(details.get("Background", {}).get("top offset (mm)", 0))
            base_font_size = int(details.get("Text", {}).get("font-size"))
            text_margin = int(details.get("Text", {}).get("margin (mm)"))
            text_bottom_offset = int(
                details.get("Text", {}).get("margin-bottom (mm)", 0)
            )

            for top, left in zip(tops, lefts):
                x, y = left, top
                self.rect(x, y, width, height, style="D")
                size_img = (
                    (height - 2 * margin) if not portrait else (width - 2 * margin)
                )
                font_box = base_font_size * 0.352778 * 1.3

                if layout_type == "Fest":
                    txtX = x + text_margin
                    txtY = y + text_margin
                    txtW = width - 2 * text_margin
                    imgX = x + margin
                    imgY = (
                        y + font_box + 2 * text_margin + top_offset - text_bottom_offset
                    )
                    bottom_txtX = txtX
                    bottom_txtY = imgY + size_img + text_margin
                    bottom_txtW = txtW
                elif portrait:
                    txtX = x + text_margin
                    txtY = y + height - font_box - text_margin - text_bottom_offset
                    txtW = width - 2 * text_margin
                    imgX = x + margin
                    imgY = y + margin + top_offset
                else:
                    txtX = x + size_img + margin + text_margin
                    txtY = y + (height - font_box) / 2
                    txtW = width - size_img - margin - 2 * text_margin
                    imgX = x + margin
                    imgY = y + margin + top_offset

                display_name = f"{name}fest" if layout_type == "Fest" else name
                current_font_size = base_font_size
                self.set_font(font_name, size=current_font_size)

                # Adjust font size if text is too wide
                while (
                    self.get_string_width(display_name) > txtW and current_font_size > 1
                ):
                    current_font_size -= 1
                    self.set_font(font_name, size=current_font_size)

                # Center the text horizontally within txtW
                text_width = self.get_string_width(display_name)
                text_x_offset = (txtW - text_width) / 2
                self.set_xy(txtX + text_x_offset, txtY)

                # Split the text to apply green color to the first letter
                first_letter = display_name[0] if display_name else ""
                remaining_text = display_name[1:] if len(display_name) > 1 else ""

                self.set_text_color(0, 128, 0)  # Green for first letter
                self.cell(
                    self.get_string_width(first_letter),
                    font_box,
                    first_letter,
                    border=0,
                    align="C",
                    ln=0,
                )
                self.set_text_color(0, 0, 0)  # Black for the rest
                self.cell(
                    self.get_string_width(remaining_text),
                    font_box,
                    remaining_text,
                    border=0,
                    align="C",
                )

                self.image(image_path, imgX, imgY, w=0, h=size_img)

                if layout_type == "Fest":
                    self.set_font(font_name, size=current_font_size)
                    self.set_text_color(0, 0, 0)
                    bottom_text_x_offset = (
                        bottom_txtW - self.get_string_width(birth_date)
                    ) / 2
                    self.set_xy(bottom_txtX + bottom_text_x_offset, bottom_txtY)
                    self.cell(
                        self.get_string_width(birth_date),
                        font_box,
                        birth_date,
                        border=0,
                        align="C",
                    )

    def new_page(self, image_path, name, birth_date):
        self.add_page(orientation="L")
        self.draw(image_path, name, birth_date)


class GroupTablePDF(FPDF):
    DEFAULT_CELL_WIDTH = 90
    DEFAULT_CELL_HEIGHT = 14
    DEFAULT_MARGIN = 0.5
    X_START = 10
    Y_START = 10
    

    def __init__(self):
        super().__init__()
        self.add_font(
            "SchoolKX_new_SB", fname=r"GUI/assets/SchoolKX_new_SemiBold.ttf", uni=True
        )
        self.set_font("SchoolKX_new_SB", size=14)

    def add_group_table_page(self, data):
        self.add_page(orientation="P")

        # Split data into two groups and sort by birth_date (oldest first)
        def parse_date(d):
            parts = d.get("birth_date", "00-00-0000").strip().split("-")
            return int(parts[2]), int(parts[1]), int(parts[0])

        group1 = sorted([d for d in data if d.get("group") == 1], key=parse_date)
        group2 = sorted([d for d in data if d.get("group") == 2], key=parse_date)

        # Define starting x positions for left and right columns
        left_column_x = self.X_START
        right_column_x = self.X_START + self.DEFAULT_CELL_WIDTH

        self._draw_group(left_column_x, self.Y_START, group1)
        self._draw_group(right_column_x, self.Y_START, group2)

    def _draw_group(self, x, y_start, items):
        y = y_start
        for item in items:
            try:
                self._draw_group_cell(
                    x, y, self.DEFAULT_CELL_WIDTH, self.DEFAULT_CELL_HEIGHT, item
                )
            except Exception as e:
                print(f"Error drawing cell for item {item}: {e}")
            y += self.DEFAULT_CELL_HEIGHT

    def _draw_group_cell(self, x, y, width, height, item):
        name = item.get("name", "").strip()
        family_name = item.get("family_name", "").strip()
        image_path = item.get("image_path", "")

        # Draw cell border
        self.rect(x, y, width, height)

        # Calculate image dimensions and positioning
        img_size = height - 2 * self.DEFAULT_MARGIN
        img_x = x + self.DEFAULT_MARGIN
        img_y = y + self.DEFAULT_MARGIN

        # Draw the image if available
        self.image(image_path, img_x, img_y, img_size, img_size)

        # vertical line to separate image and text
        self.line(
            img_x + img_size, y + self.DEFAULT_MARGIN, img_x + img_size, y + height - self.DEFAULT_MARGIN
        )

        # Determine text area on the right side of the image
        text = f"{name} {family_name}".strip()
        text_x = img_x + img_size + self.DEFAULT_MARGIN
        text_y = y + self.DEFAULT_MARGIN
        text_width = width - img_size - 2 * self.DEFAULT_MARGIN

        self.set_xy(text_x, text_y)
        self.set_text_color(0, 0, 0)
        self.cell(
            text_width, height - 2 * self.DEFAULT_MARGIN, text, border=0, align="L"
        )


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
    test_pdf.output("output.pdf")
    print("Test PDF generated as output.pdf")

    # Example usage of GroupTablePDF
    group_data = [
        {
            "name": "Renzo",
            "family_name": "Verkroost",
            "image_path": "GUI/images/potloden/blij-blauw.jpg",
            "group": 1,
            "birth_date": "12-03-2012",
        },
        {
            "name": "Furkan",
            "family_name": "Tat",
            "image_path": "GUI/images/potloden/blij-groen.jpg",
            "group": 2,
            "birth_date": "12-03-2012",
        },
        {
            "name": "Shona",
            "family_name": "Ten Napel",
            "image_path": "GUI/images/potloden/blij-geel.jpg",
            "group": 1,
            "birth_date": "12-02-2012",
        },
        {
            "name": "Saar",
            "family_name": "Ebbeling",
            "image_path": "GUI/images/potloden/blij-roze.jpg",
            "group": 2,
            "birth_date": "18-02-2015",
        },
        {
            "name": "Aras",
            "family_name": "Yazici",
            "image_path": "GUI/images/potloden/blij-oranje.jpg",
            "group": 1,
            "birth_date": "30-05-2013",
        },
        {
            "name": "Melle",
            "family_name": "Schiderman",
            "image_path": "GUI/images/potloden/blij-blauw.jpg",
            "group": 2,
            "birth_date": "07-08-2014",
        },
        {
            "name": "Zyan",
            "family_name": "Booi",
            "image_path": "GUI/images/potloden/blij-rood.jpg",
            "group": 1,
            "birth_date": "21-12-2013",
        },
        {
            "name": "Sem",
            "family_name": "uit de Bosch",
            "image_path": "GUI/images/potloden/blij-groen.jpg",
            "group": 2,
            "birth_date": "03-04-2015",
        },
        # Add more as needed...
    ]
    group_table_pdf = GroupTablePDF()
    group_table_pdf.add_group_table_page(group_data)
    group_table_pdf.output("group_table_output.pdf")
    print("Group Table PDF generated as group_table_output.pdf")
