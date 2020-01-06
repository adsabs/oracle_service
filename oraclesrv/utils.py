
from flask import current_app
import requests

from oraclesrv.client import client

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

    try:
        result, status_code = get_solr_data(rows, query, fl='bibcode')
    except requests.exceptions.HTTPError as e:
        current_app.logger.error(e)
        result = {'error from solr':'%d: %s'%(e.response.status_code, e.response.reason)}
        status_code = e.response.status_code
    return result, query, status_code


def get_solr_data_match(abstract, title):
    """

    :param abstract:
    :param title:
    :param author:
    :return:
    """
    rows = 10
    # if there is an abstract, query solr on that, otherwise query on title
    # note that it seems when abstract is available combining querying abstract and title does not work
    if abstract.lower() != 'not available':
        query = 'topn({rows}, similar("{abstract}", input abstract, {number_matched_terms_abstract}, 1, 1))'.format(rows=rows,
                          abstract=abstract, number_matched_terms_abstract=int(abstract.count(' ') * 0.3))
    else:
        query = 'topn({rows}, similar("{title}", input title, {number_matched_terms_title}, 1, 1))'.format(rows=rows,
                          title=title, number_matched_terms_title=int(title.count(' ') * 0.75))

    try:
        result, status_code = get_solr_data(rows, query, fl='bibcode,abstract,title,author_norm,year,doctype')
    except requests.exceptions.HTTPError as e:
        current_app.logger.error(e)
        result = {'error from solr':'%d: %s'%(e.response.status_code, e.response.reason)}
        status_code = e.response.status_code

    return result, query, status_code
