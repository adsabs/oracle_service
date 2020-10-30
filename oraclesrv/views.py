import sys
reload(sys)
sys.setdefaultencoding('utf-8')

from flask import current_app, request, Blueprint, Response
from flask_discoverer import advertise

import json

from oraclesrv.utils import get_solr_data_recommend, get_solr_data_match, get_solr_data_match_doi, get_solr_data_match_thesis
from oraclesrv.score import clean_data, score_match, encode_author, format_author, score_match_doi


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

def create_and_return_response(match, query, comment=None):
    """

    :param match:
    :param query:
    :param comment:
    :return:
    """
    result = {'query':query}
    if comment:
        result.update({'comment': comment.strip()})
    if len(match) > 0:
        result.update({'match':match})
    else:
        result.update({'no match': 'no document was found in solr matching the request.'})
    return return_response(results=result, status_code=200)


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

def get_requests_params(payload, param, default_value=None, default_type=str):
    """

    :param payload:
    :param param:
    :param default_value:
    :param default_type:
    :return:
    """
    if payload and param in payload:
        if type(payload[param]) is list:
            if default_type == list:
                return payload[param]
            return payload[param][0]
        return payload[param]
    return default_value

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
@bp.route('/matchdoc', methods=['POST'])
def matchdoc():
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

    # read required params
    abstract = get_requests_params(payload, 'abstract')
    title = get_requests_params(payload, 'title')
    author = get_requests_params(payload, 'author')
    year = get_requests_params(payload, 'year')
    doctype = get_requests_params(payload, 'doctype')
    doi = get_requests_params(payload, 'doi')
    mustmatch = get_requests_params(payload, 'mustmatch')
    match_doctype = get_requests_params(payload, 'match_doctype', default_type=list)

    if not (abstract and title and author and year and doctype):
        current_app.logger.error('missing required parameter(s)')
        return return_response(results={'error': 'all five parameters are required: `abstract`, `title`, `author`, `year`,  and `doctype`'}, status_code=400)

    author = format_author(encode_author(author))
    comment = ''

    # if matching doctype is specified use that, otherwise go with the default
    if not match_doctype:
        match_doctype = current_app.config['ORACLE_SERVICE_MATCH_DOCTYPE'].get(doctype, None)
        if not match_doctype:
            current_app.logger.error('invalid doctype %s'%doctype)
            return return_response(results={'error': 'invalid doctype %s'%doctype}, status_code=400)
    else:
        comment = 'Matching doctype `%s`.'%';'.join(match_doctype)
        is_thesis = any(input in match_doctype for input in current_app.config['ORACLE_SERVICE_MATCH_DOCTYPE'].get('thesis'))
        if is_thesis:
            results, query, solr_status_code = get_solr_data_match_thesis(author, year, ' OR '.join(match_doctype))
            # if any records from solr
            if isinstance(results, list) and len(results) > 0:
                match = score_match(abstract, title, author, year, results)
                if not match:
                    current_app.logger.debug('No result from solr for thesis.')
                    comment = ' No result from solr for thesis.'
            else:
                match = ''
                current_app.logger.debug('No matches for thesis.')
                comment = ' No matches for thesis.'
            return create_and_return_response(match=match, query=query, comment=comment)

    abstract = clean_data(abstract)
    title = clean_data(title)
    extra_filter = 'property:REFEREED' if 'eprint' not in match_doctype else ''
    match_doctype = ' OR '.join(match_doctype)

    # if doi is available try query on doi first
    if doi:
        current_app.logger.debug('with parameter: doi={doi}'.format(doi=doi))
        results, query, solr_status_code = get_solr_data_match_doi(doi, doctype)
        # if any records from solr
        # compute the score, if score is 0 doi was wrong, so continue on to query using similar
        if isinstance(results, list) and len(results) > 0:
            match = score_match_doi(doi, abstract, title, author, year, results)
            if match:
                return create_and_return_response(match, query)
            else:
                current_app.logger.debug('No matches with DOI, trying Abstract.')
                comment = ' No matches with DOI, trying Abstract.'
        else:
            current_app.logger.debug('No result from solr with DOI.')
            comment = ' No result from solr with DOI.'

    current_app.logger.debug('with parameters: abstract={abstract}, title={title}, author={author}, year={year}, doctype={doctype}'.format(
                                               abstract=abstract[:100]+'...', title=title, author=author, year=year, doctype=doctype))

    # query solr using similar with abstract
    results, query, solr_status_code = get_solr_data_match(abstract, title, match_doctype, extra_filter)

    # if solr was not able to find any matches with abstract, attempt it again with title
    if solr_status_code == 200:
        # no result from solr
        if len(results) == 0:
            current_app.logger.debug('No result from solr with Abstract, trying Title.')
            comment += ' No result from solr with Abstract, trying Title.'
            results, query, solr_status_code = get_solr_data_match('', title, match_doctype, extra_filter)
        # got records from solr, see if we can get a match
        else:
            match = score_match(abstract, title, author, year, results)
            if len(match) > 0:
                confidence = match[0].get('confidence', 0)
                # if we have a match, or if we dont have a match, but it is not a must, return
                if confidence != 0 or not mustmatch:
                    return create_and_return_response(match, query, comment)
            # otherwise if no match with abstract, and we think we should have this in solr
            # and thus have a much, try with title, this is the case when abstract has changed
            # so drastically between the arXiv version and the publisher version
            current_app.logger.debug('No matches with Abstract, trying Title.')
            comment += ' No matches with Abstract, trying Title.'
            results, query, solr_status_code = get_solr_data_match('', title, match_doctype, extra_filter)

    # no result from title either
    if len(results) == 0 and solr_status_code == 200:
        current_app.logger.debug('No result from solr with Title.')
        comment += ' No result from solr with Title.'
        return create_and_return_response(match='', query=query, comment=comment)

    match = score_match(abstract, title, author, year, results)
    return create_and_return_response(match, query, comment)

