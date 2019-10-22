
from flask import current_app
import requests

from oraclesrv.client import client

def get_solr_data(reader, rows=5, sort='entry_date', cutoff_days=5, top_n_reads=10):
    """

    :param reader:
    :param rows:
    :param sort:
    :param cutoff_days:
    :param top_n_reads:
    :return:
    """
    query = '(similar(topn({topn}, reader:{reader}, {sort} desc)) entdate:[NOW-{cutoff_days}DAYS TO *])'.format(
                     topn=top_n_reads, reader=reader, sort=sort, cutoff_days=cutoff_days)
    try:
        response = client().get(
            url=current_app.config['ORACLE_SERVICE_SOLRQUERY_URL'],
            headers={'Authorization': 'Bearer ' + current_app.config['ORACLE_SERVICE_ADSWS_API_TOKEN']},
            params={'fl': 'bibcode', 'rows': rows, 'q': query},
        )
        if response.status_code == 200:
            from_solr = response.json()
            if from_solr.get('response'):
                num_docs = from_solr['response'].get('numFound', 0)
                if num_docs > 0:
                    current_app.logger.debug('Got {num_docs} records from solr.'.format(num_docs=num_docs))
                    result = []
                    for doc in from_solr['response']['docs']:
                        result.append(doc['bibcode'])
                    return result, query
        current_app.logger.error('Solr returned {response}.'.format(response=response))
        return None, query
    except requests.exceptions.RequestException as e:
        # catastrophic error. bail.
        current_app.logger.error('Solr exception. Terminated request.')
        current_app.logger.error(e)
        return None, query
