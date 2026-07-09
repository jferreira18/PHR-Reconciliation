from __future__ import annotations

import contextlib
import io
import os
import queue
import sys
import threading
import traceback
from pathlib import Path

from run_pipeline import DEFAULT_OUTPUT, build_output, run_unit_tests


REPO_ROOT = Path(__file__).resolve().parents[2]


def configure_tk_paths() -> None:
    candidate_roots = []
    if getattr(sys, "frozen", False):
        candidate_roots.append(Path(getattr(sys, "_MEIPASS")) / "tcl")
    candidate_roots.extend(
        [
            Path(sys.base_prefix) / "tcl",
            Path(sys.prefix) / "tcl",
        ]
    )

    for root in candidate_roots:
        tcl_dir = root / "tcl8.6"
        tk_dir = root / "tk8.6"
        if (tcl_dir / "init.tcl").exists() and (tk_dir / "tk.tcl").exists():
            os.environ.setdefault("TCL_LIBRARY", str(tcl_dir))
            os.environ.setdefault("TK_LIBRARY", str(tk_dir))
            return


configure_tk_paths()

from tkinter import filedialog, messagebox
import tkinter as tk
from tkinter import ttk


class PHRReconcileApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PHR to PSD Reconciliation")
        self.geometry("820x560")
        self.minsize(760, 500)

        self.phr_pdf = tk.StringVar()
        self.phr_xlsx = tk.StringVar()
        self.psd_xlsx = tk.StringVar()
        self.status = tk.StringVar(value="Select the three source files.")
        self.output_path = REPO_ROOT / DEFAULT_OUTPUT
        self.messages: queue.Queue[tuple[str, str]] = queue.Queue()

        self._build_layout()
        self.after(100, self._drain_messages)

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        header = ttk.Frame(self, padding=(18, 16, 18, 8))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)

        title = ttk.Label(header, text="PHR to PSD Reconciliation", font=("Segoe UI", 15, "bold"))
        title.grid(row=0, column=0, sticky="w")
        subtitle = ttk.Label(
            header,
            text="Choose the PHR PDF, PHR XLSX, and PSD PULL workbook. The final CSV is generated automatically.",
        )
        subtitle.grid(row=1, column=0, sticky="w", pady=(4, 0))

        inputs = ttk.Frame(self, padding=(18, 8))
        inputs.grid(row=1, column=0, sticky="ew")
        inputs.columnconfigure(1, weight=1)

        self._add_file_row(inputs, 0, "PHR PDF", self.phr_pdf, [("PDF files", "*.pdf"), ("All files", "*.*")])
        self._add_file_row(
            inputs,
            1,
            "PHR XLSX",
            self.phr_xlsx,
            [("Excel workbooks", "*.xlsx *.xlsm *.xls"), ("All files", "*.*")],
        )
        self._add_file_row(
            inputs,
            2,
            "PSD PULL",
            self.psd_xlsx,
            [("Excel workbooks", "*.xlsx *.xlsm *.xls"), ("All files", "*.*")],
        )

        log_frame = ttk.Frame(self, padding=(18, 8))
        log_frame.grid(row=2, column=0, sticky="nsew")
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)

        self.log = tk.Text(log_frame, wrap="word", height=14, state="disabled", font=("Consolas", 10))
        self.log.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.log.configure(yscrollcommand=scroll.set)

        footer = ttk.Frame(self, padding=(18, 8, 18, 16))
        footer.grid(row=3, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)

        ttk.Label(footer, textvariable=self.status).grid(row=0, column=0, sticky="w")
        self.copy_log_button = ttk.Button(footer, text="Copy Log", command=self._copy_log, state="disabled")
        self.copy_log_button.grid(row=0, column=1, padx=(8, 0))
        self.open_folder_button = ttk.Button(footer, text="Open Output Folder", command=self._open_output_folder, state="disabled")
        self.open_folder_button.grid(row=0, column=2, padx=(8, 0))
        self.open_file_button = ttk.Button(footer, text="Open CSV", command=self._open_output_file, state="disabled")
        self.open_file_button.grid(row=0, column=3, padx=(8, 0))
        self.run_button = ttk.Button(footer, text="Run", command=self._run)
        self.run_button.grid(row=0, column=4, padx=(8, 0))

    def _add_file_row(
        self,
        parent: ttk.Frame,
        row: int,
        label: str,
        variable: tk.StringVar,
        filetypes: list[tuple[str, str]],
    ) -> None:
        ttk.Label(parent, text=label, width=10).grid(row=row, column=0, sticky="w", pady=4)
        entry = ttk.Entry(parent, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", padx=(8, 8), pady=4)
        ttk.Button(
            parent,
            text="Browse",
            command=lambda: self._browse(variable, filetypes),
        ).grid(row=row, column=2, pady=4)

    def _browse(self, variable: tk.StringVar, filetypes: list[tuple[str, str]]) -> None:
        selected = filedialog.askopenfilename(parent=self, filetypes=filetypes)
        if selected:
            variable.set(selected)

    def _run(self) -> None:
        paths = {
            "PHR PDF": self.phr_pdf.get().strip(),
            "PHR XLSX": self.phr_xlsx.get().strip(),
            "PSD PULL": self.psd_xlsx.get().strip(),
        }
        missing = [name for name, value in paths.items() if not value]
        if missing:
            text = "Missing files: " + ", ".join(missing)
            self._record_user_error(text)
            messagebox.showerror("Missing files", text, parent=self)
            return

        missing_on_disk = [name for name, value in paths.items() if not Path(value).exists()]
        if missing_on_disk:
            text = "File not found. Check: " + ", ".join(missing_on_disk)
            self._record_user_error(text)
            messagebox.showerror("File not found", text, parent=self)
            return

        self._set_running(True)
        self._clear_log()
        self._append_log("Running unit tests and building final output...\n")
        worker = threading.Thread(target=self._run_pipeline_worker, args=(paths,), daemon=True)
        worker.start()

    def _run_pipeline_worker(self, paths: dict[str, str]) -> None:
        stdout = io.StringIO()
        stderr = io.StringIO()
        input_report = "\n".join(f"{name}: {value}" for name, value in paths.items())
        try:
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                run_unit_tests()
                build_output(
                    phr_pdf=Path(paths["PHR PDF"]),
                    phr_xlsx=Path(paths["PHR XLSX"]),
                    psd_xlsx=Path(paths["PSD PULL"]),
                    output_path=self.output_path,
                )
        except BaseException:
            error_report = (
                "\n=== ERROR REPORT ===\n"
                f"{input_report}\n\n"
                f"{traceback.format_exc()}"
                "=== END ERROR REPORT ===\n"
            )
            self.messages.put(("log", stdout.getvalue()))
            self.messages.put(("log", stderr.getvalue()))
            self.messages.put(("log", error_report))
            self.messages.put(("error", "Run failed. Use Copy Log and send the details for troubleshooting."))
            return

        self.messages.put(("log", stdout.getvalue()))
        self.messages.put(("log", stderr.getvalue()))
        self.messages.put(("success", f"Done. Final output: {self.output_path}"))

    def _drain_messages(self) -> None:
        while True:
            try:
                kind, text = self.messages.get_nowait()
            except queue.Empty:
                break

            if kind == "log" and text:
                self._append_log(text)
            elif kind == "success":
                self.status.set(text)
                self._set_running(False)
                self.open_file_button.configure(state="normal")
                self.open_folder_button.configure(state="normal")
                messagebox.showinfo("Complete", text, parent=self)
            elif kind == "error":
                self.status.set(text)
                self._set_running(False)
                messagebox.showerror("Run failed", text, parent=self)

        self.after(100, self._drain_messages)

    def _set_running(self, running: bool) -> None:
        self.run_button.configure(state="disabled" if running else "normal")
        if running:
            self.open_file_button.configure(state="disabled")
            self.open_folder_button.configure(state="disabled")
            self.status.set("Working...")

    def _clear_log(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")
        self.copy_log_button.configure(state="disabled")

    def _append_log(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text)
        self.log.see("end")
        self.log.configure(state="disabled")
        self.copy_log_button.configure(state="normal")

    def _record_user_error(self, text: str) -> None:
        self._clear_log()
        self._append_log(text + "\n")
        self.status.set(text)

    def _copy_log(self) -> None:
        text = self.log.get("1.0", "end").strip()
        if not text:
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status.set("Log copied to clipboard.")

    def _open_output_file(self) -> None:
        if self.output_path.exists():
            os.startfile(self.output_path)

    def _open_output_folder(self) -> None:
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        os.startfile(self.output_path.parent)


def main() -> None:
    if "--smoke-test" in sys.argv:
        tk.Tcl().eval("info patchlevel")
        run_unit_tests()
        return

    app = PHRReconcileApp()
    app.mainloop()


if __name__ == "__main__":
    main()
