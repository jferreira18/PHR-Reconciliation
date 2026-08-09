from pathlib import Path

from phr_diff.compare import compare_receipts
from phr_diff.parser import parse_hand_receipt
from phr_diff.report import generate_report
from phr_diff.validation import attach_validation_warnings


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"


def test_real_fixture_parse_counts_and_nonstandard_identifier():
    july = parse_hand_receipt(FIXTURES / "WACEHD_PHR_JULY.pdf")
    august = parse_hand_receipt(FIXTURES / "WACEHD PHR AUG.pdf")
    assert len(july.items) == 150
    assert len(august.items) == 164
    item = next(item for item in july.items if item.stock_number == "7025GDOFU5:C_00PP")
    assert item.description == "Docking Station"
    assert [(s.identifier, s.associated_qty) for s in item.serial_entries] == [("B", 3)]


def test_real_fixture_comparison_and_crop_generation(tmp_path):
    old_pdf = FIXTURES / "WACEHD_PHR_JULY.pdf"
    new_pdf = FIXTURES / "WACEHD PHR AUG.pdf"
    july = parse_hand_receipt(old_pdf)
    august = parse_hand_receipt(new_pdf)
    reconciliation = compare_receipts(july, august)
    attach_validation_warnings(reconciliation, july, august)
    assert reconciliation.added_items
    assert any(change.change_type == "quantity_changed" for change in reconciliation.modified_items)
    assert any(change.change_type.startswith("serial_") for change in reconciliation.changes)
    index = generate_report(old_pdf, new_pdf, july, august, reconciliation, tmp_path)
    assert index.exists()
    assert (tmp_path / "reconciliation.json").exists()
    assert any((tmp_path / "assets" / "crops").glob("*.png"))

