#!/usr/bin/env python3
"""
pdfm - PDF Modifier CLI
Modifica PDF mantenendo testo selezionabile, annotazioni e metadati.

Uso:
    pdfm count <file.pdf>
    pdfm add_blank_page <file.pdf> <page_number> [--output <out.pdf>]

Esempi:
    pdfm count documento.pdf
    pdfm add_blank_page documento.pdf 1
    pdfm add_blank_page documento.pdf 3 --output nuovo.pdf
"""

import argparse
import sys
import os
from pathlib import Path
from io import BytesIO

try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import NameObject, ArrayObject, DictionaryObject
except ImportError:
    print("Errore: pypdf non trovato. Installalo con: pip install pypdf")
    sys.exit(1)

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as rl_canvas
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


# ─────────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────────

def count_pages(pdf_path: str) -> int:
    """Ritorna il numero di pagine del PDF."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"File non trovato: {pdf_path}")
    if not path.suffix.lower() == ".pdf":
        raise ValueError(f"Il file non è un PDF: {pdf_path}")

    reader = PdfReader(str(path))
    return len(reader.pages)


def _create_blank_page(width, height) -> object:
    """
    Crea una pagina bianca con le stesse dimensioni passate.
    Usa reportlab se disponibile (più compatibile), altrimenti pypdf.
    """
    if HAS_REPORTLAB:
        buf = BytesIO()
        c = rl_canvas.Canvas(buf, pagesize=(width, height))
        c.showPage()  # registra la pagina bianca prima di salvare
        c.save()
        buf.seek(0)
        blank_reader = PdfReader(buf)
        return blank_reader.pages[0]
    else:
        # Fallback: pagina vuota tramite pypdf
        writer_tmp = PdfWriter()
        writer_tmp.add_blank_page(width=width, height=height)
        buf = BytesIO()
        writer_tmp.write(buf)
        buf.seek(0)
        blank_reader = PdfReader(buf)
        return blank_reader.pages[0]


def add_blank_page(pdf_path: str, page_number: int, output_path: str = None) -> str:
    """
    Inserisce una pagina bianca PRIMA della posizione page_number (1-based).

    - page_number = 1  → pagina bianca diventa la prima pagina
    - page_number = 3  → pagina bianca va in posizione 3, le altre slittano
    - page_number > n  → pagina bianca viene aggiunta in fondo

    Preserva:
    - Testo selezionabile (layer testo originale intatto)
    - Annotazioni / scarabocchi (ink annotations, commenti, ecc.)
    - Metadati del documento (titolo, autore, soggetto, ecc.)
    - Segnalibri (outlines/bookmarks), se presenti
    """
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"File non trovato: {pdf_path}")

    reader = PdfReader(str(path))
    total_pages = len(reader.pages)

    # Validazione page_number
    if page_number < 1:
        raise ValueError(f"page_number deve essere >= 1 (ricevuto: {page_number})")
    if page_number > total_pages + 1:
        print(f"  ⚠  page_number={page_number} supera {total_pages + 1}: "
              f"la pagina bianca sarà aggiunta in fondo.")
        page_number = total_pages + 1

    # Indice 0-based dove inserire la pagina bianca
    insert_idx = page_number - 1  # 0-based

    # Determina dimensioni: usa la pagina adiacente come riferimento
    if total_pages > 0:
        ref_idx = min(insert_idx, total_pages - 1)
        ref_page = reader.pages[ref_idx]
        width = float(ref_page.mediabox.width)
        height = float(ref_page.mediabox.height)
    else:
        width, height = A4 if HAS_REPORTLAB else (595.276, 841.89)

    blank_page = _create_blank_page(width, height)

    # Costruisci il writer e copia tutto
    writer = PdfWriter()

    # ── Pagine (inserendo la bianca all'indice giusto) ──
    for i in range(total_pages):
        if i == insert_idx:
            writer.add_page(blank_page)
        writer.add_page(reader.pages[i])

    # Se la pagina va in fondo (insert_idx == total_pages)
    if insert_idx >= total_pages:
        writer.add_page(blank_page)

    # ── Metadati ──
    meta = reader.metadata
    if meta:
        meta_dict = {}
        for key in meta:
            # pypdf restituisce chiavi come '/Title', '/Author', ecc.
            try:
                value = meta[key]
                if value:
                    meta_dict[key] = str(value)
            except Exception:
                pass
        if meta_dict:
            writer.add_metadata(meta_dict)

    # ── Segnalibri / Outline ──
    # pypdf clona automaticamente le outline quando le pagine vengono aggiunte;
    # tuttavia i riferimenti alle pagine potrebbero slittare.
    # Per sicurezza, copiamo l'outline raw aggiornando i riferimenti.
    _copy_outlines(reader, writer, insert_idx)

    # ── Output path ──
    if output_path is None:
        stem = path.stem
        suffix = path.suffix
        output_path = str(path.parent / f"{stem}_modified{suffix}")

    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path


def _copy_outlines(reader: PdfReader, writer: PdfWriter, insert_idx: int):
    """
    Ricopia i segnalibri (bookmarks/outlines) dal reader al writer,
    aggiornando i numeri di pagina per tenere conto della pagina inserita.
    """
    try:
        outlines = reader.outline
        if not outlines:
            return

        def _add_outline_items(items, parent=None):
            for item in items:
                if isinstance(item, list):
                    # È un gruppo di figli — il parent è l'ultimo bookmark aggiunto
                    # non facciamo nulla qui, vengono gestiti nella chiamata ricorsiva
                    continue
                try:
                    # Recupera il numero di pagina originale
                    orig_page_num = reader.get_destination_page_number(item)
                    # Shift: se la pagina originale è >= insert_idx, scala di 1
                    new_page_num = orig_page_num + (1 if orig_page_num >= insert_idx else 0)
                    new_page_num = min(new_page_num, len(writer.pages) - 1)

                    title = item.title if hasattr(item, 'title') else str(item)
                    if parent:
                        writer.add_outline_item(title, new_page_num, parent=parent)
                    else:
                        writer.add_outline_item(title, new_page_num)
                except Exception:
                    pass

        _add_outline_items(outlines)
    except Exception:
        # Se i segnalibri non si riescono a copiare, procediamo senza
        pass


# ─────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────

def cmd_count(args):
    try:
        n = count_pages(args.pdf)
        print(f"📄  {args.pdf}  →  {n} pagina{'e' if n != 1 else ''}")
    except (FileNotFoundError, ValueError) as e:
        print(f"Errore: {e}", file=sys.stderr)
        sys.exit(1)


def cmd_add_blank(args):
    try:
        total = count_pages(args.pdf)
        print(f"📄  PDF originale: {total} pagine")
        print(f"➕  Inserisco pagina bianca in posizione {args.page_number}...")

        out = add_blank_page(args.pdf, args.page_number, args.output)

        new_total = count_pages(out)
        print(f"✅  Salvato: {out}  ({new_total} pagine)")
    except (FileNotFoundError, ValueError) as e:
        print(f"Errore: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Errore inatteso: {e}", file=sys.stderr)
        import traceback; traceback.print_exc()
        sys.exit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pdfm",
        description="pdfm – PDF Modifier: modifica PDF preservando testo, annotazioni e metadati.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    subparsers = parser.add_subparsers(dest="command", metavar="<comando>")
    subparsers.required = True

    # ── count ──
    p_count = subparsers.add_parser(
        "count",
        help="Conta le pagine di un PDF",
        description="Conta le pagine di un PDF."
    )
    p_count.add_argument("pdf", metavar="<file.pdf>", help="Path del PDF")
    p_count.set_defaults(func=cmd_count)

    # ── add_blank_page ──
    p_blank = subparsers.add_parser(
        "add_blank_page",
        help="Inserisce una pagina bianca in una posizione specifica",
        description=(
            "Inserisce una pagina bianca PRIMA di <page_number> (1-based).\n"
            "Preserva testo selezionabile, annotazioni/scarabocchi e metadati."
        )
    )
    p_blank.add_argument("pdf", metavar="<file.pdf>", help="Path del PDF di input")
    p_blank.add_argument("page_number", metavar="<page_number>", type=int,
                         help="Posizione (1-based) dove inserire la pagina bianca")
    p_blank.add_argument("--output", "-o", metavar="<out.pdf>", default=None,
                         help="Path del PDF di output (default: <nome>_modified.pdf)")
    p_blank.set_defaults(func=cmd_add_blank)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()