from __future__ import print_function

from data_profiler.profilers.column_profile_compilers import \
    ColumnPrimitiveTypeProfileCompiler

from .test_base_column_profilers import AbstractTestColumnProfiler

import os
import unittest


test_root_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


class TestColumnDataTypeProfiler(AbstractTestColumnProfiler, unittest.TestCase):

    column_profiler = ColumnPrimitiveTypeProfileCompiler
    profile_keys = ['data_type', 'statistics', 'data_type_representation']

    def setUp(self):
        AbstractTestColumnProfiler.setUp(self)

    @classmethod
    def setUpClass(cls):
        super(TestColumnDataTypeProfiler, cls).setUpClass()


if __name__ == '__main__':
    unittest.main()
