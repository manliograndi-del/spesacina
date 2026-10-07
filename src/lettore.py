"""Trasforma un PDF di volantino in immagini leggibili (una per pagina)
e in un file di testo per pagina, letto dall'OCR.
"""

import json
import subprocess
import sys
from pathlib import Path

import fitz  # pymupdf

RADICE = Path(__file__).resolve().parent.parent
USCITA = RADICE / "pg" / "lidl-prova"
LARGHEZZA_MAX = 1400
DPI = 150


def ocr(immagine: Path) -> str:
    try:
        r = subprocess.run(
            ["tesseract", str(immagine), "stdout", "-l", "ita"],
            capture_output=True, text=True, timeout=180,
        )
        return r.stdout or ""
    except Exception as e:
        print(f"   OCR non disponibile ({e})")
        return ""


def trova_pdf(cartella: Path) -> Path:
    pdfs = sorted(p for p in cartella.glob("*.pdf") if not p.name.startswith("."))
    if not pdfs:
        print(f"Nessun PDF in {cartella}")
        sys.exit(1)
    if len(pdfs) > 1:
        print(f"Trovati {len(pdfs)} PDF, uso il primo: {pdfs[0].name}")
    return pdfs[0]


def main():
    cartella = Path(sys.argv[1]) if len(sys.argv) > 1 else RADICE
    if not cartella.is_absolute():
        cartella = RADICE / cartella

    pdf = trova_pdf(cartella)
    print(f"PDF: {pdf.name} ({pdf.stat().st_size // 1024} KB)")

    USCITA.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf)
    print(f"Pagine: {doc.page_count}")

    indice = []
    for i in range(doc.page_count):
        pagina = doc.load_page(i)
        testo_nativo = pagina.get_text("text").strip()

        zoom = DPI / 72
        pix = pagina.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        if pix.width > LARGHEZZA_MAX:
            fattore = LARGHEZZA_MAX / pix.width
            pix = pagina.get_pixmap(matrix=fitz.Matrix(zoom * fattore, zoom * fattore))

        img_path = USCITA / f"pagina-{i + 1:02d}.jpg"
        pix.save(str(img_path), jpg_quality=80)

        testo = testo_nativo
        if len(testo) < 40:
            testo = ocr(img_path)

        (USCITA / f"pagina-{i + 1:02d}.txt").write_text(testo, encoding="utf-8")

        indice.append({
            "pagina": i + 1,
            "immagine": img_path.name,
            "testo_len": len(testo),
            "prime_parole": " ".join(testo.split()[:25]),
        })
        print(f"  pagina {i + 1}: {pix.width}x{pix.height}, {len(testo)} caratteri di testo")

    doc.close()

    (USCITA / "indice.json").write_text(
        json.dumps({"pdf": pdf.name, "pagine": indice}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nFatto. Guarda in pg/lidl-prova/")


if __name__ == "__main__":
    main()
