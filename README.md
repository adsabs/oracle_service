# oracle_service

[![Build Status](https://travis-ci.org/adsabs/oracle_service.svg)](https://travis-ci.org/adsabs/oracle_service)
[![Coverage Status](https://coveralls.io/repos/adsabs/oracle_service/badge.svg)](https://coveralls.io/r/adsabs/oracle_service?branch=master)


# ADS Reference Service

## Short Summary

This microservice provides article recommendation for ADS users.



## Setup (recommended)

 $ virtualenv python
 $ source python/bin/activate
 $ pip install -r requirements.txt
 $ pip install -r dev-requirements.txt
 $ vim local_config.py # edit, edit

 
## Testing

On your desktop run:

 $ py.test
 

## API

### GET a request:
 /readhist

### POST a request:

To get recommendation you do a POST request to the endpoint

    https://api.adsabs.harvard.edu/v1/oracle/readhist

within the POST, payload can have the following optinal prameters `function`, `sort`, `num_docs`, `cutoff_days`, and `top_n_reads`.
* Possible values for parameter `function` are: `similar`, `trending`, `useful`, and `reviews`. Default is `similar`.
* Possible values for parameter `sort` are any sort options, the default is `entry_date`.
* `num_docs` is number of recommendation documents. Default is 5.
* `cutoff_days` is number days going back from today for including published papers. Default is 5.
* `top_n_reads` is number of articles read to consider. Default is 10.

For example payload of, 
 
    {"function": "similar", "sort": "entry_date", "num_docs": 5, "cutoff_days": 5, "top_n_reads": 10}

produces the query:

    (similar(topn(10, reader:{reader}, entry_date desc)) entdate:[NOW-5DAYS TO *])


`reader` is a 16-digit ananoymous user id that gets extracted from session id.

To call oracle service `/readhist` do

    curl -H "Authorization: Bearer <your API token>" -H "Content-Type: application/json" -X POST -d '{"function": "similar", "sort": "entry_date", "num_docs": 5, "cutoff_days": 5, "top_n_reads": 10}' https://api.adsabs.harvard.edu/v1/oracle/readhist

and the API then responds in JSON with query that was executed and the list of bibcodes returned from the query.

    {"query": "...", "bibcodes": "..."}



To find match to merge two papers you do a POST request to the endpoint

    https://api.adsabs.harvard.edu/v1/oracle/matchdoc

within the POST, payload should have the following required prameters `abstract`, `title`, and `author`.
* `abstract` is the abstract of the paper to find a match for.
* `title` is the title of the paper.
* `author` is the list of authors, comma separated.

To call oracle service `/matchdoc` do

    curl -H "Authorization: Bearer <your API token>" -H "Content-Type: application/json" -X POST -d '{"abstract": "<abstract text>", "title": "<title text>", "author": <"comma separated author list">}' https://api.adsabs.harvard.edu/v1/oracle/matchdoc

and the API then responds in JSON with query that was executed and the list of bibcodes with their corresponding scores for matched abstract, title and author.

    {"query": "...", "match": [{"bibcode": "...", "scores": {"abstract": 0.89, "author": 1, "title": 1.0}}]}



## Maintainers

Golnaz