import json
import hashlib

import pylibmc
import requests
from urllib import urlencode


CIVIS_BASE_URL = 'http://match.civisanalytics.com'


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
        people_list = []
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
                cache_hosts=[], cache_expiry=3600):
        self.auth = (user, password)
        self.caching_enabled = False
        self.expiry = cache_expiry
        if cache_hosts:
            self.cache = pylibmc.Client(cache_hosts)
            self.caching_enabled = True

    def _check_cache(self, url):
        ''' Checks the cache for Civis match results. Hashes the URL plus the
        params used in the check to create a key.
        '''
        if not self.caching_enabled:
            return None

        url_hash = hashlib.md5(url).hexdigest()
        return self.cache.get(url_hash)

    def _set_cache(self, url, data):
        ''' Sets the cache with the key being a hashed form of the URL and
        params
        '''
        if self.caching_enabled:
            url_hash = hashlib.md5(url).hexdigest()
            self.cache.set(url_hash, data, time=self.expiry)

    def _check_civis(self, url):
        ''' Makes an actual call to Civis in the event that we don't already
        have anything stored in the cache
        '''
        resp = requests.get(url, auth=self.auth)
        if resp.status_code != 200:
            raise MatchException(
                'Invalid response code: %s, url: %s' % (
                    resp.status_code,
                    resp.url
                )
            )

        data = json.loads(resp.content)
        if data['error']:
            raise MatchException(
                'Error returned by Civis: id: %s, message: %s, url: %s' % (
                    data['error_id'],
                    data['error_message'],
                    resp.url
                )
            )

        self._set_cache(url, data)
        return data

    def _make_request(self, url, params):
        ''' Helper function for making a request to Civis. Checks our cache
        before moving on the actually make a request to Civis.
        '''
        req_url = '%s?%s' % (url, urlencode(params))
        data = self._check_cache(req_url)
        if not data:
            data = self._check_civis(req_url)
        return data, req_url

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
        url = '%s/match' % CIVIS_BASE_URL
        request_params = kwargs
        request_params.update({
            'first_name': first_name,
            'last_name': last_name
        })
        data, req_url = self._make_request(url, request_params)

        data['result'].update({'url': req_url})
        return MatchResult(**data['result'])
