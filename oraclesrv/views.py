
# encoding=utf8
PYTHONIOENCODING="UTF-8"

from flask import current_app, request, Blueprint, Response
from flask_discoverer import advertise

import json
import time

from adsmutils import get_date
from datetime import timedelta

from adsmsg import DocMatchRecordList
from google.protobuf.json_format import Parse, ParseError

from oraclesrv.utils import get_solr_data_recommend, add_records, del_records, query_docmatch, query_source_score, lookup_confidence
from oraclesrv.keras_model import create_keras_model
from oraclesrv.doc_matching import DocMatching, get_requests_params

import oraclesrv.utils as utils

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

def docmatch(save=True):
    """

    :param save:
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
    results, status_code = DocMatching(payload, save=save).process()

    current_app.logger.debug('docmatching results = %s'%json.dumps(results))
    current_app.logger.debug('docmatching status_code = %d'%status_code)

    current_app.logger.debug("Matched doc in {duration} ms".format(duration=(time.time() - start_time) * 1000))
    return return_response(results, status_code)

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
def docmatch_post():
    """

    :return:
    """
    return docmatch(save=False)

@advertise(scopes=['ads:oracle-service'], rate_limit=[1000, 3600 * 24])
@bp.route('/docmatch_add', methods=['POST'])
def docmatch_add_post():
    """

    :return:
    """
    return docmatch()

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
@bp.route('/keras_model', methods=['PUT'])
def keras_model():
    """
    endpoint to be called locally only whenever the models needs be changed

    :return:
    """
    # to save a new model
    create_keras_model()

    return return_response({'OK': 'objects saved'}, 200)

@advertise(scopes=[], rate_limit=[1000, 3600 * 24])
@bp.route('/query', methods=['POST'])
def query():
    """

    :return:
    """
    current_app.logger.debug('received request to query database')

    try:
        payload = request.get_json(force=True)  # post data in json
    except:
        payload = dict(request.form)  # post data in form encoding

    # initialize params in payload if missing
    # rows: number of records to return
    max_rows = current_app.config['ORACLE_SERVICE_QUERY_MAX_RECORDS']
    if 'rows' not in payload:
        payload['rows'] = max_rows
    elif payload['rows'] > max_rows:
        payload['rows'] = max_rows
    # start: offset to table's rows
    if 'start' not in payload:
        payload['start'] = 0
    # number of days from today to return records
    if 'days' not in payload:
        payload['date_cutoff'] = get_date('1972/01/01 00:00:00')
    else:
        payload['date_cutoff'] = get_date() - timedelta(days=int(payload['days']))

    start_time = time.time()
    results, status_code = query_docmatch(payload)

    current_app.logger.debug('docmatching results = %s'%json.dumps(results))
    current_app.logger.debug('docmatching status_code = %d'%status_code)

    current_app.logger.debug("Matched doc in {duration} ms".format(duration=(time.time() - start_time) * 1000))

    # before returning convert the date to a string
    # otherwise gets JSON serializable error
    payload['date_cutoff'] = str(payload['date_cutoff'])
    return return_response({'params':payload, 'results':results}, status_code)

@advertise(scopes=[], rate_limit=[1000, 3600 * 24])
@bp.route('/source_score', methods=['GET'])
def source_score():
    """

    :return:
    """
    current_app.logger.debug('received request to get the list of source and score')

    results, status_code = query_source_score()

    current_app.logger.debug('source_score results = %s'%json.dumps(results))
    current_app.logger.debug('source_score status_code = %d'%status_code)

    return return_response({'results':results}, status_code)

@advertise(scopes=[], rate_limit=[1000, 3600 * 24])
@bp.route('/confidence/<source>', methods=['GET'])
def confidence(source):
    """

    :return:
    """
    current_app.logger.debug('received request to get confidence score for source name %s'%source)

    score, status_code = lookup_confidence(source)

    current_app.logger.debug('confidence value = %s'%score)
    current_app.logger.debug('confidence status_code = %d'%status_code)

    return return_response({'confidence':score}, status_code)

@advertise(scopes=['ads:oracle-service'], rate_limit=[1000, 3600 * 24])
@bp.route('/cleanup', methods=['GET'])
def cleanup():
    """
    cleans up the db, removing tmp bibcodes and lower confidence of multi matches

    :return:
    """
    counts, status = utils.clean_db()
    if all(count >= 0 for count in counts.values()):
        if counts.get('count_deleted_tmp', -1) > 0:
            message = 'Successfully removed %d matches having tmp bibcode while matches with canonical bibcode exists. '%counts['count_deleted_tmp']
        else:
            message = 'No duplicate (tmp and canoncial) records found. '
        if counts.get('count_updated_canonical', -1) > 0:
            message += 'Successfully replaced %d tmp matches with its canonical bibcode. ' % counts['count_updated_canonical']
        else:
            message += 'No tmp bibcode was updated with the canonical bibcode. '
        if counts.get('count_deleted_multi_matches') > 0:
            message += 'Successfully removed %d matches having multiple matches, kept the match with highest confidence.' % counts['count_deleted_multi_matches']
        else:
            message += 'No multiple match records found.'

        return return_response({'details': message}, 200)
    else:
        return return_response({'details':'unable to perform the cleanup, ERROR: %s'%status}, 400)

@advertise(scopes=['ads:oracle-service'], rate_limit=[1000, 3600 * 24])
@bp.route('/list_tmps', methods=['GET'])
def list_tmps():
    """
    list tmp bibcodes in the db

    :return:
    """
    results, status_code = utils.get_tmp_bibcodes()

    current_app.logger.debug('tmp bibcodes results = %s'%json.dumps(results))
    current_app.logger.debug('tmp bibcodes status_code = %d'%status_code)

    return return_response({'count':len(results), 'results':results}, status_code)


@advertise(scopes=['ads:oracle-service'], rate_limit=[1000, 3600 * 24])
@bp.route('/list_multis', methods=['GET'])
def list_multis():
    """
    list multi matched bibcodes from the db

    :return:
    """
    results, status_code = utils.get_muti_matches()

    current_app.logger.debug('multi matches results = %s'%json.dumps(results))
    current_app.logger.debug('multi matches status_code = %d'%status_code)

    return return_response({'count':len(results), 'results':results}, status_code)
