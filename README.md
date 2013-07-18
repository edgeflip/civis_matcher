# Civis Matcher

Library for wrapping the Civis Analytics Matching API

## Installation:

This package depends on `libmemcached-dev`, as it has optional caching 
support built-in. After that it's as simple as:

    git clone https://github.com/edgeflip/civis_matcher
    cd civis_matcher
    pip install -r requirements.txt
    python setup.py develop

After that, you should be good to go.

## Usage:

Using the Civis Matcher API is fairly straightforward:

    from civis_matcher import matcher
    cm = matcher.CivisMatcher()
    result = cm.match('First_Name', 'Last_Name', state='IL')

The example above is a fairly standard usage of the API. All of the fields that
can be passed to the API's match service are as follows:

* first_name
* last_name
* city
* state
* birth_year
* birth_month
* birth_day

Also, in the event that the authentication credentials as some point change, 
you can also pass in a new authentication credentials like so:

    from civis_matcher import matcher
    cm = matcher.CivisMatcher(user='username', password='password')

Results come back from the API as JSON, which we convert into Python objects in 
the form of MatchResults. At the top level of these objects are information about
the request/response, such as:

* url (str)
* score_mean (int)
* score_max (int)
* score_min (int)
* score_std (int)
* people_count (int)
* more_people (bool)
* people (list of matcher.Person objects)

The ``people`` list contains matcher.Person objects which have the following 
attributes:

* first_name
* last_name
* city
* state
* birth_year
* birth_month
* birth_day
* gender
* id
* dma
* dma_name
* score
* TokenCount
* nick_name

### Bulk Matching

Civis recently gave us the ability to perform bulk match queries. These will 
help cut down on making large quantities of calls to check a large dataset for 
matches. In order to use this service, you need to build a `dict` like so:


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

The '01', '02', etc. can be whatever you desire. Any unique identifier that'll
help you match results back to where you generated the `dict` from will work
just fine. After you've built that structure, you can do the following:

    from civis_matcher import matcher
    cm = matcher.CivisMatcher()
    result = cm.bulk_match(YOUR_DICTIONARY)

The structure of the result object will be like so:

    {
        u'0': MatchResult: Object,
        u'1': MatchResult: Object,
        u'2': MatchResult: Object,
        u'3': MatchResult: Object
    }

The `MatchResult` objects are not any different than what you'd get if you did
a single match against the API. 
