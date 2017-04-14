import unittest
import json
from mycroft.util.json_helper import load_commented_json, uncomment_json


class TestFileLoad(unittest.TestCase):

    def test_load(self):
        # Load normal JSON file
        with open('plain.json', 'rw') as f:
            data_from_plain = json.load(f)

        # Load commented JSON file
        data_from_commented = load_commented_json('commented.json')

        # Should be the same...
        self.assertEqual(data_from_commented, data_from_plain)


if __name__ == "__main__":
    unittest.main()
