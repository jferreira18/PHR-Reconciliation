from __future__ import annotations

import cgi
import html
import shutil
import sys
import threading
import uuid
import webbrowser
from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

from .compare import compare_receipts
from .parser import parse_hand_receipt
from .report import generate_report, summary
from .validation import attach_validation_warnings, tagged_validation_warnings


APP_TITLE = "PHR Diff"


def reports_root() -> Path:
    root = Path.home() / "Documents" / "PHR Diff Reports"
    root.mkdir(parents=True, exist_ok=True)
    return root


def page(title: str, body: str) -> bytes:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root {{
  color-scheme: dark;
  --bg: #0d1117;
  --panel: #161b22;
  --border: #30363d;
  --text: #e6edf3;
  --muted: #8b949e;
  --accent: #2f81f7;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--text);
}}
main {{ max-width: 900px; margin: 0 auto; padding: 30px 18px; }}
h1 {{ margin: 0 0 6px; font-size: 26px; }}
p {{ color: var(--muted); }}
.panel {{
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--panel);
  padding: 18px;
  margin-top: 18px;
}}
label {{ display: block; margin: 14px 0 6px; font-weight: 600; }}
input[type=file], input[type=text] {{
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 10px;
  background: #0d1117;
  color: var(--text);
}}
.checks {{ display: flex; gap: 18px; flex-wrap: wrap; margin: 14px 0; }}
.checks label {{ margin: 0; font-weight: 400; }}
button, .button {{
  display: inline-block;
  border: 1px solid var(--accent);
  border-radius: 6px;
  background: var(--accent);
  color: white;
  padding: 10px 14px;
  text-decoration: none;
  cursor: pointer;
}}
.secondary {{ background: #21262d; border-color: var(--border); }}
.stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }}
.stat {{ border: 1px solid var(--border); border-radius: 6px; padding: 10px; background: #0f1620; }}
.stat b {{ display: block; font-size: 20px; }}
code {{ color: #a5d6ff; }}
ul {{ color: var(--muted); }}
.warning-list {{ display: grid; gap: 10px; }}
.warning-item {{
  border: 1px solid var(--border);
  border-radius: 6px;
  background: #0f1620;
  padding: 10px;
}}
.warning-tag {{
  display: inline-block;
  min-width: 108px;
  margin-right: 8px;
  border: 1px solid #d29922;
  border-radius: 999px;
  padding: 2px 8px;
  color: #f2cc60;
  font-size: 12px;
  text-align: center;
}}
.warning-message {{ color: var(--text); }}
.warning-help {{ color: var(--muted); font-size: 12px; margin-top: 6px; }}
</style>
</head>
<body><main>{body}</main></body>
</html>""".encode("utf-8")


def home_page() -> bytes:
    return page(
        APP_TITLE,
        """<h1>PHR Diff</h1>
<p>Select a baseline and current GCSS-Army Primary Hand Receipt PDF. Processing stays on this computer.</p>
<form class="panel" method="post" action="/run" enctype="multipart/form-data">
  <label for="old_pdf">Baseline PDF</label>
  <input id="old_pdf" name="old_pdf" type="file" accept="application/pdf,.pdf" required>
  <label for="new_pdf">Current PDF</label>
  <input id="new_pdf" name="new_pdf" type="file" accept="application/pdf,.pdf" required>
  <label for="folder_name">Report folder name</label>
  <input id="folder_name" name="folder_name" type="text" value="phr_report">
  <div class="checks">
    <label><input type="checkbox" name="include_metadata"> Include metadata-only changes</label>
    <label><input type="checkbox" name="full_pages"> Generate full-page view</label>
  </div>
  <button type="submit">Generate Report</button>
</form>
<div class="panel">
  <p>Reports are written under <code>Documents\\PHR Diff Reports</code>.</p>
  <p>After the report is generated, open <code>index.html</code> or use the report link shown here.</p>
</div>""",
    )


def sanitize_folder_name(value: str) -> str:
    cleaned = "".join(ch for ch in value.strip() if ch.isalnum() or ch in (" ", "_", "-")).strip()
    return cleaned or "phr_report"


class WebGuiHandler(BaseHTTPRequestHandler):
    server: "PHRDiffServer"

    def log_message(self, format: str, *args) -> None:
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send(home_page())
            return
        if parsed.path == "/shutdown":
            self._send(page(APP_TITLE, "<h1>PHR Diff has closed.</h1><p>You can close this browser tab.</p>"))
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        if parsed.path.startswith("/report/"):
            self._serve_report_file(parsed.path)
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/run":
            self.send_error(404)
            return
        try:
            result = self._run_upload()
            self._send(result)
        except Exception as exc:
            self._send(
                page(
                    APP_TITLE,
                    f"""<h1>Report generation failed</h1>
<div class="panel"><p>{html.escape(str(exc))}</p><p><a class="button secondary" href="/">Start over</a></p></div>""",
                ),
                status=500,
            )

    def _run_upload(self) -> bytes:
        form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={"REQUEST_METHOD": "POST"})
        old_field = form["old_pdf"]
        new_field = form["new_pdf"]
        folder_name = sanitize_folder_name(form.getfirst("folder_name", "phr_report"))
        run_id = f"{folder_name}_{uuid.uuid4().hex[:8]}"
        output_dir = reports_root() / run_id
        upload_dir = output_dir / "_uploads"
        upload_dir.mkdir(parents=True, exist_ok=True)

        old_pdf = upload_dir / (Path(old_field.filename or "baseline.pdf").name or "baseline.pdf")
        new_pdf = upload_dir / (Path(new_field.filename or "current.pdf").name or "current.pdf")
        with old_pdf.open("wb") as stream:
            shutil.copyfileobj(old_field.file, stream)
        with new_pdf.open("wb") as stream:
            shutil.copyfileobj(new_field.file, stream)

        old_receipt = parse_hand_receipt(old_pdf)
        new_receipt = parse_hand_receipt(new_pdf)
        reconciliation = compare_receipts(
            old_receipt,
            new_receipt,
            include_metadata_changes="include_metadata" in form,
        )
        attach_validation_warnings(reconciliation, old_receipt, new_receipt)
        index = generate_report(
            old_pdf,
            new_pdf,
            old_receipt,
            new_receipt,
            reconciliation,
            output_dir,
            full_pages="full_pages" in form,
        )
        stats = summary(reconciliation)
        report_url = f"/report/{run_id}/index.html"
        pdf_url = f"/report/{run_id}/phr-diff-report.pdf"
        stat_html = "".join(
            f"<div class='stat'><b>{value}</b><span>{html.escape(label.replace('_', ' ').title())}</span></div>"
            for label, value in stats.items()
        )
        warning_details = tagged_validation_warnings(reconciliation.warnings)
        warnings = "".join(
            "<div class='warning-item'>"
            f"<span class='warning-tag'>{html.escape(warning['tag'])}</span>"
            f"<span class='warning-message'>{html.escape(warning['message'])}</span>"
            f"<div class='warning-help'>{html.escape(warning['explanation'])}</div>"
            "</div>"
            for warning in warning_details[:20]
        )
        extra_count = max(0, len(warning_details) - 20)
        more = f"<p>{extra_count} more warnings are available in the visual report.</p>" if extra_count else ""
        warning_block = (
            f"<div class='panel'><h2>Validation Warnings</h2><div class='warning-list'>{warnings}</div>{more}</div>"
            if warnings
            else ""
        )
        return page(
            APP_TITLE,
            f"""<h1>Report Generated</h1>
<p>Saved to <code>{html.escape(str(index))}</code>.</p>
<p><a class="button" href="{report_url}" target="_blank">Open Visual Report</a>
<a class="button secondary" href="{pdf_url}" target="_blank">Open PDF Report</a>
<a class="button secondary" href="/">Run Another Compare</a>
<a class="button secondary" href="/shutdown">Close App</a></p>
<div class="panel stats">{stat_html}</div>
{warning_block}""",
        )

    def _serve_report_file(self, request_path: str) -> None:
        relative = unquote(request_path.removeprefix("/report/"))
        target = (reports_root() / relative).resolve()
        root = reports_root().resolve()
        if not str(target).startswith(str(root)) or not target.is_file():
            self.send_error(404)
            return
        content_type = "text/html"
        if target.suffix.lower() == ".json":
            content_type = "application/json"
        elif target.suffix.lower() == ".png":
            content_type = "image/png"
        elif target.suffix.lower() == ".pdf":
            content_type = "application/pdf"
        data = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _send(self, data: bytes, status: int = 200) -> None:
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class PHRDiffServer(ThreadingHTTPServer):
    pass


def main(argv: list[str] | None = None) -> None:
    argv = sys.argv[1:] if argv is None else argv
    if "--smoke-test" in argv:
        print("PHRDiff web GUI smoke test ok")
        return

    parser = ArgumentParser(description="Start the local PHR Diff browser GUI.")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-open", action="store_true")
    args = parser.parse_args(argv)

    server = PHRDiffServer(("127.0.0.1", args.port), WebGuiHandler)
    url = f"http://127.0.0.1:{server.server_port}/"
    if not args.no_open:
        webbrowser.open(url)
    print(url)
    server.serve_forever()


if __name__ == "__main__":
    main()
