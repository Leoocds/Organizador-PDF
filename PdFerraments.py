import os
import math
import shutil
import subprocess
import sys
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, PhotoImage
import customtkinter as ctk
from PIL import Image, ImageTk

# ========== CONFIGURAÇÕES ==========
TARGET_SIZE_MB = 3.0
QUALITY_PRESET = "/ebook"
MAX_ITERATIONS = 10

# ===================================

# Ghostscript
def find_ghostscript_executable():
    from shutil import which
    candidates = ["gswin64c", "gswin32c", "gs"]
    for c in candidates:
        if which(c):
            return c
    return None

GS_EXEC = find_ghostscript_executable()
if not GS_EXEC:
    raise SystemExit("Ghostscript não encontrado no PATH. Instale e adicione.")

# ======= COMPACTAR =======

def compactar_pdf(input_path, output_path, quality=QUALITY_PRESET):
    cmd = [
        GS_EXEC,
        "-sDEVICE=pdfwrite",
        f"-dPDFSETTINGS={quality}",
        "-dCompatibilityLevel=1.4",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_path}",
        input_path,
    ]
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        startupinfo=startupinfo
    )
    
# ========== DIVIDIR ========== 

def file_size_mb(path):
    return os.path.getsize(path) / (1024 * 1024)

def extract_pages_to_pdf(reader, start_idx, end_idx, out_path):
    writer = PdfWriter()
    for i in range(start_idx, end_idx):
        writer.add_page(reader.pages[i])
    with open(out_path, "wb") as f:
        writer.write(f)

def try_split_until_ok(input_pdf, dest_dir, base_name, log_func=print):
    reader = PdfReader(input_pdf)
    total_pages = len(reader.pages)
    original_size = file_size_mb(input_pdf)
    initial_N = max(1, math.ceil(original_size / TARGET_SIZE_MB))
    N = initial_N
    attempts = 0

    while True:
        attempts += 1
        if attempts > MAX_ITERATIONS:
            N = total_pages
        temp_try_dir = os.path.join(dest_dir, f".temp_split_try_{N}")
        os.makedirs(temp_try_dir, exist_ok=True)
        parts = []
        ok = True
        base_per_block = total_pages // N
        remainder = total_pages % N
        start = 0

        for part_idx in range(N):
            pages_count = base_per_block + (1 if part_idx < remainder else 0)
            end = start + pages_count
            if pages_count <= 0:
                start = end
                continue
            temp_part_raw = os.path.join(temp_try_dir, f"{base_name}_raw_part{part_idx+1}.pdf")
            temp_part_compact = os.path.join(temp_try_dir, f"{base_name}_part{part_idx+1}.pdf")
            extract_pages_to_pdf(reader, start, end, temp_part_raw)
            try:
                compactar_pdf(temp_part_raw, temp_part_compact)
            except:
                ok = False
                parts.append((temp_part_raw, None))
                start = end
                continue

            size_mb = file_size_mb(temp_part_compact)
            parts.append((temp_part_raw, temp_part_compact, size_mb))
            if size_mb > TARGET_SIZE_MB:
                ok = False
            start = end

        if ok:
            final_paths = []
            for item in parts:
                compacted = item[1]
                final_name = os.path.basename(compacted)
                final_path = os.path.join(dest_dir, final_name)
                shutil.move(compacted, final_path)
                final_paths.append(final_path)
            shutil.rmtree(temp_try_dir, ignore_errors=True)
            return final_paths
        else:
            shutil.rmtree(temp_try_dir, ignore_errors=True)
            if N >= total_pages:
                final_paths = []
                per_page_temp = os.path.join(dest_dir, ".temp_per_page")
                os.makedirs(per_page_temp, exist_ok=True)
                for i in range(total_pages):
                    temp_raw = os.path.join(per_page_temp, f"{base_name}_pg{i+1}_raw.pdf")
                    temp_comp = os.path.join(per_page_temp, f"{base_name}_pg{i+1}.pdf")
                    extract_pages_to_pdf(reader, i, i+1, temp_raw)
                    compactar_pdf(temp_raw, temp_comp)
                    if file_size_mb(temp_comp) <= TARGET_SIZE_MB:
                        final_dest = os.path.join(dest_dir, os.path.basename(temp_comp))
                        shutil.move(temp_comp, final_dest)
                        final_paths.append(final_dest)
                    else:
                        final_dest = os.path.join(dest_dir, os.path.basename(temp_comp))
                        shutil.move(temp_comp, final_dest)
                        final_paths.append(final_dest)
                shutil.rmtree(per_page_temp, ignore_errors=True)
                return final_paths
            N = min(total_pages, N * 2)
            
# ======= PROCESSAR =======

def process_folder(folder_path, log_func=print):
    folder_path = os.path.normpath(folder_path)
    nome_pasta = os.path.basename(folder_path)
    downloads = os.path.join(Path.home(), "Downloads")
    dest_root = os.path.join(downloads, f"{nome_pasta} - Compactado")
    os.makedirs(dest_root, exist_ok=True)

    for entry in sorted(os.listdir(folder_path)):
        if not entry.lower().endswith(".pdf"):
            continue
        full_input = os.path.join(folder_path, entry)
        base_name = Path(entry).stem
    
        log_func(f"\nProcessando: {entry}")
        temp_whole = os.path.join(dest_root, entry)
        compactar_pdf(full_input, temp_whole)
        try:
            size_whole = file_size_mb(temp_whole)
        except FileNotFoundError:
            log_func("  Erro ao gerar arquivo compactado inteiro. Pulando.")
            continue

        if size_whole <= TARGET_SIZE_MB:
            log_func(f"  Arquivo inteiro cabe: {size_whole:.2f} MB -> salvo em {dest_root}")
            continue
        else:
            os.remove(temp_whole)
            dest_sub = os.path.join(dest_root, base_name)
            os.makedirs(dest_sub, exist_ok=True)
            log_func(f"  Arquivo inteiro tem {size_whole:.2f} MB -> iniciando divisão inteligente...")
            final_parts = try_split_until_ok(full_input, dest_sub, base_name)
            log_func(f"  Criadas {len(final_parts)} parte(s) em: {dest_sub}")
            for p in final_parts:
                try:
                    log_func(f"    - {os.path.basename(p)} ({file_size_mb(p):.2f} MB)")
                except:
                    pass
    log_func(f"\nConcluído. Saída em: {dest_root}")

# ========== INTERFACE ==========

def log_func(msg):
    log_text.insert(tk.END, msg + "\n")
    log_text.see(tk.END)  
    root.update()

def selecionar_pasta():
    folder = filedialog.askdirectory()
    if folder:
        pasta_var.set(folder)

def iniciar_processamento():
    folder = pasta_var.get()
    if not folder or not os.path.exists(folder):
        messagebox.showerror("Erro", "Selecione uma pasta válida!")
        return
    global TARGET_SIZE_MB
    TARGET_SIZE_MB = target_var.get()
    log_text.delete(1.0, tk.END)
    root.update()
    try:
        process_folder(folder, log_func=log_func)
    except Exception as e:
        messagebox.showerror("Erro", f"Ocorreu um erro:\n{e}")
    else:
        messagebox.showinfo("Sucesso", "Todos os PDFs foram processados!")

root = tk.Tk()
root.title("Organizador de PDFs")

icon_image_png = Image.open(r'S:\Users\leonardo.pedroso\Downloads\PdFerraments.png')
icon_image_tk = ImageTk.PhotoImage(icon_image_png)

root.iconphoto(True, icon_image_tk)

image_path = Image.open("S:/Users/leonardo.pedroso/Downloads/PdFerraments.png")
image_path = image_path.resize((80, 80))
img = ImageTk.PhotoImage(image_path)
label = tk.Label(root, image=img).pack()

pasta_var = tk.StringVar()

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

frame = tk.Frame(root)
frame.pack(padx=10, pady=10)

tk.Label(frame, text="Pasta de PDFs:").grid(row=0, column=0, sticky="w")
tk.Entry(frame, textvariable=pasta_var, width=50).grid(row=0, column=1, padx=5)
tk.Button(frame, text="Selecionar Pasta", command=selecionar_pasta).grid(row=0, column=2)

target_var = tk.DoubleVar(value=3.0)  
tk.Label(frame, text="Tamanho máximo por arquivo (MB):").grid(row=1, column=0, sticky="w")
tk.Scale(frame, from_=1, to=25, orient="horizontal", variable=target_var, bg="white", resolution=0.5, length=200).grid(row=1, column=1, padx=5)

tk.Button(frame, text="Iniciar Compactação", command=iniciar_processamento, bg="blue", fg="white").grid(row=2, column=0, columnspan=3, pady=10)

log_text = scrolledtext.ScrolledText(root, width=80, height=20)
log_text.pack(padx=10, pady=10)

root.mainloop()

