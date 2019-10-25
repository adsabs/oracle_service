# -*- coding: utf-8 -*-

from flask import current_app, request, Blueprint, Response
from flask_discoverer import advertise
from requests.exceptions import HTTPError, ConnectionError

import json
import urlparse

from oraclesrv.utils import get_solr_data


bp = Blueprint('oracle_service', __name__)

def return_response(results, status_code):
    """

    :param results:
    :param status_code:
    :return:
    """
    r = Response(response=json.dumps(results), status=status_code)
    r.headers['content-type'] = 'application/json'
    return r

def get_user_info_from_adsws(session):
    """

    :param session:
    :return:
    """
    if session:
        try:
            current_app.logger.info('getting user info from adsws for %s' % (session))
            url = current_app.config['ORACLE_SERVICE_ACCOUNT_INFO_URL'] + '/' + session
            headers = {'Authorization': 'Bearer ' + current_app.config['ORACLE_SERVICE_ADSWS_API_TOKEN']}
            r = current_app.client.get(url=url, headers=headers)
            if r.status_code == 200:
                current_app.logger.info('got results from adsws=%s' % (r.json()))
                return r.json()
            current_app.logger.error('got status code from adsws=%s with message %s' % (r.status_code, r.json()))
        except Exception as e:
            current_app.logger.error('adsws exception: %s'%e)
            raise
    return None

def get_requests_params(payload, param, default_value):
    """

    :param payload:
    :param param:
    :param default_value:
    :return:
    """
    if payload and param in payload:
        if type(payload[param]) is list:
            return payload[param][0]
        return payload[param]
    return default_value

@advertise(scopes=[], rate_limit=[1000, 3600 * 24])
@bp.route('/readhist', defaults={'reader': None}, methods=['POST'])
@bp.route('/readhist', defaults={'reader': None}, methods=['GET'])
@bp.route('/readhist/<reader>', methods=['GET'])
def readhist(reader):
    """

    :return:
    """
    if request.method == 'GET':
        the_reader = reader
        payload = request.args.to_dict(flat=False)
        # try extracting reader from passed in parameters
        if the_reader is None:
            the_reader = get_requests_params(payload, 'reader', None)
    else: # request.method == 'POST':
        try:
            payload = request.get_json(force=True)  # post data in json
        except:
            payload = dict(request.form)  # post data in form encoding

        if not payload:
            return return_response(results={'error': 'no information received'}, status_code=400)

        the_reader = get_requests_params(payload, 'reader', None)

    # if no reader, see if there is a session and reader can be extracted accordingly
    if the_reader is None:
        session = request.cookies.get('session', None)
        if not session:
            return return_response(results={'error': 'neither reader found in payload (parameter name is `reader`) nor session information received'}, status_code=400)
        account = get_user_info_from_adsws(session)
        if not account:
            return return_response(results={'error': 'unable to obtain reader id'}, status_code=400)
        client_id = account['hashed_client_id']
        the_reader = client_id[:16]

    current_app.logger.debug('received POST request with reader={the_reader} to find similiar articles'.format(the_reader=the_reader))

    # read any optional params
    sort = get_requests_params(payload, 'sort', 'entry_date')
    num_docs = get_requests_params(payload, 'num_docs', 5)
    cutoff_days = get_requests_params(payload, 'cutoff_days', 5)
    top_n_reads = get_requests_params(payload, 'top_n_reads', 10)

    current_app.logger.debug('with parameters: num_docs={num_docs}, sort={sort}, cutoff_days={cutoff_days}, and top_n_reads={top_n_reads}'.format(
                                               num_docs=num_docs, sort=sort, cutoff_days=cutoff_days, top_n_reads=top_n_reads))

    bibcodes, query, solr_status_code = get_solr_data(the_reader, num_docs, sort, cutoff_days, top_n_reads)
    if bibcodes:
        return return_response(results={'bibcodes':','.join(bibcodes), 'query':query}, status_code=200)
    return return_response(results={'error': 'no result from solr with status code=%d'%solr_status_code, 'query': query}, status_code=404)
