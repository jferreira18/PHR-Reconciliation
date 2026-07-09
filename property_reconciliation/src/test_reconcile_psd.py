import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from reconcile_psd import append_psd_matches, load_psd_rows


class TestPSDReconciliation(unittest.TestCase):
    def test_serial_match_requires_identifier_alignment(self) -> None:
        phr_df = pd.DataFrame(
            [
                {
                    "nsn": "015223494",
                    "lin": "63026N",
                    "serial_number": "1183",
                    "nomenclature": "POWER SUPPLY",
                    "quantity": "1",
                }
            ]
        )
        psd_df = pd.DataFrame(
            [
                {
                    "PSD ID": "wrong-serial-collision",
                    "To PB LIN": "PM20BQ",
                    "Source NIIN": "016954549",
                    "Source LIN Name": "RADIO SET",
                    "Validated Quantity": "20",
                    "PSD Status": "Open",
                    "Condition/Maintenance": "As Is",
                    "Serial Numbers": "(20) 000564, 000719, 001183",
                    "Type": "Lateral Transfer",
                    "Vetting Level": "DIV",
                    "Vetting Status": "DST Approved",
                    "Status": "Open",
                    "ERDS Pass thru?": "False",
                    "From Code": "A",
                    "To Code": "B",
                    "From Name": "From",
                    "To Name": "To",
                }
            ]
        )
        psd_df = load_psd_rows_from_frame(psd_df)

        reconciled = append_psd_matches(phr_df, psd_df)

        self.assertEqual(reconciled.loc[0, "psd_match_status"], "missing_psd")

    def test_serial_and_identifier_match_appends_psd_id(self) -> None:
        phr_df = pd.DataFrame(
            [
                {
                    "nsn": "01W002043",
                    "lin": "70210N",
                    "serial_number": "2TK43204HG",
                    "nomenclature": "COMPUTER, LAPTOP",
                    "quantity": "1",
                }
            ]
        )
        psd_df = pd.DataFrame(
            [
                {
                    "PSD ID": "matching-psd",
                    "To PB LIN": "70210N",
                    "Source NIIN": "701001W002043",
                    "Source LIN Name": "COMPUTER, MICRO LAP-TOP",
                    "Validated Quantity": "2",
                    "PSD Status": "Open",
                    "Condition/Maintenance": "As Is",
                    "Serial Numbers": "(2) 2TK43204HG, 2TK43204M1",
                    "Type": "Lateral Transfer",
                    "Vetting Level": "DIV",
                    "Vetting Status": "DST Approved",
                    "Status": "Open",
                    "ERDS Pass thru?": "False",
                    "From Code": "A",
                    "To Code": "B",
                    "From Name": "From",
                    "To Name": "To",
                }
            ]
        )
        psd_df = load_psd_rows_from_frame(psd_df)

        reconciled = append_psd_matches(phr_df, psd_df)

        self.assertEqual(reconciled.loc[0, "psd_match_status"], "matched")
        self.assertEqual(reconciled.loc[0, "psd_match_method"], "serial_identifier_lin")
        self.assertEqual(reconciled.loc[0, "psd_psd_id"], "matching-psd")


def load_psd_rows_from_frame(df: pd.DataFrame) -> pd.DataFrame:
    with tempfile.TemporaryDirectory() as temp_dir:
        path = Path(temp_dir) / "_test_psd.xlsx"
        df.to_excel(path, sheet_name="POWER BI", index=False)
        return load_psd_rows(path)


if __name__ == "__main__":
    unittest.main()
