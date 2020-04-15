# -*- coding: utf-8 -*-

from flask import current_app, request, Blueprint, Response
from flask_discoverer import advertise

import json

from oraclesrv.utils import get_solr_data_recommend, get_solr_data_match
from oraclesrv.score import clean_data, score_match, encode_author, format_author


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

def get_user_info_from_adsws(endpoint):
    """

    :param endpoint:
    :return:
    """
    if endpoint:
        try:
            current_app.logger.info('getting user info from adsws for %s' % (endpoint))
            url = current_app.config['ORACLE_SERVICE_ACCOUNT_INFO_URL'] + '/' + endpoint
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

def get_the_reader(session, user_token, user_id):
    """
    if reader is not provided, per Roman, try to get it in the order Authorization > X-Adsws-Uid > session

    :param session: 
    :param user_token: 
    :param user_id: 
    :return: 
    """
    if user_token:
        account = get_user_info_from_adsws(user_token)
        if account:
            client_id = account['hashed_client_id']
            return client_id[:16]
    if user_id:
        account = get_user_info_from_adsws(user_token)
        if account:
            client_id = account['hashed_client_id']
            return client_id[:16]
    if session:
        account = get_user_info_from_adsws(session)
        if account:
            client_id = account['hashed_client_id']
            return client_id[:16]
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

def read_history(payload, function, reader):
    """

    :param payload:
    :param function:
    :param reader:
    :return:
    """
    # read any optional params
    sort = get_requests_params(payload, 'sort', 'entry_date')
    num_docs = get_requests_params(payload, 'num_docs', 5)
    cutoff_days = get_requests_params(payload, 'cutoff_days', 5)
    top_n_reads = get_requests_params(payload, 'top_n_reads', 10)

    current_app.logger.debug('with parameters: function={the_function}, reader={the_reader}, num_docs={num_docs}, sort={sort}, cutoff_days={cutoff_days}, and top_n_reads={top_n_reads}'.format(
                                               the_function=function, the_reader=reader, num_docs=num_docs, sort=sort, cutoff_days=cutoff_days, top_n_reads=top_n_reads))

    bibcodes, query, solr_status_code = get_solr_data_recommend(function, reader, num_docs, sort, cutoff_days, top_n_reads)
    if bibcodes:
        return return_response(results={'bibcodes':','.join(bibcodes), 'query':query}, status_code=200)
    return return_response(results={'error': 'no result from solr with status code=%d'%solr_status_code, 'query': query}, status_code=404)

@advertise(scopes=[], rate_limit=[1000, 3600 * 24])
@bp.route('/readhist/<function>/<reader>', methods=['GET'])
def read_history_get(function, reader):
    """

    :param function:
    :param reader:
    :return:
    """
    current_app.logger.debug('received GET request to read history')

    the_function = function
    the_reader = reader
    payload = request.args.to_dict(flat=False)
    # try extracting reader and/or function from passed in parameters
    if the_function is None:
        the_function = verify_the_function(get_requests_params(payload, 'function', None))
    if the_reader is None:
        the_reader = get_requests_params(payload, 'reader', None)
        if the_reader is None:
            session = request.cookies.get('session', None)
            user_token = request.headers.get('Authorization', '')[7:].strip()
            user_id = request.headers.get('X-Adsws-Uid', None)
            if session is None and user_token is None and user_id is None:
                return return_response(results={'error': 'neither reader found in payload (parameter name is `reader`) nor header and session information received'}, status_code=400)
            the_reader = get_the_reader(session, user_token, user_id)
    if the_reader is None:
        return return_response(results={'error': 'unable to obtain reader id'}, status_code=400)

    return read_history(payload, the_function, the_reader)

@advertise(scopes=[], rate_limit=[1000, 3600 * 24])
@bp.route('/readhist', methods=['POST'])
def read_history_post():
    """

    :return:
    """
    current_app.logger.debug('received POST request to read history')

    try:
        payload = request.get_json(force=True)  # post data in json
    except:
        payload = dict(request.form)  # post data in form encoding

    if not payload:
        current_app.logger.error("no payload")
        return return_response(results={'error': 'no information received'}, status_code=400)

    the_function = verify_the_function(get_requests_params(payload, 'function', None))
    the_reader = get_requests_params(payload, 'reader', None)
    if the_reader is None:
        session = request.cookies.get('session', None)
        user_token = request.headers.get('Authorization', None)
        user_id = request.headers.get('X-Adsws-Uid', None)
        if session is None and user_token is None and user_id is None:
            return return_response(results={'error': 'neither reader found in payload (parameter name is `reader`) nor header and session information received'}, status_code=400)
        the_reader = get_the_reader(session, user_token, user_id)
    if the_reader is None:
        return return_response(results={'error': 'unable to obtain reader id'}, status_code=400)

    return read_history(payload, the_function, the_reader)

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
    year = get_requests_params(payload, 'year', None)
    doctype = get_requests_params(payload, 'doctype', None)

    if not (abstract and title and author and year and doctype):
        current_app.logger.error('missing required parameter(s)')
        return return_response(results={'error': 'all five parameters are required: `abstract`, `title`, `author`, `year`,  and `doctype`'}, status_code=400)

    current_app.logger.debug('with parameters: abstract={abstract}, title={title}, author={author}, year={year}, doctype={doctype}'.format(
                                               abstract=abstract[:100]+'...', title=title, author=author, year=year, doctype=doctype))

    abstract = clean_data(abstract)
    title = clean_data(title)
    author = format_author(encode_author(author))
    results, query, solr_status_code = get_solr_data_match(abstract, title)
    if solr_status_code == 200:
        match = score_match(abstract, title, author, year, doctype, results)
        if len(match) > 0:
            return return_response(results={'match':match, 'query':query}, status_code=200)
        else:
            return return_response(results={'no match': 'no document was found in solr matching the request', 'query': query}, status_code=200)
    return return_response(results=results, status_code=404)
