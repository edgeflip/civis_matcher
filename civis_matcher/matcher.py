import json

import requests


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

    def __init__(self, user='edgeflip', password='civis!19'):
        self.auth = (user, password)

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
        resp = requests.get(url, auth=self.auth, params=request_params)
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

        data['result'].update({'url': resp.url})
        return MatchResult(**data['result'])
