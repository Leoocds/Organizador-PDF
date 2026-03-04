import os
import math
import shutil
import subprocess
import sys
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# ================= CONFIGURAÇÕES =================
TARGET_SIZE_MB = 3.0
QUALITY_PRESET = "/ebook"
MAX_ITERATIONS = 10

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ================= GHOSTSCRIPT =================
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

# ================= UTILITÁRIOS =================
def file_size_mb(path):
    return os.path.getsize(path) / (1024 * 1024)

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

def extract_pages_to_pdf(reader, start_idx, end_idx, out_path):
    writer = PdfWriter()
    for i in range(start_idx, end_idx):
        writer.add_page(reader.pages[i])
    with open(out_path, "wb") as f:
        writer.write(f)

# ================= DIVISÃO INTELIGENTE =================
def try_split_until_ok(input_pdf, dest_dir, base_name, log_func):
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

            temp_raw = os.path.join(temp_try_dir, f"{base_name}_raw_{part_idx+1}.pdf")
            temp_comp = os.path.join(temp_try_dir, f"{base_name}_part{part_idx+1}.pdf")

            extract_pages_to_pdf(reader, start, end, temp_raw)
            compactar_pdf(temp_raw, temp_comp)

            size_mb = file_size_mb(temp_comp)
            parts.append((temp_raw, temp_comp, size_mb))

            if size_mb > TARGET_SIZE_MB:
                ok = False

            start = end

        if ok:
            final_paths = []
            for _, comp, _ in parts:
                final_path = os.path.join(dest_dir, os.path.basename(comp))
                shutil.move(comp, final_path)
                final_paths.append(final_path)

            shutil.rmtree(temp_try_dir, ignore_errors=True)
            return final_paths

        shutil.rmtree(temp_try_dir, ignore_errors=True)

        if N >= total_pages:
            return []
        N = min(total_pages, N * 2)

# ================= PROCESSAMENTO =================
def process_folder(folder_path, log_func):
    folder_path = os.path.normpath(folder_path)
    nome_pasta = os.path.basename(folder_path)
    downloads = os.path.join(Path.home(), "Downloads")
    dest_root = os.path.join(downloads, f"{nome_pasta} - Compactado")
    os.makedirs(dest_root, exist_ok=True)

    pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]
    total_files = len(pdf_files)
    current = 0

    for entry in sorted(pdf_files):
        current += 1
        progress_bar.set(current / total_files)
        root.update()

        full_input = os.path.join(folder_path, entry)
        base_name = Path(entry).stem

        log_func(f"Processando: {entry}")

        temp_whole = os.path.join(dest_root, entry)
        compactar_pdf(full_input, temp_whole)

        if not os.path.exists(temp_whole):
            log_func("Erro ao compactar.")
            continue

        size_whole = file_size_mb(temp_whole)

        if size_whole <= TARGET_SIZE_MB:
            log_func(f"✔ Compactado: {size_whole:.2f} MB")
            continue

        os.remove(temp_whole)

        dest_sub = os.path.join(dest_root, base_name)
        os.makedirs(dest_sub, exist_ok=True)

        final_parts = try_split_until_ok(full_input, dest_sub, base_name, log_func)
        log_func(f"✔ Dividido em {len(final_parts)} partes")

    log_func("Processamento concluído.")

# ================= INTERFACE =================
root = ctk.CTk()
root.title("Organizador Corporativo de PDFs")
root.geometry("820x600")
root.resizable(False, False)

main_frame = ctk.CTkFrame(root, corner_radius=15)
main_frame.pack(padx=20, pady=20, fill="both", expand=True)

title_label = ctk.CTkLabel(
    main_frame,
    text="Organizador Corporativo de PDFs",
    font=("Segoe UI", 20, "bold")
)
title_label.pack(pady=(20, 5))

subtitle_label = ctk.CTkLabel(
    main_frame,
    text="Compactação inteligente com divisão automática",
    font=("Segoe UI", 12)
)
subtitle_label.pack(pady=(0, 20))

config_frame = ctk.CTkFrame(main_frame)
config_frame.pack(padx=20, pady=10, fill="x")

pasta_var = tk.StringVar()
target_var = tk.DoubleVar(value=3.0)

def selecionar_pasta():
    folder = filedialog.askdirectory()
    if folder:
        pasta_var.set(folder)

def log_func(msg):
    log_text.insert("end", msg + "\n")
    log_text.see("end")
    root.update()

def iniciar_processamento():
    folder = pasta_var.get()
    if not folder or not os.path.exists(folder):
        messagebox.showerror("Erro", "Selecione uma pasta válida!")
        return

    global TARGET_SIZE_MB
    TARGET_SIZE_MB = target_var.get()

    log_text.delete("1.0", "end")
    progress_bar.set(0)

    try:
        process_folder(folder, log_func)
        messagebox.showinfo("Sucesso", "Todos os PDFs foram processados!")
    except Exception as e:
        messagebox.showerror("Erro", str(e))

ctk.CTkLabel(config_frame, text="Pasta de PDFs:").grid(row=0, column=0, padx=10, pady=10, sticky="w")

entry_pasta = ctk.CTkEntry(config_frame, textvariable=pasta_var, width=400)
entry_pasta.grid(row=0, column=1, padx=10, pady=10)

ctk.CTkButton(
    config_frame,
    text="Selecionar",
    width=120,
    command=selecionar_pasta
).grid(row=0, column=2, padx=10)

ctk.CTkLabel(config_frame, text="Tamanho máximo (MB):").grid(row=1, column=0, padx=10, pady=10, sticky="w")

slider = ctk.CTkSlider(
    config_frame,
    from_=1,
    to=25,
    variable=target_var,
    number_of_steps=48,
    width=300
)
slider.grid(row=1, column=1, padx=10)

size_label = ctk.CTkLabel(config_frame, textvariable=target_var)
size_label.grid(row=1, column=2)

start_button = ctk.CTkButton(
    main_frame,
    text="Iniciar Processamento",
    height=45,
    font=("Segoe UI", 14, "bold"),
    fg_color="#1f2937",
    hover_color="#111827",
    command=iniciar_processamento
)
start_button.pack(pady=20)

progress_bar = ctk.CTkProgressBar(main_frame, width=600)
progress_bar.pack(pady=10)
progress_bar.set(0)

log_text = ctk.CTkTextbox(
    main_frame,
    width=760,
    height=200,
    corner_radius=10
)
log_text.pack(padx=20, pady=20)

root.mainloop()