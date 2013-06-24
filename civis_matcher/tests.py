import unittest
import json
from mock import Mock

from civis_matcher import matcher


class TestCivisMatcher(unittest.TestCase):

    def setUp(self):
        super(TestCivisMatcher, self).setUp()
        self.orig_requests_get = matcher.requests.get
        self.requests_mock = Mock()
        matcher.requests.get = self.requests_mock
        self.cm = matcher.CivisMatcher()

    def tearDown(self):
        super(TestCivisMatcher, self).tearDown()

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
