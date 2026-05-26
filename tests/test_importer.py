import sys
import unittest
from unittest.mock import patch, MagicMock
import json
import os

import tools.fh6_import_layer_table as fh6_importer

class TestImporter(unittest.TestCase):
    def test_clamp_byte(self):
        self.assertEqual(fh6_importer.clamp_byte(-10), 0)
        self.assertEqual(fh6_importer.clamp_byte(255), 255)
        self.assertEqual(fh6_importer.clamp_byte(300), 255)
        self.assertEqual(fh6_importer.clamp_byte(128.5), 128)

    def test_pack_color(self):
        shape = {"color": [10, 20, 30]}
        packed = fh6_importer.pack_color(shape)
        self.assertEqual(packed, bytes([10, 20, 30, 255]))

        shape_incomplete = {"color": [10]}
        packed_incomplete = fh6_importer.pack_color(shape_incomplete)
        self.assertEqual(packed_incomplete, bytes([10, 255, 255, 255]))

    def test_is_header_shape(self):
        valid_header = {
            "type": 1,
            "data": [0.00001, -0.00001, 100, 100],
            "color": [255, 255, 255, 0]
        }
        self.assertTrue(fh6_importer.is_header_shape(valid_header))

        invalid_type = valid_header.copy()
        invalid_type["type"] = 2
        self.assertFalse(fh6_importer.is_header_shape(invalid_type))

    def test_is_user_ptr(self):
        self.assertTrue(fh6_importer.is_user_ptr(0x10000000000))
        self.assertFalse(fh6_importer.is_user_ptr(0))

    def test_is_finite_in_range(self):
        self.assertTrue(fh6_importer.is_finite_in_range(50, 0, 100))
        self.assertFalse(fh6_importer.is_finite_in_range(-10, 0, 100))
        self.assertFalse(fh6_importer.is_finite_in_range(float('inf'), 0, 100))

    def test_find_canvas(self):
        shapes_with_header = [
            {"type": 1, "data": [0.0, 0.0, 800, 600], "color": [255, 255, 255, 0]},
            {"type": 2, "data": [10, 20, 30, 40], "color": [0, 0, 0, 255]}
        ]
        self.assertEqual(fh6_importer.find_canvas(shapes_with_header), (800, 600))

        shapes_no_header = [
            {"type": 2, "data": [10, 20, 500, 500], "color": [0, 0, 0, 255]}
        ]
        self.assertEqual(fh6_importer.find_canvas(shapes_no_header), (500, 500))

    def test_build_import_shape_list(self):
        shapes = [
            {"type": 1, "data": [0.0, 0.0, 800, 600], "color": [255, 255, 255, 0]},
            {"type": 2, "data": [10, 20, 30, 40], "color": [0, 0, 0, 255]},
            {"type": 2, "data": [1, 2], "color": [0, 0, 0, 255]} # Invalid data length
        ]

        filtered_no_header = fh6_importer.build_import_shape_list(shapes, include_header=False)
        self.assertEqual(len(filtered_no_header), 1)
        self.assertEqual(filtered_no_header[0]["data"], [10, 20, 30, 40])

        filtered_with_header = fh6_importer.build_import_shape_list(shapes, include_header=True)
        self.assertEqual(len(filtered_with_header), 2)
        self.assertEqual(filtered_with_header[0]["data"], [0.0, 0.0, 800, 600])

    @patch('tools.fh6_import_layer_table.kernel32')
    def test_find_forza_process(self, mock_kernel32):
        if not sys.platform == "win32":
            return

    def test_is_readable(self):
        self.assertFalse(fh6_importer.is_readable(fh6_importer.PAGE_NOACCESS))
        self.assertFalse(fh6_importer.is_readable(fh6_importer.PAGE_GUARD))
        self.assertTrue(fh6_importer.is_readable(fh6_importer.PAGE_READONLY))
        self.assertTrue(fh6_importer.is_readable(fh6_importer.PAGE_READWRITE))

    def test_is_writable(self):
        self.assertFalse(fh6_importer.is_writable(fh6_importer.PAGE_NOACCESS))
        self.assertFalse(fh6_importer.is_writable(fh6_importer.PAGE_READONLY))
        self.assertTrue(fh6_importer.is_writable(fh6_importer.PAGE_READWRITE))
        self.assertTrue(fh6_importer.is_writable(fh6_importer.PAGE_EXECUTE_READWRITE))

    def tearDown(self):
        for file in ['test_heuristics.json', 'test_shapes.json']:
            if os.path.exists(file):
                os.remove(file)

    def test_heuristics_manager(self):
        manager = fh6_importer.HeuristicsManager('test_heuristics.json')
        self.assertEqual(manager.data, {"successful_regions": [], "last_success_addr": None})

        region = {"Size": 1000, "Protect": 0x04, "Base": 0x1000}
        manager.record_success(0x2000, region)
        self.assertEqual(manager.data["last_success_addr"], 0x2000)
        self.assertEqual(manager.data["successful_regions"][0]["size"], 1000)


    def test_load_shapes(self):
        test_json = {
            "shapes": [
                {"type": 1, "data": [0, 0, 100, 100], "color": [255, 255, 255, 0]},
                {"type": 2, "data": [10, 20], "color": [10, 20, 30, 255]}
            ]
        }
        with open('test_shapes.json', 'w') as f:
            json.dump(test_json, f)

        shapes = fh6_importer.load_shapes('test_shapes.json')
        self.assertEqual(len(shapes), 2)
        self.assertEqual(shapes[0]["type"], 1)
        self.assertEqual(shapes[0]["data"], [0.0, 0.0, 100.0, 100.0])
        self.assertEqual(shapes[1]["type"], 2)


if __name__ == '__main__':
    unittest.main()
