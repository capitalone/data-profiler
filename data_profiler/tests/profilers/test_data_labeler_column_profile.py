from __future__ import print_function

from data_profiler.profilers.data_labeler_column_profile import DataLabelerColumn

import unittest
from unittest import mock
import pandas as pd
import numpy as np
import six

from unittest.mock import patch, MagicMock
from collections import defaultdict


@mock.patch('data_profiler.profilers.data_labeler_column_profile.DataLabeler')
class TestDataLabelerColumnProfiler(unittest.TestCase):

    @staticmethod
    def _setup_data_labeler_mock(mock_instance):
        mock_DataLabeler = mock_instance.return_value
        mock_DataLabeler.label_mapping = {"a": 0, "b": 1}
        mock_DataLabeler.reverse_label_mapping = {0: "a", 1: "b"}
        mock_DataLabeler.model.num_labels = 2

        def mock_predict(data, *args, **kwargs):
            len_data = len(data)
            output = [[1, 0], [0, 1]] * (len_data // 2)
            if len_data % 2:
                output += [[1, 0]]
            conf = np.array(output)
            pred = np.argmax(conf, axis=1)
            return {'pred': pred, 'conf': conf}
        mock_DataLabeler.predict.side_effect = mock_predict

    def test_base_case(self, mock_instance):
        self._setup_data_labeler_mock(mock_instance)

        data = pd.Series([], dtype=object)
        profiler = DataLabelerColumn(data.name)

        time_array = [float(i) for i in range(4, 0, -1)]
        with patch('time.time', side_effect=lambda: time_array.pop()):
            profiler.update(data)

            self.assertEqual(0, profiler.sample_size)
            self.assertEqual(["a", "b"], profiler._possible_data_labels)
            self.assertEqual(None, profiler.data_label)
            self.assertEqual(None, profiler.avg_predictions)
            six.assertCountEqual(
                self,
                ["avg_predictions", "data_label_representation", "times"],
                list(profiler.profile.keys())
            )
            self.assertEqual({
                    "avg_predictions": None,
                    "data_label_representation": None,
                    "times": defaultdict()
                },
                profiler.profile, )

    def test_update(self, mock_instance):
        self._setup_data_labeler_mock(mock_instance)

        data = pd.Series(['1', '2', '3'])
        profiler = DataLabelerColumn(data.name)
        profiler.update(data)

        self.assertEqual(3, profiler.sample_size)
        self.assertEqual(["a", "b"], profiler._possible_data_labels)
        self.assertEqual("a", profiler.data_label)
        self.assertDictEqual(dict(a=2/3, b=1/3), profiler.avg_predictions)
        self.assertDictEqual(dict(a=2, b=1), profiler.rank_distribution)
        self.assertDictEqual(dict(a=2/3, b=1/3), profiler.label_representation)

    def test_data_label_low_accuracy(self, mock_instance):
        self._setup_data_labeler_mock(mock_instance)

        def mock_low_predict(data, *args, **kwargs):
            return {'pred': np.array([[0, 0]]), 'conf': np.array([[0.2, 0.2]])}
        mock_instance.return_value.predict.side_effect = mock_low_predict

        data = pd.Series(['1'])
        profiler = DataLabelerColumn(data.name)
        profiler.update(data)
        self.assertEqual("could not determine", profiler.data_label)

    def test_multi_labels(self, mock_instance):
        mock_DataLabeler = mock_instance.return_value
        mock_DataLabeler.label_mapping = {"a": 0, "b": 1, "c": 2, "d": 3}
        mock_DataLabeler.reverse_label_mapping = \
            {0: "a", 1: "b", 2: "c", 3: "d"}
        mock_DataLabeler.model.num_labels = 4

        def mock_low_predict(data, *args, **kwargs):
            return {'pred': None, 'conf': np.array([
                [1, 0, 0, 0],  # 4 repeated
                [1, 0, 0, 0],
                [1, 0, 0, 0],
                [1, 0, 0, 0],
                [0, 1, 0, 0],  # 2 repeated
                [0, 1, 0, 0],
                [0, 0, 1, 0],  # 3 repeated
                [0, 0, 1, 0],
                [0, 0, 1, 0],
                [0, 0, 0, 1],  # 1 repeated
            ])}  # counts [4, 2, 3, 1] => [a, b, c, d]
        mock_instance.return_value.predict.side_effect = mock_low_predict

        data = pd.Series(['1'] * 10)
        profiler = DataLabelerColumn(data.name)
        profiler.update(data)
        self.assertEqual("a|c|b", profiler.data_label)

    def test_profile(self, mock_instance):
        self._setup_data_labeler_mock(mock_instance)

        data = pd.Series(['1', '2', '3'])
        profiler = DataLabelerColumn(data.name)

        expected_profile = {
            "avg_predictions": dict(a=2/3, b=1/3),
            "data_label_representation": dict(a=2/3, b=1/3),
            "times": defaultdict(float, {'data_labeler_predict': 1.0})
        }

        time_array = [float(i) for i in range(4, 0, -1)]
        with patch('time.time', side_effect=lambda: time_array.pop()):
            # Validate that the times dictionary is empty
            self.assertEqual(defaultdict(float), profiler.profile['times'])
            profiler.update(data)

            # Validate the time in the DataLabeler class has the expected time.
            profile = profiler.profile
            self.assertDictEqual(expected_profile, profile)

            # Validate time in datetime class has expected time after second update
            profiler.update(data)
            expected = defaultdict(float, {'data_labeler_predict': 2.0})
            self.assertEqual(expected, profiler.profile['times'])


    def test_label_match(self, mock_instance):
        """
        Test label match between avg_prediction and data_label_representation
        """
        mock_DataLabeler = mock_instance.return_value
        mock_DataLabeler.label_mapping = \
            {"a": 0, "b": 1, "c": 1, "d": 2, "e": 2, "f": 3}
        mock_DataLabeler.reverse_label_mapping = \
            {0: "a", 1: "c", 2: "e", 3: "f"}
        mock_DataLabeler.model.num_labels = 4

        data = pd.Series(['1', '2', '3', '4', '5', '6'])
        profiler = DataLabelerColumn(data.name)
        profiler.sample_size = 1

        self.assertEqual(["a", "c", "e", "f"], profiler._possible_data_labels)
        self.assertDictEqual(dict(a=0, c=0, e=0, f=0), profiler.label_representation)
        self.assertDictEqual(dict(a=0, c=0, e=0, f=0), profiler.avg_predictions)


    def test_profile_merge(self, mock_instance):
        self._setup_data_labeler_mock(mock_instance)

        data = pd.Series(['1', '2', '3', '11'])
        data2 = pd.Series(['4', '5', '6', '7', '9', '10', '12'])

        expected_profile = {
            "avg_predictions": dict(a=54 / 99, b=45 / 99),
            "data_label_representation": dict(a=54 / 99, b=45 / 99),
            "times": defaultdict(float, {'data_labeler_predict': 2.0})
        }
        expected_sum_predictions = [6, 5]
        expected_rank_distribution = {'a': 6, 'b': 5}

        time_array = [float(i) for i in range(4, 0, -1)]
        with patch('time.time', side_effect=lambda: time_array.pop()):
            profiler = DataLabelerColumn(data.name)
            profiler.update(data)

            profiler2 = DataLabelerColumn(data2.name)
            profiler2.update(data2)

            profiler3 = profiler + profiler2

            # Assert correct values
            self.assertEqual(expected_profile, profiler3.profile)
            self.assertEqual(expected_sum_predictions,
                             profiler3._sum_predictions.tolist())
            self.assertEqual(expected_rank_distribution,
                             profiler3.rank_distribution)
            self.assertEqual(expected_profile, profiler3.profile)
            self.assertEqual(profiler.data_labeler, profiler3.data_labeler)
            self.assertEqual(profiler._possible_data_labels,
                             profiler3._possible_data_labels)
            self.assertEqual(profiler._top_k_voting, profiler3._top_k_voting)
            self.assertEqual(profiler._min_voting_prob,
                             profiler3._min_voting_prob)
            self.assertEqual(profiler._min_prob_differential,
                             profiler3._min_prob_differential)
            self.assertEqual(profiler._top_k_labels, profiler3._top_k_labels)
            self.assertEqual(profiler._min_top_label_prob,
                             profiler3._min_top_label_prob)
            self.assertEqual(profiler._max_sample_size,
                             profiler3._max_sample_size)
            self.assertEqual(profiler._top_k_voting, profiler3._top_k_voting)

            # Check adding even more profiles together
            profiler3 = profiler + profiler3
            expected_profile = {
                "avg_predictions": dict(a=8 / 15, b=7 / 15),
                "data_label_representation": dict(a=8 / 15, b=7 / 15),
                "times": defaultdict(float, {'data_labeler_predict': 3.0})
            }
            expected_sum_predictions = [8, 7]
            expected_rank_distribution = {'a': 8, 'b': 7}

            # Assert only the proper changes have been made
            self.assertEqual(expected_profile, profiler3.profile)
            self.assertEqual(expected_sum_predictions,
                             profiler3._sum_predictions.tolist())
            self.assertEqual(expected_rank_distribution,
                             profiler3.rank_distribution)
            self.assertEqual(expected_profile, profiler3.profile)
            self.assertEqual(profiler.data_labeler, profiler3.data_labeler)
            self.assertEqual(profiler._possible_data_labels,
                             profiler3._possible_data_labels)
            self.assertEqual(profiler._top_k_voting, profiler3._top_k_voting)
            self.assertEqual(profiler._min_voting_prob,
                             profiler3._min_voting_prob)
            self.assertEqual(profiler._min_prob_differential,
                             profiler3._min_prob_differential)
            self.assertEqual(profiler._top_k_labels, profiler3._top_k_labels)
            self.assertEqual(profiler._min_top_label_prob,
                             profiler3._min_top_label_prob)
            self.assertEqual(profiler._max_sample_size,
                             profiler3._max_sample_size)
            self.assertEqual(profiler._top_k_voting, profiler3._top_k_voting)

        # Check that error is thrown if profiles are unequal
        with self.assertRaises(ValueError):
            profiler._top_k_voting = 13
            test = profiler + profiler2
