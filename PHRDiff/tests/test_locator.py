from pathlib import Path

from phr_diff.locator import item_context_bbox
from phr_diff.parser import parse_hand_receipt


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_row_quantity_and_serial_coordinates_from_real_pdf():
    receipt = parse_hand_receipt(FIXTURES / "WACEHD_PHR_JULY.pdf")
    item = next(item for item in receipt.items if item.stock_number == "7025GDOFU5:C_00PP")
    assert item.row_bbox is not None
    assert item.qty_bbox is not None
    assert item.serial_entries[0].bbox is not None
    context = item_context_bbox(item)
    assert context is not None
    assert context.height > item.row_bbox.height

