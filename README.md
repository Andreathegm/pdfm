# PDFM - Insert Blank pages into PDF

A lightweight Windows utility for inserting blank pages into PDF documents directly from the File Explorer context menu.

## Overview

PDFM is designed for users who frequently read PDF documents such as research papers, articles, theses, and lecture notes, and need additional space for handwritten notes, sketches, or annotations.

While modern PDF viewers such as **Microsoft Edge** provide excellent reading and annotation capabilities, they do not allow users to insert new pages into existing documents. PDFM fills this gap by making it possible to add blank pages exactly where they are needed.
Also with nowadays AI assistance Edge is able to read the open tab to help you study.

## Features

- Insert a blank page at any position within a PDF
- Preserve selectable text and document structure
- Retain existing annotations and comments
- Preserve document metadata
- Maintain bookmark and outline functionality
- Simple graphical interface built with Tkinter
- Windows File Explorer context menu integration
- High-DPI aware interface
- Lightweight and fast


## Installation

- **Quick installation**: Go to the **Releases** section .
- **Manual installation** Follow the steps listed below.

### Requirements

- Python 3.7 or later
- Windows (required for context menu integration)
- Edge installed

### Setup

Clone the repository:

```bash
git clone <repository-url>
cd pdfm
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Main dependencies:

- `pypdf` — PDF reading and modification
- `reportlab` — blank page generation

## Project Structure

```text
pdfm
    ├── pdfm.py              # Core PDF manipulation logic and CLI
    ├── pdfm_gui.py          # Tkinter graphical interface
    ├── requirements.txt     # Project dependencies
    └──install_menu_v5.reg  # Windows registry integration
```

### Optional: Windows Context Menu Integration

Just double-click on **install_menu_v5.reg**.
This adds the **Open with PDFM** entry to the context menu for PDF files.

## Graphical Interface

### Usage
If context menu integration is installed : 
1. Right-click a PDF file in Windows File Explorer
2. Select **Open with PDFM**(if it doesn't appear right after you have to click 'more option')
3. In the application window:
   - View the total number of pages
   - Enter the page number before which the blank page should be inserted
   - Click **Add Blank Page**
4. The PDF is saved automatically
5. Click **Open in Edge** to review the result

Alternatively you can run : 

```bash
python pdfm_gui.py
```
and then browse your pdf. The GUI will appear and work like above.

## Command-Line Usage

### Count Pages

```bash
python pdfm.py count document.pdf
```

### Insert a Blank Page

```bash
python pdfm.py add_blank_page document.pdf 3
```

### Specify an Output File

```bash
python pdfm.py add_blank_page document.pdf 3 --output modified_document.pdf
```

## Examples

### Insert a Notes Page at the Beginning

```bash
pdfm add_blank_page paper.pdf 1 --output paper_notes.pdf
```

The blank page becomes page 1 and the original document starts at page 2.

### Insert a Notes Page Between Sections

To insert a blank page before page 13:

```bash
pdfm add_blank_page paper.pdf 13 --output paper_notes.pdf
```

### Append a Notes Page at the End

```bash
pdfm add_blank_page paper.pdf 999 --output paper_notes.pdf
```

If the specified page exceeds the document length, the blank page is appended to the end of the document.

## License

This project is provided for personal and educational use.