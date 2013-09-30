import json
import hashlib
import logging
from datetime import datetime, timedelta

import boto
from boto.exception import S3ResponseError

import pylibmc
import requests
from urllib import urlencode


CIVIS_BASE_URL = 'http://match.civisanalytics.com'
TIME_FORMAT = '%m-%d-%y_%H:%M:%S'
logger = logging.getLogger(__name__)


class MatchException(Exception):
    pass


class Struct(object):
    def __init__(self, **entries):
        self.__dict__.update(entries)


class Person(Struct):

    def __unicode__(self):
        return u'Person: %s %s' % (self.first_name, self.last_name)

    def __str__(self):
        return self.__unicode__()

    def __repr__(self):
        return self.__unicode__()


class MatchResult(Struct):

    def __init__(self, **entries):
        self.__dict__.update(entries)
        self.url = ''
        people_list = []
        if self.people:
            for person in self.people:
                people_list.append(Person(**person))

        self.people = people_list

    def __unicode__(self):
        return u'MatchResult: %s' % self.url

    def __str__(self):
        return self.__unicode__()

    def __repr__(self):
        return self.__unicode__()


class CivisMatcher(object):

    def __init__(self, user='edgeflip', password='civis!19',
                 cache_hosts=[], cache_expiry=3600, base_url='',
                 timeout=5):
        self.auth = (user, password)
        self.caching_enabled = False
        self.expiry = cache_expiry
        if cache_hosts:
            self.cache = pylibmc.Client(cache_hosts)
            self.caching_enabled = True

        # Useful if you want to test against their staging instance
        self.base_url = base_url if base_url else CIVIS_BASE_URL
        self.timeout = timeout

    def _check_cache(self, url, params):
        ''' Checks the cache for Civis match results. Hashes the URL plus the
        params used in the check to create a key.
        '''
        if not self.caching_enabled:
            return None

        url_hash = hashlib.md5('%s?%s' % (url, urlencode(params))).hexdigest()
        return self.cache.get(url_hash)

    def _set_cache(self, url, params, data):
        ''' Sets the cache with the key being a hashed form of the URL and
        params
        '''
        if self.caching_enabled:
            url_hash = hashlib.md5('%s?%s' % (url, params)).hexdigest()
            self.cache.set(url_hash, data, time=self.expiry)

    def _validate_result(self, resp):
        if resp.status_code != 200:
            logger.error('Invalid status code (%s) on %s' % (
                resp.status_code,
                resp.url
            ))
            raise MatchException(
                'Invalid response code: %s, url: %s' % (
                    resp.status_code,
                    resp.url
                )
            )

        data = json.loads(resp.content)
        if data.get('error'):
            logger.error('Civis Error: %s, %s' % (
                data['error_id'],
                data['error_message']
            ))
            raise MatchException(
                'Error returned by Civis: id: %s, message: %s, url: %s' % (
                    data['error_id'],
                    data['error_message'],
                    resp.url
                )
            )
        return data

    def _get(self, url, params):
        req_url = '%s?%s' % (url, urlencode(params))
        resp = requests.get(req_url, auth=self.auth, timeout=self.timeout)
        data = self._validate_result(resp)
        self._set_cache(url, params, data)
        return data

    def _post(self, url, params):
        resp = requests.post(url, data=json.dumps(params),
                            auth=self.auth, timeout=self.timeout)
        data = self._validate_result(resp)
        post_url = '%s?%s' % (url, urlencode(params))
        self._set_cache(post_url, params, data)
        return data

    def _check_civis(self, url, params, method):
        ''' Makes an actual call to Civis in the event that we don't already
        have anything stored in the cache
        '''
        if method == 'GET':
            return self._get(url, params)
        elif method == 'POST':
            return self._post(url, params)

    def _make_request(self, url, params, method='GET'):
        ''' Helper function for making a request to Civis. Checks our cache
        before moving on the actually make a request to Civis.
        '''
        data = self._check_cache(url, params)
        if not data:
            data = self._check_civis(url, params, method)
        return data, '%s?%s' % (url, urlencode(params))

    def match(self, first_name, last_name, **kwargs):
        '''
        Performs a request against the Civis Matching service with the
        provided information. First and last name are required. The other
        optional fields are:

            birth_year
            birth_month
            birth_day
            state
            city

        '''
        url = '%s/match' % self.base_url
        request_params = kwargs
        request_params.update({
            'first_name': first_name,
            'last_name': last_name
        })
        data, req_url = self._make_request(url, request_params)

        data['result'].update({'url': req_url})
        return MatchResult(**data['result'])

    def bulk_match(self, match_dict):
        '''
        Performs a bulk match query against the Civis Matching service. Expects
        a dictionary structured like so:

            {'people': {
                '01': {
                    'first_name': 'Test',
                    'last_name': 'User1',
                    'state': 'IL',
                    'city': 'Chicago',
                },
                '02': {
                    'first_name': 'Test',
                    'last_name': 'User2',
                    'state': 'IL',
                    'city': 'Chicago',
                }
            }

        Responses look like:

            {u'0': {u'error': False,
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
                        u'scores': {u'gotv_score': 0,
                        u'persuasion_score': 25.59,
                        u'persuasion_score_dec': 3,
                        u'support_cand_2013': 52.085,
                        u'support_cand_2013_dec': 7,
                        u'turnout_2013': 85.419,
                        u'turnout_2013_dec': 9},
                        u'state': u'VA'}],
                    u'people_count': 1,
                    u'scores': {u'gotv_score': {u'count': 1,
                        u'max': 0,
                        u'mean': 0,
                        u'min': 0,
                        u'std': 0}
                    }
                }
            }
        }

        '''
        url = '%s/multimatch' % self.base_url
        data, req_url = self._make_request(url, match_dict, 'POST')
        full_result = {}
        for k, v in data.items():
            if 'result' in v:
                full_result[k] = MatchResult(**v['result'])
            else:
                logger.warn('Match Result Error: %s' % v)
        return full_result


class S3CivisMatcher(CivisMatcher):

    def __init__(self, aws_access_key_id, aws_secret_access_key,
                 user='edgeflip', password='civis!19',
                 bucket='civis_cache', cache_expiry_days=30,
                 base_url='', timeout=5):
        self.auth = (user, password)
        self.caching_enabled = False
        self.expiry = datetime.now() - timedelta(days=cache_expiry_days)
        self.base_url = base_url if base_url else CIVIS_BASE_URL
        self.timeout = timeout
        self.s3_conn = boto.connect_s3(
            aws_access_key_id, aws_secret_access_key
        )
        self.bucket = self._get_bucket(bucket)

    def _get_bucket(self, bucket_name):
        ''' Retrieves bucket if it exists, otherwise creates it '''
        try:
            bucket = self.s3_conn.get_bucket(bucket_name)
        except S3ResponseError:
            try:
                bucket = self.s3_conn.create_bucket(bucket_name)
            except S3ResponseError:
                logger.error(
                    'Failed to obtain connection to bucket: %s' % bucket_name
                )
                raise

        return bucket

    def cache_match(self, fbids):
        missing_count = 0
        match_results = {}
        for fbid in fbids:
            key = self.bucket.get_key(fbid)
            if not key:
                missing_count += 1
                continue

            match_results[fbid] = json.loads(key.get_contents_as_string())

        return match_results, missing_count

    def _store_match_results(self, data):
        for fbid, match in data.iteritems():
            match_key = self.bucket.get_key(fbid)
            if match_key:
                stored_json = json.loads(match_key.get_contents_as_string())
            else:
                match_key = self.bucket.new_key(fbid)
                stored_json = {}

            people_count = stored_json.get('result', {}).get('people_count', 0)
            match_count = match.get('result', {}).get('people_count', 0)
            cache_time = datetime.strptime(
                stored_json.get('timestamp', datetime.now().strftime(TIME_FORMAT)),
                TIME_FORMAT
            )
            if (not stored_json or
                    match_count > people_count or
                    cache_time < self.expiry):
                match['timestamp'] = datetime.now().strftime(TIME_FORMAT)
                match_key.set_contents_from_string(json.dumps(match))

    def bulk_match(self, match_dict, raw=False):
        ''' Very similar to its parent in regards to how the bulk matching
        is performed, however it does contain some minor differences. Instead
        of returning result objects, this will return raw JSON, and also
        will store that raw JSON in S3 for later usage
        '''
        url = '%s/multimatch' % self.base_url
        data, req_url = self._make_request(url, match_dict, 'POST')
        self._store_match_results(data)
        return data
