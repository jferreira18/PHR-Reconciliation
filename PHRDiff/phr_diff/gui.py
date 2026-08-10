from __future__ import annotations

import queue
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import BooleanVar, StringVar, Tk, filedialog, messagebox, ttk

from .compare import compare_receipts
from .parser import parse_hand_receipt
from .paths import default_reports_root
from .report import generate_report, summary
from .validation import attach_validation_warnings


class PHRDiffApp:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title("PHR Diff")
        self.root.geometry("760x560")
        self.root.minsize(680, 500)

        default_output = default_reports_root()
        self.old_pdf = StringVar()
        self.new_pdf = StringVar()
        self.output_dir = StringVar(value=str(default_output))
        self.include_metadata = BooleanVar(value=False)
        self.full_pages = BooleanVar(value=False)
        self.open_report = BooleanVar(value=True)
        self.status = StringVar(value="Choose baseline and current PHR PDFs.")
        self.queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.running = False
        self.latest_report: Path | None = None

        self._build_ui()
        self.root.after(100, self._poll_queue)

    def _build_ui(self) -> None:
        padding = {"padx": 16, "pady": 8}
        frame = ttk.Frame(self.root)
        frame.pack(fill="both", expand=True)

        title = ttk.Label(frame, text="Primary Hand Receipt Diff", font=("Segoe UI", 16, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", padx=16, pady=(16, 8))

        self._file_row(frame, 1, "Baseline PDF", self.old_pdf, self._browse_old)
        self._file_row(frame, 2, "Current PDF", self.new_pdf, self._browse_new)
        self._folder_row(frame, 3, "Output Folder", self.output_dir, self._browse_output)

        options = ttk.LabelFrame(frame, text="Options")
        options.grid(row=4, column=0, columnspan=3, sticky="ew", **padding)
        ttk.Checkbutton(options, text="Include metadata-only changes", variable=self.include_metadata).grid(
            row=0, column=0, sticky="w", padx=10, pady=8
        )
        ttk.Checkbutton(options, text="Generate full-page view", variable=self.full_pages).grid(
            row=0, column=1, sticky="w", padx=10, pady=8
        )
        ttk.Checkbutton(options, text="Open report when finished", variable=self.open_report).grid(
            row=0, column=2, sticky="w", padx=10, pady=8
        )

        actions = ttk.Frame(frame)
        actions.grid(row=5, column=0, columnspan=3, sticky="ew", **padding)
        self.run_button = ttk.Button(actions, text="Generate Report", command=self._start)
        self.run_button.pack(side="left")
        self.open_button = ttk.Button(actions, text="Open Last Report", command=self._open_latest, state="disabled")
        self.open_button.pack(side="left", padx=(8, 0))

        ttk.Label(frame, textvariable=self.status).grid(row=6, column=0, columnspan=3, sticky="ew", **padding)
        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.grid(row=7, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 8))

        log_frame = ttk.LabelFrame(frame, text="Run Log")
        log_frame.grid(row=8, column=0, columnspan=3, sticky="nsew", **padding)
        self.log = ttk.Treeview(log_frame, columns=("message",), show="tree", height=10)
        self.log.pack(fill="both", expand=True, padx=8, pady=8)

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(8, weight=1)

    def _file_row(self, parent: ttk.Frame, row: int, label: str, variable: StringVar, command) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=16, pady=8)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=8, pady=8)
        ttk.Button(parent, text="Browse", command=command).grid(row=row, column=2, sticky="e", padx=16, pady=8)

    def _folder_row(self, parent: ttk.Frame, row: int, label: str, variable: StringVar, command) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", padx=16, pady=8)
        ttk.Entry(parent, textvariable=variable).grid(row=row, column=1, sticky="ew", padx=8, pady=8)
        ttk.Button(parent, text="Choose", command=command).grid(row=row, column=2, sticky="e", padx=16, pady=8)

    def _browse_old(self) -> None:
        path = filedialog.askopenfilename(title="Choose baseline PHR PDF", filetypes=[("PDF files", "*.pdf")])
        if path:
            self.old_pdf.set(path)

    def _browse_new(self) -> None:
        path = filedialog.askopenfilename(title="Choose current PHR PDF", filetypes=[("PDF files", "*.pdf")])
        if path:
            self.new_pdf.set(path)

    def _browse_output(self) -> None:
        path = filedialog.askdirectory(title="Choose output folder")
        if path:
            self.output_dir.set(path)

    def _start(self) -> None:
        if self.running:
            return
        old_pdf = Path(self.old_pdf.get())
        new_pdf = Path(self.new_pdf.get())
        output_parent = Path(self.output_dir.get())
        if not old_pdf.is_file():
            messagebox.showerror("Missing baseline PDF", "Choose a valid baseline PDF.")
            return
        if not new_pdf.is_file():
            messagebox.showerror("Missing current PDF", "Choose a valid current PDF.")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = output_parent / f"phr_report_{timestamp}"
        self.running = True
        self.latest_report = None
        self.run_button.config(state="disabled")
        self.open_button.config(state="disabled")
        self.progress.start(10)
        self.status.set("Running comparison...")
        self.log.delete(*self.log.get_children())

        worker = threading.Thread(
            target=self._run_pipeline,
            args=(old_pdf, new_pdf, output_dir),
            daemon=True,
        )
        worker.start()

    def _run_pipeline(self, old_pdf: Path, new_pdf: Path, output_dir: Path) -> None:
        try:
            self._emit("Parsing baseline PHR...")
            old_receipt = parse_hand_receipt(old_pdf)
            self._emit(f"Baseline records: {len(old_receipt.items)}")

            self._emit("Parsing current PHR...")
            new_receipt = parse_hand_receipt(new_pdf)
            self._emit(f"Current records: {len(new_receipt.items)}")

            self._emit("Comparing structured records...")
            reconciliation = compare_receipts(
                old_receipt,
                new_receipt,
                include_metadata_changes=self.include_metadata.get(),
            )
            attach_validation_warnings(reconciliation, old_receipt, new_receipt)

            self._emit("Rendering visual report...")
            index = generate_report(
                old_pdf,
                new_pdf,
                old_receipt,
                new_receipt,
                reconciliation,
                output_dir,
                full_pages=self.full_pages.get(),
            )
            stats = summary(reconciliation)
            self._emit(f"Detected changes: {stats['changes']}")
            self._emit(f"Validation warnings: {stats['validation_warnings']}")
            self._emit(f"Report: {index}")
            self.queue.put(("done", str(index)))
        except Exception as exc:
            self.queue.put(("error", str(exc)))

    def _emit(self, message: str) -> None:
        self.queue.put(("log", message))

    def _poll_queue(self) -> None:
        while True:
            try:
                kind, message = self.queue.get_nowait()
            except queue.Empty:
                break
            if kind == "log":
                self.log.insert("", "end", text=message)
                self.log.yview_moveto(1)
            elif kind == "done":
                self.running = False
                self.progress.stop()
                self.run_button.config(state="normal")
                self.latest_report = Path(message)
                self.open_button.config(state="normal")
                self.status.set("Report generated successfully.")
                if self.open_report.get():
                    webbrowser.open(self.latest_report.resolve().as_uri())
                messagebox.showinfo("PHR Diff", f"Report generated:\n{self.latest_report}")
            elif kind == "error":
                self.running = False
                self.progress.stop()
                self.run_button.config(state="normal")
                self.status.set("Report generation failed.")
                messagebox.showerror("PHR Diff failed", message)
        self.root.after(100, self._poll_queue)

    def _open_latest(self) -> None:
        if self.latest_report and self.latest_report.exists():
            webbrowser.open(self.latest_report.resolve().as_uri())


def main() -> None:
    root = Tk()
    PHRDiffApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
