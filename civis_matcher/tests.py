import unittest
import json
from datetime import datetime, timedelta

from mock import Mock
from boto.exception import S3ResponseError

from civis_matcher import matcher


class BaseCivisMatcher(unittest.TestCase):

    def setUp(self):
        super(BaseCivisMatcher, self).setUp()

        # Requests Mock
        self.orig_requests_get = matcher.requests.get
        self.orig_requests_post = matcher.requests.post
        self.requests_mock = Mock()
        matcher.requests.get = self.requests_mock
        matcher.requests.post = self.requests_mock

        # pylibmc Mock
        self.orig_cache_client = matcher.pylibmc.Client
        self.cache_mock = Mock()
        self.client_mock = Mock()
        self.client_mock.set.return_value = None
        self.client_mock.get.return_value = None
        self.cache_mock.return_value = self.client_mock
        matcher.pylibmc.Client = self.cache_mock

        self.cm = matcher.CivisMatcher(cache_hosts=['127.0.0.1'])

    def tearDown(self):
        matcher.requests.get = self.orig_requests_get
        matcher.requests.post = self.orig_requests_post
        matcher.pylibmc.Client = self.orig_cache_client

        super(BaseCivisMatcher, self).tearDown()


class TestCivisMatcher(BaseCivisMatcher):

    def test_invalid_status_code(self):
        ''' Tests what occurs when CivisMatcher is given an invalid, non-200
        status code response. It should raise a MatchException.
        '''
        self.requests_mock.return_value = Mock(
            status_code=301,
            url='http://example.com/test-failure'
        )
        with self.assertRaises(matcher.MatchException) as e:
            self.cm.match('Test', 'User', state='IL')

        self.assertEqual(
            e.exception.message,
            'Invalid response code: 301, url: http://example.com/test-failure'
        )

    def test_error_response(self):
        ''' Test what occurs when Civis returns an error to us. Should raise
        a MatchException
        '''
        self.requests_mock.return_value = Mock(
            status_code=200,
            url='http://example.com/test-failure',
            content=json.dumps({
                'error': True,
                'error_id': 1,
                'error_message': 'Fail',
            })
        )
        with self.assertRaises(matcher.MatchException) as e:
            self.cm.match('Test', 'User', state='IL')

        self.assertEqual(
            e.exception.message,
            'Error returned by Civis: id: 1, message: Fail, url: http://example.com/test-failure'
        )

    def test_successful_match(self):
        ''' Test a successful match returned from Civis '''
        self.requests_mock.return_value = Mock(
            status_code=200,
            url='http://example.com/test-failure',
            content=json.dumps({
                'error': False,
                'result': {
                    'score_mean': 357,
                    'score_min': 357,
                    'score_max': 357,
                    'score_std': 0,
                    'people_count': 1,
                    'more_people': False,
                    'people': [{
                        'id': '194446445',
                        'gender': 'M',
                        'first_name': 'Test',
                        'last_name': 'User',
                        'nick_name': 'TESTUSER',
                        'city': 'BELMONT',
                        'state': 'MA',
                        'birth_day': '11',
                        'birth_month': '07',
                        'birth_year': '1984',
                        'dma': '506',
                        'dma_name': 'Boston MA (Manchester NH)',
                        'score': 357,
                        'TokenCount': 6
                    }]
                }
            })
        )
        result = self.cm.match('Test', 'User')
        assert isinstance(result, matcher.MatchResult)
        assert isinstance(result.people[0], matcher.Person)
        person = result.people[0]
        self.assertEqual(person.first_name, 'Test')
        self.assertEqual(person.last_name, 'User')
        self.assertEqual(result.score_mean, 357)
        self.assertEqual(result.people_count, 1)

    def test_successful_bulk_match(self):
        ''' Tests a successful match against the multimatch end point '''
        self. requests_mock.return_value = Mock(
            status_code=200,
            url='http://example.com/test-failure',
            content=json.dumps({
                u'0': {
                    u'error': False,
                    u'result': {u'more_people': False,
                    u'people': [{u'TokenCount': 6,
                            u'birth_day': u'01',
                            u'birth_month': u'12',
                            u'birth_year': u'1969',
                            u'city': u'CHARLOTTESVILLE',
                            u'dma': u'584',
                            u'dma_name': u'Charlottesville VA',
                            u'first_name': u'TEST',
                            u'gender': u'M',
                            u'id': u'16595385',
                            u'last_name': u'USER',
                            u'nick_name': u'TESTUSER',
                            u'scores': {
                                u'gotv_score': 0,
                                u'persuasion_score': 25.59,
                                u'persuasion_score_dec': 3,
                                u'support_cand_2013': 52.085,
                                u'support_cand_2013_dec': 7,
                                u'turnout_2013': 85.419,
                                u'turnout_2013_dec': 9},
                            u'state': u'VA'}],
                    u'people_count': 1,
                    u'scores': {u'gotv_score': {u'count': 1,
                        u'max': 23.592,
                        u'mean': 23.592,
                        u'min': 23.592,
                        u'std': 0},
                    u'persuasion_score': {u'count': 1,
                        u'max': 17.161,
                        u'mean': 17.161,
                        u'min': 17.161,
                        u'std': 0},
                                }}
                }
            })
        )
        match_dict = {
            'people': {
                0: {'city': 'Arlington',
                    'first_name': 'Molly',
                    'last_name': 'Ball',
                    'state': 'VA'},
                1: {'city': 'Burke',
                    'first_name': 'Luanne',
                    'last_name': 'Smith',
                    'state': 'VA'},
                2: {'birth_day': '04',
                    'birth_month': '05',
                    'birth_year': '1958',
                    'city': 'Chester',
                    'first_name': 'David',
                    'last_name': 'Martin',
                    'state': 'VA'},
                3: {'birth_day': '01',
                    'birth_month': '12',
                    'birth_year': '1969',
                    'city': 'Charlottesville',
                    'first_name': 'David',
                    'last_name': 'Swanson',
                    'state': 'VA'}
            }
        }
        result = self.cm.bulk_match(match_dict)['0']
        self.assertEqual(result.people[0].first_name, 'TEST')
        self.assertEqual(result.people[0].last_name, 'USER')
        self.assertEqual(result.people[0].scores['persuasion_score'], 25.59)

    def test_successful_bulk_match_raw(self):
        ''' Tests a successful match against the multimatch end point '''
        self. requests_mock.return_value = Mock(
            status_code=200,
            url='http://example.com/test-failure',
            content=json.dumps({
                u'0': {
                    u'error': False,
                    u'result': {u'more_people': False,
                    u'people': [{u'TokenCount': 6,
                            u'birth_day': u'01',
                            u'birth_month': u'12',
                            u'birth_year': u'1969',
                            u'city': u'CHARLOTTESVILLE',
                            u'dma': u'584',
                            u'dma_name': u'Charlottesville VA',
                            u'first_name': u'TEST',
                            u'gender': u'M',
                            u'id': u'16595385',
                            u'last_name': u'USER',
                            u'nick_name': u'TESTUSER',
                            u'scores': {
                                u'gotv_score': 0,
                                u'persuasion_score': 25.59,
                                u'persuasion_score_dec': 3,
                                u'support_cand_2013': 52.085,
                                u'support_cand_2013_dec': 7,
                                u'turnout_2013': 85.419,
                                u'turnout_2013_dec': 9},
                            u'state': u'VA'}],
                    u'people_count': 1,
                    u'scores': {u'gotv_score': {u'count': 1,
                        u'max': 23.592,
                        u'mean': 23.592,
                        u'min': 23.592,
                        u'std': 0},
                    u'persuasion_score': {u'count': 1,
                        u'max': 17.161,
                        u'mean': 17.161,
                        u'min': 17.161,
                        u'std': 0},
                                }}
                }
            })
        )
        match_dict = {
            'people': {
                0: {'city': 'Arlington',
                    'first_name': 'Molly',
                    'last_name': 'Ball',
                    'state': 'VA'},
                1: {'city': 'Burke',
                    'first_name': 'Luanne',
                    'last_name': 'Smith',
                    'state': 'VA'},
                2: {'birth_day': '04',
                    'birth_month': '05',
                    'birth_year': '1958',
                    'city': 'Chester',
                    'first_name': 'David',
                    'last_name': 'Martin',
                    'state': 'VA'},
                3: {'birth_day': '01',
                    'birth_month': '12',
                    'birth_year': '1969',
                    'city': 'Charlottesville',
                    'first_name': 'David',
                    'last_name': 'Swanson',
                    'state': 'VA'}
            }
        }
        result = self.cm.bulk_match(match_dict, True)
        assert isinstance(result, dict)
        self.assertEqual(
            result['0']['result']['people'][0]['first_name'],
            'TEST'
        )
        self.assertEqual(
            result['0']['result']['people'][0]['last_name'],
            'USER'
        )
        self.assertEqual(
            result['0']['result']['people'][0]['scores']['persuasion_score'],
            25.59
        )


class TestS3CivisMatcher(BaseCivisMatcher):

    def setUp(self):
        super(TestS3CivisMatcher, self).setUp()
        self.orig_boto = matcher.boto
        self.boto_mock = Mock()
        matcher.boto = self.boto_mock
        self.cm = matcher.S3CivisMatcher('KEY', 'SECRET_KEY')
        self.civis_result = {
            u'123456': {
                u'error': False,
                u'result': {u'more_people': False,
                u'people': [{u'TokenCount': 6,
                        u'birth_day': u'01',
                        u'birth_month': u'12',
                        u'birth_year': u'1969',
                        u'city': u'CHARLOTTESVILLE',
                        u'dma': u'584',
                        u'dma_name': u'Charlottesville VA',
                        u'first_name': u'TEST',
                        u'gender': u'M',
                        u'id': u'16595385',
                        u'last_name': u'USER',
                        u'nick_name': u'TESTUSER',
                        u'scores': {
                            u'gotv_score': 0,
                            u'persuasion_score': 25.59,
                            u'persuasion_score_dec': 3,
                            u'support_cand_2013': 52.085,
                            u'support_cand_2013_dec': 7,
                            u'turnout_2013': 85.419,
                            u'turnout_2013_dec': 9},
                        u'state': u'VA'}],
                u'people_count': 1,
                u'scores': {
                    u'gotv_score': {
                        u'count': 1,
                        u'max': 23.592,
                        u'mean': 23.592,
                        u'min': 23.592,
                        u'std': 0
                    },
                    u'persuasion_score': {
                        u'count': 1,
                        u'max': 17.161,
                        u'mean': 17.161,
                        u'min': 17.161,
                        u'std': 0
                    }
                }}
            }
        }

    def tearDown(self):
        matcher.boto = self.orig_boto
        super(TestS3CivisMatcher, self).tearDown()

    def test_get_bucket_failure(self):
        ''' Test the S3 bucket retrieval failure '''
        self.cm.s3_conn.get_bucket.side_effect = S3ResponseError('o', 'w')
        self.cm.s3_conn.create_bucket.side_effect = S3ResponseError('oh', 'no')
        with self.assertRaises(S3ResponseError):
            self.cm._get_bucket('bad bucket')

    def test_get_bucket_success(self):
        ''' Test a successful bucket retrieval '''
        self.cm.s3_conn.get_bucket.return_value = 'mrbucket_rocks'
        self.assertEqual(
            self.cm._get_bucket('mrbucket'),
            'mrbucket_rocks'
        )

    def test_store_match_results_new_key(self):
        ''' Tests the _store_match_results method with a new key'''
        self.cm.bucket = Mock()
        self.cm.bucket.get_key.return_value = None
        create_key_mock = Mock()
        self.cm.bucket.new_key.return_value = create_key_mock
        self.cm._store_match_results(self.civis_result)
        assert create_key_mock.set_contents_from_string.called
        store_data = json.loads(
            create_key_mock.set_contents_from_string.call_args_list[0][0][0]
        )
        self.assertEqual(
            store_data['result'],
            self.civis_result['123456']['result']
        )

    def test_store_match_results_existing_key(self):
        ''' Test of the result storage where we update an existing key '''
        self.cm.bucket = Mock()
        key_mock = Mock()
        key_data = self.civis_result.copy()
        key_data['timestamp'] = (datetime.now() - timedelta(days=100)).strftime(
            matcher.TIME_FORMAT
        )
        key_mock.get_contents_as_string.return_value = json.dumps(key_data)
        self.cm.bucket.get_key.return_value = key_mock
        self.cm._store_match_results(self.civis_result)
        assert key_mock.get_contents_as_string.called
        assert key_mock.set_contents_from_string.called

    def test_store_match_results_key_too_fresh(self):
        ''' Test result storage where an object is found to be new enough to be
        trusted
        '''
        self.cm.bucket = Mock()
        key_mock = Mock()
        key_data = self.civis_result.copy()
        key_data['123456']['timestamp'] = datetime.now().strftime(
            matcher.TIME_FORMAT
        )
        key_mock.get_contents_as_string.return_value = json.dumps(
            key_data['123456']
        )
        self.cm.bucket.get_key.return_value = key_mock
        self.cm._store_match_results(self.civis_result)
        assert key_mock.get_contents_as_string.called
        assert not key_mock.set_contents_from_string.called
