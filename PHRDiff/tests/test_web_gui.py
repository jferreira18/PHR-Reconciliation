from io import BytesIO

from phr_diff.web_gui import parse_multipart_form


def test_parse_multipart_form_without_cgi():
    boundary = "----phr-boundary"
    body = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="folder_name"\r\n\r\n'
        "august-report\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="old_pdf"; filename="old.pdf"\r\n'
        "Content-Type: application/pdf\r\n\r\n"
        "%PDF-old\r\n"
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="full_pages"\r\n\r\n'
        "on\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")

    fields, files = parse_multipart_form(
        f"multipart/form-data; boundary={boundary}",
        len(body),
        BytesIO(body),
    )

    assert fields["folder_name"] == "august-report"
    assert "full_pages" in fields
    assert files["old_pdf"].filename == "old.pdf"
    assert files["old_pdf"].data == b"%PDF-old"
