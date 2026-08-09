from phr_diff.validation import classify_validation_warning


def test_validation_warning_tags_are_clear():
    serial_warning = "WACEHD.pdf: 5820014635543: parsed 10 unique serials but OH Qty is 11."
    duplicate_warning = "WACEHD.pdf: duplicate stock-number record ABC appears 2 times."
    coordinate_warning = "WACEHD.pdf: ABC: coordinate lookup failure for property row or quantity."

    assert classify_validation_warning(serial_warning)["tag"] == "SERIAL COUNT"
    assert classify_validation_warning(duplicate_warning)["tag"] == "DUPLICATE STOCK"
    assert classify_validation_warning(coordinate_warning)["tag"] == "COORDINATE"

