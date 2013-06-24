civis_matcher
=============

Library for wrapping the Civis Analytics Matching API

Usage:
-------------

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
