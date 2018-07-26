#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""Unit test for PubSub verifier."""

import logging
import unittest

import mock
from hamcrest import assert_that as hc_assert_that

from apache_beam.io.gcp.pubsub import PubsubMessage
from apache_beam.io.gcp.tests.pubsub_matcher import PubSubMessageMatcher

# Protect against environments where pubsub library is not available.
# pylint: disable=wrong-import-order, wrong-import-position
try:
  from google.cloud import pubsub
except ImportError:
  pubsub = None
# pylint: enable=wrong-import-order, wrong-import-position


@unittest.skipIf(pubsub is None, 'PubSub dependencies are not installed.')
class PubSubMatcherTest(unittest.TestCase):

  def setUp(self):
    self.mock_presult = mock.MagicMock()

  def init_matcher(self, with_attributes=False, strip_attributes=None):
    self.pubsub_matcher = PubSubMessageMatcher(
        'mock_project', 'mock_sub_name', ['mock_expected_msg'],
        with_attributes=with_attributes, strip_attributes=strip_attributes)

  @mock.patch('time.sleep', return_value=None)
  @mock.patch('apache_beam.io.gcp.tests.pubsub_matcher.'
              'PubSubMessageMatcher._get_subscription')
  def test_message_matcher_success(self, mock_get_sub, unsued_mock):
    self.init_matcher()
    self.pubsub_matcher.expected_msg = ['a', 'b']
    mock_sub = mock_get_sub.return_value
    mock_sub.pull.side_effect = [
        [(1, pubsub.message.Message(b'a', 'unused_id'))],
        [(2, pubsub.message.Message(b'b', 'unused_id'))],
    ]
    hc_assert_that(self.mock_presult, self.pubsub_matcher)
    self.assertEqual(mock_sub.pull.call_count, 2)

  @mock.patch('time.sleep', return_value=None)
  @mock.patch('apache_beam.io.gcp.tests.pubsub_matcher.'
              'PubSubMessageMatcher._get_subscription')
  def test_message_matcher_attributes_success(self, mock_get_sub, unsued_mock):
    self.init_matcher(with_attributes=True)
    self.pubsub_matcher.expected_msg = [PubsubMessage('a', {'k': 'v'})]
    mock_sub = mock_get_sub.return_value
    msg_a = pubsub.message.Message(b'a', 'unused_id')
    msg_a.attributes['k'] = 'v'
    mock_sub.pull.side_effect = [[(1, msg_a)]]
    hc_assert_that(self.mock_presult, self.pubsub_matcher)
    self.assertEqual(mock_sub.pull.call_count, 1)

  @mock.patch('time.sleep', return_value=None)
  @mock.patch('apache_beam.io.gcp.tests.pubsub_matcher.'
              'PubSubMessageMatcher._get_subscription')
  def test_message_matcher_attributes_fail(self, mock_get_sub, unsued_mock):
    self.init_matcher(with_attributes=True)
    self.pubsub_matcher.expected_msg = [PubsubMessage('a', {})]
    mock_sub = mock_get_sub.return_value
    msg_a = pubsub.message.Message(b'a', 'unused_id')
    msg_a.attributes['k'] = 'v'  # Unexpected.
    mock_sub.pull.side_effect = [[(1, msg_a)]]
    with self.assertRaisesRegexp(AssertionError, r'Unexpected'):
      hc_assert_that(self.mock_presult, self.pubsub_matcher)
    self.assertEqual(mock_sub.pull.call_count, 1)

  @mock.patch('time.sleep', return_value=None)
  @mock.patch('apache_beam.io.gcp.tests.pubsub_matcher.'
              'PubSubMessageMatcher._get_subscription')
  def test_message_matcher_strip_success(self, mock_get_sub, unsued_mock):
    self.init_matcher(with_attributes=True,
                      strip_attributes=['id', 'timestamp'])
    self.pubsub_matcher.expected_msg = [PubsubMessage('a', {'k': 'v'})]
    mock_sub = mock_get_sub.return_value
    msg_a = pubsub.message.Message(b'a', 'unused_id')
    msg_a.attributes['id'] = 'foo'
    msg_a.attributes['timestamp'] = 'bar'
    msg_a.attributes['k'] = 'v'
    mock_sub.pull.side_effect = [[(1, msg_a)]]
    hc_assert_that(self.mock_presult, self.pubsub_matcher)
    self.assertEqual(mock_sub.pull.call_count, 1)

  @mock.patch('time.sleep', return_value=None)
  @mock.patch('apache_beam.io.gcp.tests.pubsub_matcher.'
              'PubSubMessageMatcher._get_subscription')
  def test_message_matcher_strip_fail(self, mock_get_sub, unsued_mock):
    self.init_matcher(with_attributes=True,
                      strip_attributes=['id', 'timestamp'])
    self.pubsub_matcher.expected_msg = [PubsubMessage('a', {'k': 'v'})]
    mock_sub = mock_get_sub.return_value
    # msg_a is missing attribute 'timestamp'.
    msg_a = pubsub.message.Message(b'a', 'unused_id')
    msg_a.attributes['id'] = 'foo'
    msg_a.attributes['k'] = 'v'
    mock_sub.pull.side_effect = [[(1, msg_a)]]
    with self.assertRaisesRegexp(AssertionError, r'Stripped attributes'):
      hc_assert_that(self.mock_presult, self.pubsub_matcher)
    self.assertEqual(mock_sub.pull.call_count, 1)

  @mock.patch('time.sleep', return_value=None)
  @mock.patch('apache_beam.io.gcp.tests.pubsub_matcher.'
              'PubSubMessageMatcher._get_subscription')
  def test_message_matcher_mismatch(self, mock_get_sub, unused_mock):
    self.init_matcher()
    self.pubsub_matcher.expected_msg = ['a']
    mock_sub = mock_get_sub.return_value
    mock_sub.pull.return_value = [
        (1, pubsub.message.Message(b'c', 'unused_id')),
        (1, pubsub.message.Message(b'd', 'unused_id')),
    ]
    with self.assertRaises(AssertionError) as error:
      hc_assert_that(self.mock_presult, self.pubsub_matcher)
    self.assertEqual(mock_sub.pull.call_count, 1)
    self.assertItemsEqual(['c', 'd'], self.pubsub_matcher.messages)
    self.assertTrue(
        '\nExpected: Expected 1 messages.\n     but: Got 2 messages.'
        in str(error.exception.args[0]))

  @mock.patch('time.sleep', return_value=None)
  @mock.patch('apache_beam.io.gcp.tests.pubsub_matcher.'
              'PubSubMessageMatcher._get_subscription')
  def test_message_matcher_timeout(self, mock_get_sub, unused_mock):
    self.init_matcher()
    mock_sub = mock_get_sub.return_value
    mock_sub.return_value.full_name.return_value = 'mock_sub'
    self.pubsub_matcher.timeout = 0.1
    with self.assertRaisesRegexp(AssertionError, r'Expected 1.*\n.*Got 0'):
      hc_assert_that(self.mock_presult, self.pubsub_matcher)
    self.assertTrue(mock_sub.pull.called)


if __name__ == '__main__':
  logging.getLogger().setLevel(logging.INFO)
  unittest.main()
