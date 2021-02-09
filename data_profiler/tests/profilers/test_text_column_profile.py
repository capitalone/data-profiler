import unittest
import os
import pandas as pd
import numpy as np
import six

from data_profiler.tests.profilers import utils as test_utils
from data_profiler.profilers import TextColumn
from data_profiler.profilers.profiler_options import TextOptions
from unittest.mock import patch, MagicMock
from collections import defaultdict


test_root_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


class TestTextColumnProfiler(unittest.TestCase):

    def setUp(self):
        test_utils.set_seed(seed=0)

    def test_profiled_vocab(self):
        """
        Checks whether the vocab list for the profiler is correct.
        :return:
        """
        df1 = pd.Series([
            "abcd", "aa", "abcd", "aa", "b", "4", "3", "2", "dfd", "2",
        ]).apply(str)
        df2 = pd.Series(["1", "1", "ee", "ff", "ff", "gg",
                         "gg", "abcd", "aa", "b", "ee", "b"]).apply(str)
        df3 = pd.Series([
            "NaN", "b", "nan", "c",
        ]).apply(str)

        text_profiler = TextColumn(df1.name)
        text_profiler.update(df1)

        unique_vocab = dict.fromkeys(''.join(df1.tolist())).keys()
        six.assertCountEqual(self, unique_vocab, text_profiler.vocab)
        six.assertCountEqual(
            self, set(text_profiler.vocab), text_profiler.vocab)

        text_profiler.update(df2)
        df = pd.concat([df1, df2])
        unique_vocab = dict.fromkeys(''.join(df.tolist())).keys()
        six.assertCountEqual(self, unique_vocab, text_profiler.vocab)
        six.assertCountEqual(
            self, set(text_profiler.vocab), text_profiler.vocab)

        text_profiler.update(df3)
        df = pd.concat([df1, df2, df3])
        unique_vocab = dict.fromkeys(''.join(df.tolist())).keys()
        six.assertCountEqual(self, unique_vocab, text_profiler.vocab)

    def test_profiled_str_numerics(self):
        """
        Checks whether the vocab list for the profiler is correct.
        :return:
        """

        def mean(df):
            total = 0
            for item in df:
                total += item
            return total / len(df)

        def var(df):
            var = 0
            mean_df = mean(df)
            for item in df:
                var += (item - mean_df) ** 2
            return var / (len(df) - 1)

        def batch_variance(mean_a, var_a, count_a, mean_b, var_b, count_b):
            delta = mean_b - mean_a
            m_a = var_a * (count_a - 1)
            m_b = var_b * (count_b - 1)
            M2 = m_a + m_b + delta ** 2 * count_a * count_b / (
                count_a + count_b)
            return M2 / (count_a + count_b - 1)

        df1 = pd.Series([
            "abcd", "aa", "abcd", "aa", "b", "4", "3", "2", "dfd", "2", np.nan,
        ]).apply(str)
        df2 = pd.Series(["1", "1", "ee", "ff", "ff", "gg",
                         "gg", "abcd", "aa", "b", "ee", "b"]).apply(str)
        df3 = pd.Series([
            "NaN", "b", "nan", "c", None,
        ]).apply(str)

        text_profiler = TextColumn(df1.name)
        text_profiler.update(df1)

        self.assertEqual(mean(df1.str.len()), text_profiler.mean)
        self.assertAlmostEqual(var(df1.str.len()), text_profiler.variance)
        self.assertAlmostEqual(
            np.sqrt(var(df1.str.len())), text_profiler.stddev)

        variance = batch_variance(
            mean_a=text_profiler.mean,
            var_a=text_profiler.variance,
            count_a=text_profiler.sample_size,
            mean_b=mean(df2.str.len()),
            var_b=var(df2.str.len()),
            count_b=df2.count()
        )
        text_profiler.update(df2)
        df = pd.concat([df1, df2])
        self.assertEqual(df.str.len().mean(), text_profiler.mean)
        self.assertAlmostEqual(variance, text_profiler.variance)
        self.assertAlmostEqual(np.sqrt(variance), text_profiler.stddev)

        variance = batch_variance(
            mean_a=text_profiler.mean,
            var_a=text_profiler.variance,
            count_a=text_profiler.match_count,
            mean_b=mean(df3.str.len()),
            var_b=var(df3.str.len()),
            count_b=df3.count()
        )
        text_profiler.update(df3)

        df = pd.concat([df1, df2, df3])
        self.assertEqual(df.str.len().mean(), text_profiler.mean)
        self.assertAlmostEqual(variance, text_profiler.variance)
        self.assertAlmostEqual(np.sqrt(variance), text_profiler.stddev)

    def test_base_case(self):
        data = pd.Series([], dtype=object)
        profiler = TextColumn(data.name)
        profiler.update(data)
        profiler.update(data)  # intentional to validate no changes if empty

        self.assertEqual(profiler.match_count, 0)
        self.assertEqual(profiler.min, None)
        self.assertEqual(profiler.max, None)
        self.assertIsNone(profiler.data_type_ratio)

    def test_data_ratio(self):
        # should always be 1.0 unless empty
        df1 = pd.Series([
            "abcd", "aa", "abcd", "aa", "b", "4", "3", "2", "dfd", "2",
        ]).apply(str)

        profiler = TextColumn(df1.name)
        profiler.update(df1)
        self.assertEqual(profiler.data_type_ratio, 1.0)

        # ensure batch update doesn't alter values
        profiler.update(df1)
        self.assertEqual(profiler.data_type_ratio, 1.0)

    def test_profiled_min(self):
        df = pd.Series(["aaa", "aa", "aaaa", "aaa"]).apply(str)

        profiler = TextColumn(df.name)
        profiler.update(df)
        self.assertEqual(profiler.min, 2)

        df = pd.Series(["aa", "a"]).apply(str)
        profiler.update(df)
        self.assertEqual(profiler.min, 1)

    def test_profiled_max(self):
        df = pd.Series(["a", "aa", "a", "a"]).apply(str)

        profiler = TextColumn(df.name)
        profiler.update(df)
        self.assertEqual(profiler.max, 2)

        df = pd.Series(["aa", "aaa", "a"]).apply(str)
        profiler.update(df)
        self.assertEqual(profiler.max, 3)

    def test_profile(self):
        df = pd.Series(
            ["abcd", "aa", "abcd", "aa", "b", "4", "3", "2", "dfd", "2"]
        ).apply(str)
        profiler = TextColumn(df.name)
        expected_profile = dict(
            min=1.0,
            max=4.0,
            mean=20.0 / 10.0,
            median=None,
            variance=14.0 / 9.0,
            stddev=np.sqrt(14.0 / 9.0),
            histogram={
                'bin_counts': np.array([5, 0, 2, 0, 1, 2]),
                'bin_edges': np.array([1., 1.5, 2., 2.5, 3., 3.5, 4.])
            },
            quantiles={0: 1.25, 1: 1.5, 2: 3.0},
            vocab=['a', 'b', 'c', 'd', '4', '3', '2', 'f'],
            times=defaultdict(float, {'vocab': 1.0,
                                      'max': 1.0,
                                      'min': 1.0,
                                      'histogram_and_quantiles': 15.0,
                                      'sum': 1.0,
                                      'variance': 1.0})
        )
        time_array = [float(x) for x in range(30, 0, -1)]
        with patch('time.time', side_effect=lambda: time_array.pop()):
            profiler.update(df)
            profile = profiler.profile
            expected_histogram = expected_profile.pop('histogram')
            expected_quantiles = expected_profile.pop('quantiles')
            quantiles = profile.pop('quantiles')
            histogram = profile.pop('histogram')
            # key and value populated correctly
            self.assertDictEqual(expected_profile, profile)
            self.assertTrue(np.all(
                expected_histogram['bin_counts'] == histogram['bin_counts']
            ))
            self.assertTrue(np.all(
                expected_histogram['bin_edges'] == histogram['bin_edges']
            ))
            self.assertDictEqual(
                expected_quantiles, {
                    0: quantiles[249], 1: quantiles[499], 2: quantiles[749]})

    def test_option_timing(self):
        data = [2.0, 12.5, 'not a float', 6.0, 'not a float']
        df = pd.Series(data).apply(str)

        options = TextOptions()
        options.set({"min.is_enabled": False})

        profiler = TextColumn(df.name, options=options)

        time_array = [float(i) for i in range(100, 0, -1)]
        with patch('time.time', side_effect=lambda: time_array.pop()):
            # Validate that the times dictionary is empty
            self.assertEqual(defaultdict(float), profiler.profile['times'])
            profiler.update(df)

            # Validate the time in the datetime class has the expected time.
            profile = profiler.profile

            expected = defaultdict(float,
                                   {'max': 1.0,
                                    'sum': 1.0,
                                    'variance': 1.0,
                                    'histogram_and_quantiles': 15.0,
                                    'vocab': 1.0})
            self.assertEqual(expected, profile['times'])

            # Validate time in datetime class has expected time after second
            # update
            profiler.update(df)
            expected = defaultdict(float,
                                   {'max': 2.0,
                                    'sum': 2.0,
                                    'variance': 2.0,
                                    'histogram_and_quantiles': 30.0,
                                    'vocab': 2.0})
            self.assertEqual(expected, profiler.profile['times'])

    def test_merge_profile(self):
        df = pd.Series(
            ["abcd", "aa", "abcd", "aa", "b", "4", "3", "2", "dfd", "2"]
        ).apply(str)

        df2 = pd.Series(
            ["hello", "my", "name", "is", "Grant", "I", "have", "67", "dogs"]
        ).apply(str)

        expected_vocab = [
            'a', 'b', 'c', 'd', '4', '3', '2', 'f', 'h', 'e', 'l', 'o', 'm',
            'y', 'n', 'i', 's', 'G', 'r', 't', 'I', 'v', '6', '7', 'g'
        ]

        profiler = TextColumn("placeholder_name")
        profiler.update(df)

        profiler2 = TextColumn("placeholder_name")
        profiler2.update(df2)

        profiler3 = profiler + profiler2

        self.assertAlmostEqual(profiler3.mean, 2.578947, 3)
        self.assertEqual(profiler3.sample_size,
                         profiler.sample_size + profiler2.sample_size)
        self.assertEqual(profiler3.max, profiler2.max)
        self.assertEqual(expected_vocab, profiler3.vocab)

    def test_merge_timing(self):
        profiler1 = TextColumn("placeholder_name")
        profiler2 = TextColumn("placeholder_name")
            
        profiler1.times = dict(vocab=2.0)
        profiler2.times = dict(vocab=3.0)

        time_array = [float(i) for i in range(2, 0, -1)]
        with patch('time.time', side_effect=lambda: time_array.pop()):
            profiler3 = profiler1 + profiler2

            # __add__() call adds 1 so expected is 6
            expected_times = defaultdict(float, {'vocab': 6.0})
            self.assertDictEqual(expected_times, profiler3.profile['times'])

