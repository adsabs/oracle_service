# -*- coding: utf-8 -*-

from flask import current_app, request, Blueprint, Response
from flask_discoverer import advertise
from requests.exceptions import HTTPError, ConnectionError

import json
import urlparse

from oraclesrv.utils import get_solr_data_recommend, get_solr_data_match, score_match


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

def verify_the_function(the_function):
    """
    verifies that the requested function is valid, if not returns the default `similar`

    :param the_function:
    :return:
    """
    if the_function in ["similar", "trending", "reviews", "useful"]:
        return the_function
    return 'similar'

@advertise(scopes=[], rate_limit=[1000, 3600 * 24])
@bp.route('/readhist', defaults={'function': None, 'reader': None}, methods=['POST'])
@bp.route('/readhist', defaults={'function': None, 'reader': None}, methods=['GET'])
@bp.route('/readhist/<function>/<reader>', methods=['GET'])
def readhist(function, reader):
    """

    :return:
    """
    current_app.logger.debug('received request with to find similar articles')

    if request.method == 'GET':
        the_reader = reader
        the_function = function
        payload = request.args.to_dict(flat=False)
        # try extracting reader and/or function from passed in parameters
        if the_reader is None:
            the_reader = get_requests_params(payload, 'reader', None)
        if the_function is None:
            the_function = verify_the_function(get_requests_params(payload, 'function', None))
    else: # request.method == 'POST':
        try:
            payload = request.get_json(force=True)  # post data in json
        except:
            payload = dict(request.form)  # post data in form encoding

        if not payload:
            return return_response(results={'error': 'no information received'}, status_code=400)

        the_reader = get_requests_params(payload, 'reader', None)
        the_function = verify_the_function(get_requests_params(payload, 'function', None))

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

    # read any optional params
    sort = get_requests_params(payload, 'sort', 'entry_date')
    num_docs = get_requests_params(payload, 'num_docs', 5)
    cutoff_days = get_requests_params(payload, 'cutoff_days', 5)
    top_n_reads = get_requests_params(payload, 'top_n_reads', 10)

    current_app.logger.debug('with parameters: function={the_function}, reader={the_reader}, num_docs={num_docs}, sort={sort}, cutoff_days={cutoff_days}, and top_n_reads={top_n_reads}'.format(
                                               the_function=the_function, the_reader=the_reader, num_docs=num_docs, sort=sort, cutoff_days=cutoff_days, top_n_reads=top_n_reads))

    bibcodes, query, solr_status_code = get_solr_data_recommend(the_function, the_reader, num_docs, sort, cutoff_days, top_n_reads)
    if bibcodes:
        return return_response(results={'bibcodes':','.join(bibcodes), 'query':query}, status_code=200)
    return return_response(results={'error': 'no result from solr with status code=%d'%solr_status_code, 'query': query}, status_code=404)

@advertise(scopes=[], rate_limit=[1000, 3600 * 24])
@bp.route('/matchdoc', methods=['POST'])
def matchdoc():
    """

    :return:
    """
    current_app.logger.debug('received request with to find match for an article')

    try:
        payload = request.get_json(force=True)  # post data in json
    except:
        payload = dict(request.form)  # post data in form encoding

    if not payload:
        return return_response(results={'error': 'no information received'}, status_code=400)

    # read required params
    abstract = get_requests_params(payload, 'abstract', None)
    title = get_requests_params(payload, 'title', None)
    author = get_requests_params(payload, 'author', None)

    if not (abstract and title and author):
        current_app.logger.error('missing required parameter(s)')
        return return_response(results={'error': 'all three parameters are required: `abstract`, `title`, and `author`'}, status_code=400)

    current_app.logger.debug('with parameters: abstract={abstract}, title={title}, author={author}'.format(
                                               abstract=abstract[:100]+'...', title=title, author=author))

    abstract =abstract.encode('ascii', 'ignore').decode('ascii')
    title = title.encode('ascii', 'ignore').decode('ascii')
    matched_docs, query, solr_status_code = get_solr_data_match(abstract, title)
    if matched_docs:
        match = score_match(abstract, title, author, matched_docs)
        if len(match) > 0:
            return return_response(results={'match':match, 'query':query}, status_code=200)
        else:
            return return_response(results={'no match': 'no document was found in solr matching the request', 'query': query}, status_code=200)
    return return_response(results={'error': 'no result from solr with status code=%d'%solr_status_code, 'query': query}, status_code=404)
