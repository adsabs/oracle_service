
# encoding=utf8
PYTHONIOENCODING="UTF-8"

from flask import current_app, request, Blueprint, Response
from flask_discoverer import advertise

import json
import time

from adsmsg import DocMatchRecordList
from google.protobuf.json_format import Parse, ParseError

from oraclesrv.utils import get_solr_data_recommend, add_records, del_records
from oraclesrv.keras_model import create_keras_model
from oraclesrv.doc_matching import DocMatching, get_requests_params


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

def get_user_info_from_adsws(parameter):
    """

    :param parameter:
    :return:
    """
    if parameter:
        try:
            current_app.logger.info('getting user info from adsws for %s' % (parameter))
            url = current_app.config['ORACLE_SERVICE_ACCOUNT_INFO_URL'] + '/' + parameter
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

def get_the_reader(request, payload):
    """
    for getting the reader, first see if user has provided as part of payload,
    if not, per Roman, try to get it in the order: Authorization > session for adsws

    :param request:
    :param payload:
    :return:
    """
    if payload:
        reader = get_requests_params(payload, 'reader')
        if reader:
            return reader

    user_token = request.headers.get('Authorization', '')[7:].strip()
    if user_token:
        account = get_user_info_from_adsws(user_token)
        if account:
            return account['hashed_client_id'][:16]

    session = request.cookies.get('session', None)
    if session:
        account = get_user_info_from_adsws(session)
        if account:
            return account['hashed_client_id'][:16]

    return None

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
    # try extracting `function` from payload now
    if the_function is None:
        the_function = verify_the_function(get_requests_params(payload, 'function'))
    # try extracting `reader` from payload or request it from adsws
    if the_reader is None:
        the_reader = get_the_reader(request, payload)
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

    the_function = verify_the_function(get_requests_params(payload, 'function'))
    the_reader = get_the_reader(request, payload)
    if the_reader is None:
        return return_response(results={'error': 'unable to obtain reader id'}, status_code=400)

    return read_history(payload, the_function, the_reader)

@advertise(scopes=[], rate_limit=[1000, 3600 * 24])
@bp.route('/docmatch', methods=['POST'])
def docmatch():
    """

    :return:
    """
    current_app.logger.debug('received request to find a match for a document')

    try:
        payload = request.get_json(force=True)  # post data in json
    except:
        payload = dict(request.form)  # post data in form encoding

    if not payload:
        return return_response(results={'error': 'no information received'}, status_code=400)

    start_time = time.time()
    results, status_code = DocMatching(payload).process()

    current_app.logger.debug('docmatching results = %s'%json.dumps(results))
    current_app.logger.debug('docmatching status_code = %d'%status_code)

    current_app.logger.debug("Matched doc in {duration} ms".format(duration=(time.time() - start_time) * 1000))
    return return_response(results, status_code)

@advertise(scopes=['ads:oracle-service'], rate_limit=[1000, 3600 * 24])
@bp.route('/add', methods=['PUT'])
def add():
    """
    """
    try:
        payload = request.get_json(force=True)  # post data in json
    except:
        payload = dict(request.form)  # post data in form encoding

    if not payload:
        return return_response({'error': 'no data received'}, 400)

    if len(payload) == 0:
        return return_response({'error': 'no records received to update db'}, 400)

    current_app.logger.info('received request to populate db with %d records' % (len(payload)))

    try:
        data = Parse(json.dumps({"status": 2, "docmatch_records": payload}), DocMatchRecordList())
    except ParseError as e:
        return return_response({'error': 'unable to extract data from protobuf structure -- %s' % (e)}, 400)

    status, text = add_records(data)
    if status == True:
        current_app.logger.info('completed request to populate db with %d records' % (len(payload)))
        return return_response({'status': text}, 200)
    current_app.logger.info('failed to populate db with %d records' % (len(payload)))
    return return_response({'error': text}, 400)

@advertise(scopes=['ads:oracle-service'], rate_limit=[1000, 3600 * 24])
@bp.route('/delete', methods=['DELETE'])
def delete():
    """
    """
    try:
        payload = request.get_json(force=True)  # post data in json
    except:
        payload = dict(request.form)  # post data in form encoding

    if not payload:
        return return_response({'error': 'no information received'}, 400)

    if len(payload) == 0:
        return return_response({'error': 'no records received to delete from db'}, 400)

    current_app.logger.info('received request to delete from db %d bibcodes' % (len(payload)))

    try:
        data = Parse(json.dumps({"status": 2, "docmatch_records": payload}), DocMatchRecordList())
    except ParseError as e:
        return return_response({'error': 'unable to extract data from protobuf structure -- %s' % (e)}, 400)

    status, count, text = del_records(data)
    if status == True:
        current_app.logger.info('completed request to delete from db total of %d records' % (count))
        return return_response({'status': text}, 200)
    current_app.logger.info('failed to delete from db %d bibcodes' % (len(payload)))
    return return_response({'error': text}, 400)


@advertise(scopes=['ads:oracle-service'], rate_limit=[1000, 3600 * 24])
@bp.route('/pickle_docmatch', methods=['PUT'])
def pickle_docmatch():
    """
    endpoint to be called locally only whenever the models needs be changed

    :return:
    """
    # to save a new model
    create_keras_model()

    return return_response({'OK': 'objects saved'}, 200)


