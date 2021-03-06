from __future__ import print_function
from __future__ import absolute_import

import os
import unittest

from dataprofiler.data_readers.data import Data
from dataprofiler.data_readers.avro_data import AVROData


test_root_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


class TestAVRODataClass(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.input_file_path = None
        cls.output_file_path = None
        cls.ss = None

        test_dir = os.path.join(test_root_path, 'data')
        cls.input_file_names = [
            os.path.join(test_dir, 'avro/users.avro'),
            os.path.join(test_dir, 'avro/userdata1.avro'),
            os.path.join(test_dir, 'avro/userdata1_intentionally_mislabled_file.parquet'),
            os.path.join(test_dir, 'avro/userdata1_intentionally_mislabled_file.csv'),
            os.path.join(test_dir, 'avro/userdata1_intentionally_mislabled_file.json'),
            os.path.join(test_dir, 'avro/userdata1_intentionally_mislabled_file.txt'),
            os.path.join(test_dir, 'avro/deflate_compressed_intentionally_mislabeled_file.csv'),
            os.path.join(test_dir, 'avro/snappy_compressed_intentionally_mislabeled_file.csv'),
        ]

    def test_avro_file_identification(self):
        """
        Determine if the avro file can be automatically identified
        """
        for input_file in self.input_file_names:
            input_data_obj = Data(input_file)
            self.assertEqual(input_data_obj.data_type, 'avro')

    def test_specifying_data_type(self):
        """
        Determine if the avro file can be loaded with manual data_type setting
        """
        for input_file in self.input_file_names:
            input_data_obj = Data(input_file, data_type='avro')
            self.assertEqual(input_data_obj.data_type, 'avro')

    def test_reload_data(self):
        """
        Determine if the avro file can be reloaded
        """
        for input_file in self.input_file_names:
            input_data_obj = Data(input_file)
            input_data_obj.reload(input_file)
            self.assertEqual(input_data_obj.data_type, 'avro')

    def test_data_formats(self):
        """
        Determine if the avro file data_formats can be used
        """
        for input_file in self.input_file_names:
            input_data_obj = Data(input_file)
            for data_format in list(input_data_obj._data_formats.keys()):
                input_data_obj.data_format = data_format
                self.assertEqual(input_data_obj.data_format, data_format)
                data = input_data_obj.data
                if data_format == "dataframe":
                    import pandas as pd
                    self.assertIsInstance(data, pd.DataFrame)
                elif data_format in ["records", "json"]:
                    self.assertIsInstance(data, list)
                    self.assertIsInstance(data[0], str)

    def test_nested_keys(self):
        """
        Determine if the avro file data_formats can be used
        """
        dict =[{'name': 1, 'favorite_number': 1}, {'favorite_color': 1, 'address': {'streetaddress': 1, 'city': 1}}]
        nested_keys = AVROData._get_nested_keys_from_dicts(dict)
        self.assertIsNotNone(nested_keys)
        schema_avro = {
              'namespace': 'avro_namespace',
              'name': 'avro_filename',
              'type': 'record',
              'fields': [
                {'name': 'name', 'type': ['string', 'null']},
                {'name': 'favorite_number', 'type': ['string', 'null']},
                {'name': 'favorite_color', 'type': ['string', 'null']},
                {
                  'name': 'address',
                  'type': [{
                      'namespace': 'avro_namespace',
                      'name': 'address',
                      'type': 'record',
                      'fields': [
                          {'name': 'streetaddress', 'type': ['string', 'null']},
                          {'name': 'city', 'type': ['string', 'null']}
                      ]
                    },
                    'null'
                  ]
                }
              ]
            }
        schema_avro = AVROData._get_schema_avro(nested_keys, schema_avro)
        self.assertIsNotNone(schema_avro)

if __name__ == '__main__':
    unittest.main()
