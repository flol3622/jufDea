import json
import pikepdf
from fpdf import FPDF
import pandas as pd


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
    def __init__(self):
        super().__init__()
        self.add_font(
            "SchoolKX_new_SB", fname=r"GUI/assets/SchoolKX_new_SemiBold.ttf", uni=True
        )
        self.set_font("SchoolKX_new_SB", size=14)

    def add_person(self, row):
        self.add_page(orientation="L")
        add_person_page(self, row)

    def save_output(self, df, output_path):
        for _, row in df.iterrows():
            self.add_person(row)

        # Add group table page as last page using the function
        self.add_page(orientation="P")
        add_group_table_page(self, df)
        self.output(output_path, "F")


def add_person_page(pdf, row):
    with open("layout.json", "r") as file:
        layout = json.load(file)

    font_name = "SchoolKX_new_SB"
    pdf.add_font(font_name, fname=r"GUI/assets/SchoolKX_new_SemiBold.ttf", uni=True)

    name = row["name"]
    birth_date = row["birth_date"]
    image_path = row["image_path"]

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
        text_bottom_offset = int(details.get("Text", {}).get("margin-bottom (mm)", 0))

        for top, left in zip(tops, lefts):
            x, y = left, top
            pdf.rect(x, y, width, height, style="D")
            size_img = (height - 2 * margin) if not portrait else (width - 2 * margin)
            font_box = base_font_size * 0.352778 * 1.3

            if layout_type == "Fest":
                txtX = x + text_margin
                txtY = y + text_margin
                txtW = width - 2 * text_margin
                imgX = x + margin
                imgY = y + font_box + 2 * text_margin + top_offset - text_bottom_offset
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
            pdf.set_font(font_name, size=current_font_size)

            # Adjust font size if text is too wide
            while pdf.get_string_width(display_name) > txtW and current_font_size > 1:
                current_font_size -= 1
                pdf.set_font(font_name, size=current_font_size)

            # Center the text horizontally within txtW
            text_width = pdf.get_string_width(display_name)
            text_x_offset = (txtW - text_width) / 2
            pdf.set_xy(txtX + text_x_offset, txtY)

            # Split the text to apply green color to the first letter
            first_letter = display_name[0] if display_name else ""
            remaining_text = display_name[1:] if len(display_name) > 1 else ""

            pdf.set_text_color(0, 128, 0)  # Green for first letter
            pdf.cell(
                pdf.get_string_width(first_letter),
                font_box,
                first_letter,
                border=0,
                align="C",
                ln=0,
            )
            pdf.set_text_color(0, 0, 0)  # Black for the rest
            pdf.cell(
                pdf.get_string_width(remaining_text),
                font_box,
                remaining_text,
                border=0,
                align="C",
            )

            pdf.image(image_path, imgX, imgY, w=0, h=size_img)

            if layout_type == "Fest":
                pdf.set_font(font_name, size=current_font_size)
                pdf.set_text_color(0, 0, 0)
                bottom_text_x_offset = (
                    bottom_txtW - pdf.get_string_width(birth_date)
                ) / 2
                pdf.set_xy(bottom_txtX + bottom_text_x_offset, bottom_txtY)
                pdf.cell(
                    pdf.get_string_width(birth_date),
                    font_box,
                    birth_date,
                    border=0,
                    align="C",
                )


def add_group_table_page(pdf, df):
    X_START = 10
    Y_START = 10
    CELL_WIDTH = 90
    CELL_HEIGHT = 12
    MARGIN = 0.5

    def parse_date(d):
        parts = str(d).strip().split("-")
        return int(parts[2]), int(parts[1]), int(parts[0])

    group1 = df[df["group"] == 1].sort_values(
        by="birth_date", key=lambda x: x.map(parse_date)
    )
    group2 = df[df["group"] == 2].sort_values(
        by="birth_date", key=lambda x: x.map(parse_date)
    )

    def draw_group(x, y_start, items):
        y = y_start
        for _, item in items.iterrows():
            name = item.get("name", "").strip()
            family_name = (
                item.get("family_name", "").strip() if "family_name" in item else ""
            )
            image_path = item.get("image_path", "")
            pdf.rect(x, y, CELL_WIDTH, CELL_HEIGHT)
            img_size = CELL_HEIGHT - 2 * MARGIN
            img_x = x + MARGIN
            img_y = y + MARGIN
            if image_path:
                pdf.image(image_path, img_x, img_y, img_size, img_size)
            pdf.line(
                img_x + img_size,
                y + MARGIN,
                img_x + img_size,
                y + CELL_HEIGHT - MARGIN,
            )
            text = f"{name} {family_name}".strip()
            text_x = img_x + img_size + MARGIN
            text_y = y + MARGIN
            text_width = CELL_WIDTH - img_size - 2 * MARGIN
            pdf.set_xy(text_x, text_y)
            pdf.set_text_color(0, 0, 0)
            pdf.set_font("SchoolKX_new_SB", size=14)
            pdf.cell(text_width, CELL_HEIGHT - 2 * MARGIN, text, border=0, align="L")
            y += CELL_HEIGHT

    draw_group(X_START, Y_START, group1)
    draw_group(X_START + CELL_WIDTH, Y_START, group2)


if __name__ == "__main__":
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
            "image_path": "GUI/images/potloden/bril-groen.jpg",
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
            "image_path": "GUI/images/potloden/cool-roze.jpg",
            "group": 2,
            "birth_date": "18-02-2015",
        },
        {
            "name": "Aras",
            "family_name": "Yazici",
            "image_path": "GUI/images/potloden/rugzak-oranje.jpg",
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
            "image_path": "GUI/images/potloden/zwaai-rood.jpg",
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
    ]
    df = pd.DataFrame(group_data)
    pdf = MyPDF()
    pdf.save_output(df, "full_output.pdf")

    single_person_pdf = MyPDF()
    single_person_pdf.add_person(df.iloc[0])
    single_person_pdf.output("single_output.pdf", "F")
