
from flask import current_app
from fuzzywuzzy import fuzz


from oraclesrv.client import client
from oraclesrv.authors import get_author_score

def get_solr_data(rows, query, fl):
    """

    :param rows:
    :param query:
    :return:
    """
    response = client().get(
        url=current_app.config['ORACLE_SERVICE_SOLRQUERY_URL'],
        headers={'Authorization': 'Bearer ' + current_app.config['ORACLE_SERVICE_ADSWS_API_TOKEN']},
        params={'fl': fl, 'rows': rows, 'q': query},
    )

    response.raise_for_status()

    from_solr = response.json()
    num_docs = from_solr['response'].get('numFound', 0)
    if num_docs > 0:
        current_app.logger.debug('Got {num_docs} records from solr.'.format(num_docs=num_docs))
        result = []
        for doc in from_solr['response']['docs']:
            if fl == 'bibcode':
                result.append(doc['bibcode'])
            else:
                result.append(doc)
        return result, response.status_code
    return None, response.status_code

def get_solr_data_recommend(function, reader, rows=5, sort='entry_date', cutoff_days=5, top_n_reads=10):
    """

    :param reader:
    :param rows:
    :param sort:
    :param cutoff_days:
    :param top_n_reads:
    :return:
    """
    query = '({function}(topn({topn}, reader:{reader}, {sort} desc)) entdate:[NOW-{cutoff_days}DAYS TO *])'.format(
               function=function, topn=top_n_reads, reader=reader, sort=sort, cutoff_days=cutoff_days)

    result, status_code = get_solr_data(rows, query, fl='bibcode')
    return result, query, status_code

def get_solr_data_match(abstract, title):
    """

    :param abstract:
    :param title:
    :param author:
    :return:
    """
    rows = 2
    if abstract.lower() != 'not available':
        # seems that title query does not work, shall check with Roman later
        # query = 'topn({rows}, similar("{abstract}", input abstract, {number_matched_terms_abstract}, 2) AND ' \
        #                      'similar("{title}", input title, {number_matched_terms_title}, 2))'.format(rows=rows,
        #                   abstract=abstract, number_matched_terms_abstract=int(abstract.count(' ') * 0.3),
        #                   title=title, number_matched_terms_title=int(title.count(' ') * 0.75))
        query = 'topn({rows}, similar("{abstract}", input abstract, {number_matched_terms_abstract}, 2))'.format(rows=rows,
                          abstract=abstract, number_matched_terms_abstract=int(abstract.count(' ') * 0.3))
    else:
        query = 'topn({rows}, similar("{title}", input title, {number_matched_terms_title}, 2))'.format(rows=rows,
                          title=title, number_matched_terms_title=int(title.count(' ') * 0.75))

    result, status_code = get_solr_data(rows, query, fl='bibcode,abstract,title,author')
    return result, query, status_code

def score_match(abstract, title, author, matched_docs):
    """

    :param abstract:
    :param title:
    :param author:
    :param matched_doc:
    :return:
    """
    results = []
    for doc in matched_docs:
        match_abstract = doc.get('abstract', '').encode('ascii', 'ignore').decode('ascii')
        match_title = ' '.join(doc.get('title', [])).encode('ascii', 'ignore').decode('ascii')
        match_author = [a.encode('ascii', 'ignore').decode('ascii') for a in doc.get('author', [])]

        scores = []
        if abstract.lower() != 'not available':
            scores.append(fuzz.token_set_ratio(abstract, match_abstract)/100.0)
        scores.append(fuzz.partial_ratio(title, match_title)/100.0)
        scores.append(get_author_score(author, match_author))

        if all(score >= 0.7 for score in scores):
            if len(scores) == 3:
                results.append({'bibcode': doc.get('bibcode', ''),
                                'scores': {'abstract':scores[0], 'title': scores[1], 'author': scores[2]}})
            elif len(scores) == 2:
                results.append({'bibcode': doc.get('bibcode', ''),
                                'scores': {'title': scores[0], 'author': scores[1]}})

    return results