#!/usr/bin/env python3
"""
pdfm_gui.py - GUI for pdfm
Launched from the Windows right-click context menu with the PDF path as argument.

Usage:
    python pdfm_gui.py <file.pdf>
"""

import sys
import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

# Fix blurry rendering on high-DPI displays (125%, 150%, etc.)
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware (Windows 10+)
except Exception:
    try:
        windll.user32.SetProcessDPIAware()   # Fallback for Windows 8/8.1
    except Exception:
        pass

# Import core functions from pdfm.py (must be in the same folder)
SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR))

try:
    from pdfm import count_pages, add_blank_page
except ImportError:
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("pdfm", "pdfm.py not found in the same folder!")
    sys.exit(1)


# ─────────────────────────────────────────────
# COLORS & FONTS
# ─────────────────────────────────────────────
BG         = "#1e1e2e"   # main background
BG_CARD    = "#2a2a3e"   # card / frame background
ACCENT     = "#7c6af7"   # purple accent
ACCENT_HOV = "#9d8fff"   # accent hover
SUCCESS    = "#50fa7b"   # success green
ERROR      = "#ff5555"   # error red
TEXT       = "#cdd6f4"   # primary text
TEXT_DIM   = "#6c7086"   # secondary / muted text
BORDER     = "#45475a"   # borders

FONT_TITLE  = ("Segoe UI", 13, "bold")
FONT_LABEL  = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_MONO   = ("Consolas", 10)
FONT_BIG    = ("Segoe UI", 24, "bold")   # large page-count display
FONT_PAGES  = ("Segoe UI", 11)           # "pages" label below the number


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def open_in_edge(path: str):
    """Open the PDF in Microsoft Edge (falls back to default viewer)."""
    abs_path = str(Path(path).resolve())
    try:
        subprocess.Popen(f'start msedge "{abs_path}"', shell=True)
    except Exception:
        try:
            os.startfile(abs_path)
        except Exception:
            pass


def styled_button(parent, text, command, color=ACCENT, width=18):
    """Flat, styled tkinter button."""
    return tk.Button(
        parent,
        text=text,
        command=command,
        bg=color,
        fg="#ffffff",
        activebackground=ACCENT_HOV,
        activeforeground="#ffffff",
        relief="flat",
        bd=0,
        padx=16,
        pady=8,
        font=("Segoe UI", 10, "bold"),
        cursor="hand2",
        width=width,
    )


def styled_entry(parent, width=8, **kwargs):
    """Flat, styled tkinter entry field."""
    return tk.Entry(
        parent,
        bg=BG,
        fg=TEXT,
        insertbackground=ACCENT,
        relief="flat",
        bd=0,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT,
        font=FONT_MONO,
        width=width,
        **kwargs
    )


# ─────────────────────────────────────────────
# MAIN VIEW — ADD BLANK PAGE
# ─────────────────────────────────────────────
class AddBlankView(tk.Frame):
    """
    Single-view UI that:
      - shows the PDF filename and total page count (large)
      - lets the user pick an insertion position via text field
      - inserts the blank page and opens the result in Edge
    """

    def __init__(self, parent, pdf_path: str):
        super().__init__(parent, bg=BG_CARD)
        self.pdf_path = pdf_path
        self.total_pages = 0
        self.output_path = None
        self._build()
        self._load_info()   # count pages and update the display

    def _build(self):
        # ── Title ──────────────────────────────────────────
        tk.Label(self, text="Add Blank Page", font=FONT_TITLE,
                 bg=BG_CARD, fg=TEXT).pack(pady=(24, 4))
        tk.Label(self, text="Insert an empty page before the selected position",
                 font=FONT_SMALL, bg=BG_CARD, fg=TEXT_DIM).pack()

        # ── PDF info: filename ──────────────────────────────
        self.info_var = tk.StringVar(value="Loading...")
        tk.Label(self, textvariable=self.info_var, font=FONT_SMALL,
                 bg=BG_CARD, fg=TEXT_DIM).pack(pady=(10, 0))

        # ── Large page-count display ────────────────────────
        count_frame = tk.Frame(self, bg=BG, bd=0,
                               highlightthickness=1, highlightbackground=BORDER)
        count_frame.pack(pady=16, ipadx=30, ipady=12)

        self.count_var = tk.StringVar(value="—")
        tk.Label(count_frame, textvariable=self.count_var,
                 font=FONT_BIG, bg=BG, fg=ACCENT).pack(padx=50, pady=(10, 2))
        tk.Label(count_frame, text="pages",
                 font=FONT_PAGES, bg=BG, fg=TEXT_DIM).pack(pady=(0, 10))

        # ── Position input ──────────────────────────────────
        input_frame = tk.Frame(self, bg=BG_CARD)
        input_frame.pack(pady=(4, 0))

        tk.Label(input_frame, text="Insert blank page at position",
                 font=FONT_LABEL, bg=BG_CARD, fg=TEXT).grid(
                 row=0, column=0, padx=(0, 12), sticky="w")

        self.page_entry = styled_entry(input_frame, width=6)
        self.page_entry.grid(row=0, column=1)
        self.page_entry.insert(0, "1")
        self.page_entry.bind("<Return>", lambda e: self._add())  # Enter key triggers add


        # ── Add button ──────────────────────────────────────
        styled_button(self, "✚  Add", self._add).pack(pady=16)

        # ── Status message ──────────────────────────────────
        self.status_var = tk.StringVar()
        self.status_lbl = tk.Label(self, textvariable=self.status_var,
                                   font=FONT_SMALL, bg=BG_CARD, fg=TEXT_DIM,
                                   wraplength=380)
        self.status_lbl.pack(pady=4)

        # ── "Open in Edge" button (hidden until a file is produced) ──
        self.open_btn = styled_button(self, "🔗  Open in Edge",
                                      self._open_result, color="#2d6a4f")


    def _load_info(self):
        """Count the PDF pages and update the UI."""
        try:
            self.total_pages = count_pages(self.pdf_path)
            name = Path(self.pdf_path).name
            self.info_var.set(f"📄  {name}")
            self.count_var.set(str(self.total_pages))
        except Exception as e:
            self.info_var.set(f"Error reading PDF: {e}")
            self.count_var.set("!")

    def _add(self):
        """Validate input, call add_blank_page, and show the result."""
        try:
            page_num = int(self.page_entry.get())
        except ValueError:
            self._set_status("⚠  Please enter a valid number.", ERROR)
            return

        if page_num < 1:
            self._set_status("⚠  Position must be >= 1.", ERROR)
            return

        try:
            self._set_status("⏳  Processing...", TEXT_DIM)
            self.update()  # force UI refresh before blocking call

            out = add_blank_page(self.pdf_path, page_num)
            self.output_path = out
            new_total = count_pages(out)

            self._set_status(
                f"✓  Blank page inserted at position {page_num}.\n"
                f"Saved as: {Path(out).name}  ({new_total} pages)",
                SUCCESS
            )
            self.open_btn.pack(pady=4)   # reveal the "Open in Edge" button

        except Exception as e:
            self._set_status(f"Error: {e}", ERROR)

    def _set_status(self, msg: str, color: str = TEXT_DIM):
        self.status_var.set(msg)
        self.status_lbl.config(fg=color)

    def _open_result(self):
        if self.output_path and Path(self.output_path).exists():
            open_in_edge(self.output_path)
        else:
            messagebox.showerror("pdfm", "Output file not found!")


# ─────────────────────────────────────────────
# MAIN WINDOW
# ─────────────────────────────────────────────
class PdfmApp(tk.Tk):
    """Main application window — no tabs, single focused view."""

    def __init__(self, pdf_path: str):
        super().__init__()
        self.pdf_path = pdf_path
        self.window_x = "460"
        self.window_y = "580"
        self.title("pdfm")
        self.window_size = f"{self.window_x}x{self.window_y}"
        self.geometry(self.window_size)
        self.resizable(False, False)
        self.configure(bg=BG)

        # Center the window on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth()  - int(self.window_x)) // 2
        y = (self.winfo_screenheight() - int(self.window_y)) // 2
        self.geometry(f"{self.window_size}+{x}+{y}")

        self._build_header()
        self._build_body()

    def _build_header(self):
        """Top accent bar + 'pdfm' logo + truncated filename."""
        # Thin colored bar at the very top
        tk.Frame(self, bg=ACCENT, height=3).pack(fill="x")

        title_frame = tk.Frame(self, bg=BG)
        title_frame.pack(fill="x", padx=20, pady=(10, 0))

        # "pdf" in normal text color, "m" in accent
        tk.Label(title_frame, text="pdf", font=("Segoe UI", 16, "bold"),
                 bg=BG, fg=TEXT).pack(side="left")
        tk.Label(title_frame, text="m", font=("Segoe UI", 16, "bold"),
                 bg=BG, fg=ACCENT).pack(side="left")

        # Truncate long filenames so they fit the header
        name = Path(self.pdf_path).name
        if len(name) > 42:
            name = "…" + name[-40:]
        tk.Label(title_frame, text=name, font=FONT_SMALL,
                 bg=BG, fg=TEXT_DIM).pack(side="right", pady=4)

    def _build_body(self):
        """Fill the window with the single AddBlankView."""
        view = AddBlankView(self, self.pdf_path)
        view.pack(fill="both", expand=True, padx=0, pady=(6, 0))


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────
def main():
    # If no argument is given (e.g. double-click), show a file picker
    if len(sys.argv) < 2:
        root = tk.Tk()
        root.withdraw()
        from tkinter import filedialog
        pdf_path = filedialog.askopenfilename(
            title="Select a PDF",
            filetypes=[("PDF files", "*.pdf")]
        )
        root.destroy()
        if not pdf_path:
            sys.exit(0)
    else:
        pdf_path = os.path.expanduser(sys.argv[1])

    if not Path(pdf_path).exists():
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("pdfm", f"File not found:\n{pdf_path}")
        root.destroy()
        sys.exit(1)

    app = PdfmApp(pdf_path)
    app.mainloop()


if __name__ == "__main__":
    main()
