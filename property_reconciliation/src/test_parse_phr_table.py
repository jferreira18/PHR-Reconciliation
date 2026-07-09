import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from parse_phr_table import PHRTableParser


class TestPHRTableParser(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = PHRTableParser("dummy.pdf")

    def test_extract_lin_from_description_line(self) -> None:
        self.assertEqual(
            self.parser._extract_lin("000000573 A23828 AIR CONDITIONER: FL/WALL A/C AC 115V 1PH"),
            "A23828",
        )

    def test_is_mpo_line_requires_alpha_lin_token(self) -> None:
        self.assertTrue(
            self.parser._is_mpo_line("000000573 A23828 AIR CONDITIONER: FL/WALL A/C AC 115V 1PH")
        )
        self.assertFalse(self.parser._is_mpo_line("114064 130952 205888"))
        self.assertFalse(self.parser._is_mpo_line("1410681 K2133754 K2134652"))

    def test_extract_serial_candidates_allows_numeric_serials(self) -> None:
        self.assertEqual(self.parser._extract_serial_candidates("941247"), ["941247"])

    def test_extract_serial_candidates_ignores_mpo_numbers(self) -> None:
        self.assertEqual(
            self.parser._extract_serial_candidates("000000573 A23828 AIR CONDITIONER: FL/WALL A/C AC 115V 1PH"),
            [],
        )

    def test_extract_serial_candidates_keeps_long_alpha_numeric_serials(self) -> None:
        self.assertEqual(
            self.parser._extract_serial_candidates("GZ00090 MT121138434"),
            ["GZ00090", "MT121138434"],
        )

    def test_extract_serial_candidates_ignores_short_unit_like_tokens(self) -> None:
        self.assertEqual(self.parser._extract_serial_candidates("115V 1PH"), [])

    def test_extract_serial_candidates_can_keep_lin_shaped_serials_in_serial_blocks(self) -> None:
        self.assertEqual(
            self.parser._extract_serial_candidates("T41402", allow_lin_like=True),
            ["T41402"],
        )

    def test_extract_serial_candidates_can_keep_three_digit_serials_in_serial_blocks(self) -> None:
        self.assertEqual(
            self.parser._extract_serial_candidates("142 149", allow_short_numeric=True),
            ["142", "149"],
        )

    def test_extract_serial_candidates_can_keep_short_alpha_numeric_serials_in_serial_blocks(self) -> None:
        self.assertEqual(
            self.parser._extract_serial_candidates("G98", allow_short_numeric=True),
            ["G98"],
        )

    def test_extract_serial_candidates_preserves_slash_serials(self) -> None:
        self.assertEqual(
            self.parser._extract_serial_candidates(
                "10TGJAM15BS129021/NP2H6B",
                allow_lin_like=True,
                allow_short_numeric=True,
            ),
            ["10TGJAM15BS129021/NP2H6B"],
        )

    def test_extract_serial_candidates_preserves_comma_serials(self) -> None:
        self.assertEqual(
            self.parser._extract_serial_candidates(
                "SC42-44398,B7",
                allow_lin_like=True,
                allow_short_numeric=True,
            ),
            ["SC42-44398,B7"],
        )

    def test_match_item_line_accepts_alphanumeric_material_ids(self) -> None:
        parsed = self.parser._match_item_line(
            "01C083596 NAVIGATION SYSTEM, ROUTE PLANNER MOBILE: EA 7 D EA 13"
        )

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["nsn"], "01C083596")
        self.assertEqual(parsed["quantity"], "13")

    def test_match_item_line_preserves_local_material_ids(self) -> None:
        parsed = self.parser._match_item_line(
            "GDOFU5:C_00PP6 Docking Station EA U D EA 3"
        )

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["nsn"], "GDOFU5:C_00PP6")
        self.assertEqual(parsed["quantity"], "3")

    def test_match_item_line_strips_fsc_prefix_from_alphanumeric_material_ids(self) -> None:
        parsed = self.parser._match_item_line(
            "660501C083596 NAVIGATION SYSTEM, ROUTE PLANNER MOBILE: EA U 6166 EA 13"
        )

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["nsn"], "01C083596")
        self.assertEqual(parsed["quantity"], "13")

    def test_match_item_line_handles_attached_local_id_description(self) -> None:
        parsed = self.parser._match_item_line(
            "7025GDOFU5:C_00PPDocking Station EA U 6151 EA 3"
        )

        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["nsn"], "GDOFU5:C_00PP")
        self.assertEqual(parsed["nomenclature"], "Docking Station")
        self.assertEqual(parsed["quantity"], "3")


if __name__ == "__main__":
    unittest.main()
