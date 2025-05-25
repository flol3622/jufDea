# Project Documentation for AI-Assisted Recreation

## 1. Project Goal

The primary goal of this project is to provide a desktop application that allows users to dynamically create and customize PDF documents. Users can define content elements, their properties (like text, color, and type), and their layout within the PDF. The application supports incorporating images (background and side images) and attaching structured data (JSON) to the generated PDFs.

## 2. Core Functionalities

*   **PDF Generation & Manipulation:**
    *   Create new PDF documents from scratch.
    *   Add text elements with specified properties (name, color, item type) to PDF pages.
    *   Incorporate background images into PDF pages.
    *   Include multiple "side images" that can be previewed and potentially used in different sections or versions of the PDF.
    *   Save the generated PDF to a user-specified location.
    *   Attach JSON data (e.g., layout configurations, table data) to the PDF.

*   **Graphical User Interface (GUI):**
    *   A main window for managing PDF content elements in a table-like structure.
    *   Users can add or remove rows, where each row represents an element in the PDF.
    *   Input fields (like `QLineEdit` and `QComboBox`) for defining element properties (name, color, item type).
    *   A preview area (implicitly, as PDF properties are updated) or a mechanism to view the generated PDF.
    *   A separate window/widget to manage and preview up to four "side images."
    *   A settings window to manage application or layout configurations, likely loaded from and saved to `layout.json`.

*   **Configuration & Data Management:**
    *   Load and save layout configurations from/to a `layout.json` file. This JSON defines properties for different element types (e.g., "Extra small", "Large") including their dimensions, positions, and text attributes.
    *   Store and manage paths to side images and background images.
    *   Collect data from the UI (table rows) to generate PDF content.

## 3. Application Structure

The application is built using Python and PyQt6 for the GUI, with `fpdf2` for PDF creation and `pikepdf` for PDF manipulation (like adding attachments).

*   **`GUI.py` (Main Application Logic):**
    *   Initializes the main application window using `GUI/layout.ui`.
    *   Manages a table (`QTableWidget`) where users define PDF elements.
    *   Handles actions like adding/removing rows (elements), saving the PDF.
    *   Connects UI elements (buttons, input fields) to corresponding backend functions.
    *   Contains methods for:
        *   `newRow()`: Adds a new row to the table for defining a PDF element.
        *   `update_pdf_props()`: Updates PDF properties based on UI changes.
        *   `save_pdf()`: Generates and saves the PDF, including attachments.
        *   `openSideImages()`: Opens the side images management window.
        *   `openSettings()`: Opens the settings management window.
    *   Uses a custom `MyPDF(FPDF)` class to draw elements on the PDF.

*   **`SideImages.py` (Side Images Management):**
    *   Initializes a separate window using `GUI/sidePicturesWidget.ui`.
    *   Displays previews of up to four side images.
    *   Likely allows users to upload/change these side images (though the upload button connections are not explicitly shown in the provided snippet).
    *   `updatePreviews()`: Refreshes the image previews in the UI.

*   **`Settings.py` (Settings Management):**
    *   Implements a `JsonModel` class that subclasses `QAbstractItemModel` to display and edit JSON data (from `layout.json`) in a `QTreeView`.
    *   Allows viewing and potentially modifying the layout settings.
    *   `load()`: Loads JSON data into the tree model.
    *   `save_json()`: Saves changes from the model back to the JSON file.

*   **`layout.json` (Layout Configuration):**
    *   A JSON file storing default layout parameters for different types of elements (e.g., "Large", "Medium", "Small"). This includes dimensions, margins, positions, and font sizes.

*   **UI Files (`.ui`):**
    *   `GUI/layout.ui`: Defines the structure of the main application window.
    *   `GUI/sidePicturesWidget.ui`: Defines the structure of the side images window.
    *   These are created using Qt Designer and loaded dynamically using `uic.loadUi`.

## 4. Key Data Structures

*   **Table Data (in `GUI.py`):** The `self.tableWidget` in `GUI.py` holds the user-defined elements for the PDF. Each row typically contains:
    *   Name (QLineEdit)
    *   Color (QComboBox)
    *   Item Type (QComboBox, e.g., "Square", "Circle")
*   **Side Images List (in `GUI.py`):** `self.sideImages` is a list of file paths to the four side images.
*   **Layout Configuration (in `layout.json` and handled by `Settings.py`):** A nested dictionary structure defining properties for various element types and a general "Background-item".
    *   Example: `"Types": { "Large": { "Size & positions": { "height (mm)": 95, ... }, "Text": { "font-size": 48, ... } } }`
*   **PDF Attachments:** The application attaches `layout.json`, an image (`bird.jpg`), and `table.json` (presumably data from the table widget) to the output PDF.

## 5. External Dependencies/Requirements

To build and run this application, the following Python libraries are required:

*   **PyQt6:** For the graphical user interface.
*   **fpdf2:** (Likely, as `FPDF` class is used) For core PDF generation.
*   **pikepdf:** For opening, modifying, and saving existing PDFs, primarily used here for adding attachments.
*   **fitz (PyMuPDF):** Used in `SideImages.py`. Its exact role in the provided snippet is for image display (`QImage`, `QPixmap`), but PyMuPDF is a powerful PDF manipulation library.

A `pyproject.toml` file might exist, which would specify these dependencies for package managers like Poetry or PDM.

## 6. User Interface (UI) Overview

*   **Main Window (`GUI/layout.ui`):**
    *   A menu bar with "Files" (New, Open, Save) and "Advanced" (Settings, Upload background, Upload side pictures) options.
    *   A central area likely split into two main group boxes.
        *   One group box (`groupBox` named "Data") is intended for the table where users input data for PDF elements.
        *   The other group box (`groupBox_2`) might be for PDF preview or other controls.
    *   Buttons to "Add Row", "Remove Row", and "Save PDF".

*   **Side Pictures Window (`GUI/sidePicturesWidget.ui`):**
    *   A grid layout to display four image previews (`label_5` to `label_8`).
    *   Four corresponding "Upload version X" buttons (`pushButton` to `pushButton_4`) to allow users to select image files for each slot.

*   **Settings Window (Implied, managed by `Settings.py`):**
    *   A window containing a `QTreeView` to display and edit the contents of `layout.json`.
    *   The tree view will have two columns: "key" and "value".

This structure allows users to configure various aspects of a PDF document, add content dynamically, and manage associated images and settings through a graphical interface.

## 7. Output PDF Structure and Appearance

The generated PDF is the primary output of the application. It's not just a visual document but also a container for structured data and resources.

### 7.1. Visual Appearance

*   **Content Elements:** The PDF will display elements (e.g., text, shapes implied by "item type") as defined by the user in the main application's table. Each element's properties (name/text, color, and type like "Square" or "Circle") will be rendered on the PDF page.
*   **Layout and Positioning:** The visual layout of these elements is determined by the settings in `layout.json`. This file specifies coordinates (left, top), dimensions (width, height), and text properties (font size, margins) for different categories of items (e.g., "Large", "Medium", "Small"). The application will use these definitions to place and style each element on the PDF pages.
*   **Background Image:** A background image (e.g., `bird.jpg` by default) will be rendered on the PDF pages, likely serving as a backdrop for the content elements. The `layout.json` file contains a "Background-item" section that might control its scaling or positioning.
*   **Multiple Pages:** The `MyPDF` class has a `new_page` method, suggesting that if the content exceeds one page or if explicitly defined, the PDF can have multiple pages, each potentially with its own set of drawn elements based on the user's input.
*   **Side Images:** While the `SideImages.py` module allows managing up to four side images, and these are stored in `self.sideImages` in `GUI.py`, their direct rendering onto the final PDF isn't explicitly detailed in the provided `MyPDF.draw` or `MyPDF.new_page` methods. They are available resources, and their use in the PDF would depend on further implementation details (e.g., if specific "item types" are designed to incorporate them or if they are used for different PDF versions/sections).

### 7.2. Metadata and Attachments

The PDF file will embed several pieces of data as attachments, making it a self-contained package of not just the visual representation but also the data and configuration used to create it. This is crucial for data persistence, sharing, and potential re-processing.

*   **`layout.json`:** The complete `layout.json` file, which defines the styling and positioning rules for different element types, will be attached. This allows the PDF to carry its own layout schema.
    *   *Navigation in App:* This file is loaded by `Settings.py` for viewing/editing and used by `GUI.py` during PDF generation to determine how and where to draw elements.
*   **Background Image File (e.g., `bird.jpg`):** The actual image file used as the background is attached.
    *   *Navigation in App:* The path to this image is stored in `self.backgroundImage` in `GUI.py` and used during PDF rendering.
*   **`table.json`:** This is a JSON file representing the data entered by the user into the main table of `GUI.py`. It would likely be a list of objects, where each object corresponds to a row and contains the 'name', 'color', and 'item type' for an element.
    *   *Navigation in App:* This data is collected from `self.tableWidget` in `GUI.py` at the time of saving the PDF. It's the raw user input that drives the content generation.

These attachments ensure that the PDF is not just a static visual document but also carries the necessary data and configuration to understand its structure and potentially recreate or modify its content.
