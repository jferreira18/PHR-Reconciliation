from pathlib import Path

from phr_diff.models import BBox
from phr_diff.parser import Row, Word, parse_property_row, parse_serial_row


def word(text: str, x0: float, y0: float = 10, x1: float | None = None) -> Word:
    width = max(6, len(text) * 5)
    return Word(text, BBox(x0, y0, x1 if x1 is not None else x0 + width, y0 + 10))


def parse_row(words: list[Word]):
    item, warning = parse_property_row(Row(words), 1, "synthetic.pdf")
    assert warning is None
    assert item is not None
    return item


def test_parse_ordinary_stock_row_with_ea_ui():
    item = parse_row(
        [
            word("1095015333013", 20),
            word("HOLSTER,PISTOL", 105),
            word("EA", 497),
            word("U", 545),
            word("6154", 584),
            word("EA", 636),
            word("1", 702),
        ]
    )
    assert item.stock_number == "1095015333013"
    assert item.ui == "EA"
    assert item.qty == 1
    assert item.qty_bbox is not None


def test_parse_nonstandard_identifier_merged_with_description():
    item = parse_row(
        [
            word("7025GDOFU5:C_00PPDocking", 21, x1=135),
            word("Station", 137),
            word("EA", 497),
            word("U", 545),
            word("6151", 584),
            word("EA", 636),
            word("3", 702),
        ]
    )
    assert item.stock_number == "7025GDOFU5:C_00PP"
    assert item.description == "Docking Station"


def test_parse_kt_and_se_ui_values():
    kt = parse_row(
        [word("6545016899365", 20), word("MEDICAL", 105), word("KT", 497), word("(1)", 512), word("U", 545), word("6151", 584), word("EA", 636), word("4", 702)]
    )
    se = parse_row(
        [word("9999999999999", 20), word("SET", 105), word("SE", 497), word("(1)", 512), word("U", 545), word("6151", 584), word("EA", 636), word("2", 702)]
    )
    assert kt.ui == "KT (1)"
    assert se.ui == "SE (1)"


def test_parse_serial_values_with_slashes_and_lot_quantities():
    serials = parse_serial_row(
        Row(
            [
                word("ABC/123", 55),
                word("LC-07C381-826", 298),
                word("-", 365),
                word("20", 375),
                word("B", 545),
                word("-", 558),
                word("3", 568),
            ]
        ),
        2,
    )
    assert [(s.identifier, s.associated_qty) for s in serials] == [
        ("ABC/123", None),
        ("LC-07C381-826", 20),
        ("B", 3),
    ]
    assert all(s.bbox is not None for s in serials)

