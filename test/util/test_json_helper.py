from os.path import dirname, join
import unittest
import json
from mycroft.util.json_helper import load_commented_json, uncomment_json


class TestFileLoad(unittest.TestCase):

    def test_load(self):
        root_dir = dirname(__file__)
        # Load normal JSON file
        plainfile = join(root_dir, 'plain.json')
        with open(plainfile, 'rw') as f:
            data_from_plain = json.load(f)

        # Load commented JSON file
        commentedfile = join(root_dir, 'commented.json')
        data_from_commented = load_commented_json(commentedfile)

        # Should be the same...
        self.assertEqual(data_from_commented, data_from_plain)


if __name__ == "__main__":
    unittest.main()
