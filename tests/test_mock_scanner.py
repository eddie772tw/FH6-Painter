import unittest
from unittest.mock import MagicMock, patch, ANY
import ctypes
import struct
import os
import sys

# Add the project root to sys.path to allow importing from tools
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import tools.fh6_import_layer_table as importer

class TestMockScanner(unittest.TestCase):
    @patch("tools.fh6_import_layer_table.kernel32")
    def test_enumerate_regions_broad(self, mock_kernel32):
        # We need a way to fill the MBI structure.
        self.assertEqual(importer.MEM_MAPPED, 0x40000)
        self.assertEqual(importer.MEM_IMAGE, 0x1000000)

        mbi_data = []
        # 1. Private
        m1 = importer.MEMORY_BASIC_INFORMATION64()
        m1.BaseAddress = 0x0
        m1.RegionSize = 0x1000
        m1.State = importer.MEM_COMMIT
        m1.Type = importer.MEM_PRIVATE
        m1.Protect = importer.PAGE_READWRITE
        mbi_data.append(m1)

        # 2. Mapped
        m2 = importer.MEMORY_BASIC_INFORMATION64()
        m2.BaseAddress = 0x1000
        m2.RegionSize = 0x1000
        m2.State = importer.MEM_COMMIT
        m2.Type = importer.MEM_MAPPED
        m2.Protect = importer.PAGE_READWRITE
        mbi_data.append(m2)

        # 3. Image
        m3 = importer.MEMORY_BASIC_INFORMATION64()
        m3.BaseAddress = 0x2000
        m3.RegionSize = 0x1000
        m3.State = importer.MEM_COMMIT
        m3.Type = importer.MEM_IMAGE
        m3.Protect = importer.PAGE_READWRITE
        mbi_data.append(m3)

        idx = 0
        def mock_vq(handle, address, mbi_ptr, size):
            nonlocal idx
            if idx >= len(mbi_data):
                return 0
            ctypes.memmove(mbi_ptr, ctypes.addressof(mbi_data[idx]), size)
            idx += 1
            return size

        mock_kernel32.VirtualQueryEx.side_effect = mock_vq

        regions = importer.enumerate_regions(None)
        self.assertEqual(len(regions), 3)
        self.assertEqual(regions[0]["Type"], importer.MEM_PRIVATE)
        self.assertEqual(regions[1]["Type"], importer.MEM_MAPPED)
        self.assertEqual(regions[2]["Type"], importer.MEM_IMAGE)

    @patch("tools.fh6_import_layer_table.try_read")
    @patch("tools.fh6_import_layer_table.is_user_ptr")
    @patch("tools.fh6_import_layer_table.read_2_floats")
    def test_score_layer_adaptive_details(self, mock_read_2_floats, mock_is_user_ptr, mock_try_read):
        mock_is_user_ptr.return_value = True

        # Scenario: Position is out of range
        mock_read_2_floats.side_effect = [
            (99999.0, 0.0), # pos: Fail
            (1.0, 1.0)      # scale: Pass
        ]
        mock_try_read.side_effect = [
            bytes([255, 255, 255, 255]), # color: Pass
            bytes([importer.SHAPE_ID_ELLIPSE]), # shape: Pass
            bytes([0]) # mask: Pass
        ]

        score, detail = importer.score_layer_adaptive(None, 0x1234, importer.StrictnessLevel.PERFECT, return_detail=True)
        self.assertEqual(score, 4)
        self.assertIn("Pos invalid", detail)

    @patch("tools.fh6_import_layer_table.enumerate_regions")
    @patch("tools.fh6_import_layer_table.try_read")
    @patch("tools.fh6_import_layer_table.read_u64")
    @patch("tools.fh6_import_layer_table.is_user_ptr")
    @patch("tools.fh6_import_layer_table.score_layer_adaptive")
    @patch("tools.fh6_import_layer_table.count_valid_layers_adaptive")
    def test_locate_layer_pointers_with_mapped_region(self, mock_count_valid, mock_score_adaptive, mock_is_user_ptr, mock_read_u64, mock_try_read, mock_enumerate):
        # Setup regions: one mapped region containing the pattern
        mock_enumerate.return_value = [
            {"Base": 0x10000, "Size": 0x1000, "Protect": importer.PAGE_READWRITE, "Type": importer.MEM_MAPPED}
        ]

        layer_count = 100
        pattern = struct.pack("<I", layer_count)

        chunk = bytearray(importer.CHUNK_SIZE)
        offset = 100
        chunk[offset:offset+4] = pattern

        mock_try_read.side_effect = [
            chunk, # scan_region_task
            struct.pack("<Q", 0x3000), # read_u64(table_addr) inside the loop
            # table_data for final pointers read
            struct.pack("<100Q", *[0x4000+i for i in range(100)])
        ]

        mock_read_u64.return_value = 0x20000
        mock_is_user_ptr.return_value = True

        def score_side_effect(handle, ptr, level, return_detail=False):
            if return_detail:
                return (5, "")
            return 5
        mock_score_adaptive.side_effect = score_side_effect

        mock_count_valid.return_value = 100

        with patch("tools.fh6_import_layer_table.HeuristicsManager") as mock_hm:
            mock_hm_inst = mock_hm.return_value
            mock_hm_inst.data = {"successful_regions": []}

            pointers, group, table = importer.locate_layer_pointers(None, layer_count, 1000)

            self.assertEqual(table, 0x20000)
            self.assertEqual(len(pointers), 100)

if __name__ == "__main__":
    unittest.main()
