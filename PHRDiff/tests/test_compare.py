from phr_diff.compare import compare_receipts
from phr_diff.models import BBox, HandReceipt, InventoryItem, SerialEntry


def item(stock: str, qty: int, serials: list[str] | None = None) -> InventoryItem:
    box = BBox(0, 0, 100, 20)
    return InventoryItem(
        stock_number=stock,
        description=f"Item {stock}",
        ui="EA",
        ciic="U",
        dla="6151",
        buom="EA",
        qty=qty,
        page=1,
        raw_line=stock,
        row_bbox=box,
        stock_bbox=box,
        description_bbox=box,
        qty_bbox=box,
        serial_entries=[SerialEntry(identifier=s, page=1, bbox=box) for s in serials or []],
    )


def receipt(*items: InventoryItem) -> HandReceipt:
    return HandReceipt(source_file="test.pdf", items=list(items))


def test_item_added_removed_and_quantity_changed():
    result = compare_receipts(receipt(item("A", 1), item("B", 1)), receipt(item("A", 2), item("C", 1)))
    assert [c.stock_number for c in result.added_items] == ["C"]
    assert [c.stock_number for c in result.removed_items] == ["B"]
    assert [(c.stock_number, c.old_value, c.new_value) for c in result.modified_items] == [("A", "1", "2")]


def test_serial_added_removed_and_swap():
    result = compare_receipts(receipt(item("A", 2, ["S1", "S2"])), receipt(item("A", 2, ["S2", "S3"])))
    assert {c.change_type for c in result.serial_swaps} == {"serial_swap_removed", "serial_swap_added"}
    assert {c.old_value or c.new_value for c in result.serial_swaps} == {"S1", "S3"}


def test_serial_added_without_swap_when_quantity_changes():
    result = compare_receipts(receipt(item("A", 1, ["S1"])), receipt(item("A", 2, ["S1", "S2"])))
    changes = result.changes
    assert any(c.change_type == "quantity_changed" for c in changes)
    assert any(c.change_type == "serial_added" and c.new_value == "S2" for c in changes)

