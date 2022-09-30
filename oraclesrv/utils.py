
import re

from flask import current_app
import requests
import flask
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_, and_, desc, func
from sqlalchemy.sql import exists
from sqlalchemy.dialects.postgresql import insert

from oraclesrv.models import DocMatch


def get_solr_data(rows, query, fl):
    """

    :param rows:
    :param query:
    :return:
    """
    result = []

    if current_app.config['REQUESTS_CONNECTION_POOL_ENABLED']:
        response = current_app.client.get(
            url=current_app.config['ORACLE_SERVICE_SOLRQUERY_URL'],
            headers={'Authorization': 'Bearer ' + current_app.config['ORACLE_SERVICE_ADSWS_API_TOKEN']},
            params={'fl': fl, 'rows': rows, 'q': query},
            timeout=current_app.config.get('API_TIMEOUT', 60)
        )
    else:
        new_headers = {}
        if flask.has_request_context():
            # Propagate key information from the original request
            new_headers[u'X-Original-Uri'] = flask.request.headers.get(u'X-Original-Uri', u'-')
            new_headers[u'X-Original-Forwarded-For'] = flask.request.headers.get(u'X-Original-Forwarded-For', u'-')
            new_headers[u'X-Forwarded-For'] = flask.request.headers.get(u'X-Forwarded-For', u'-')
            new_headers[u'X-Amzn-Trace-Id'] = flask.request.headers.get(u'X-Amzn-Trace-Id', '-')
        new_headers[u'Authorization'] = 'Bearer ' + current_app.config['ORACLE_SERVICE_ADSWS_API_TOKEN'] 
        response = requests.get(
            url=current_app.config['ORACLE_SERVICE_SOLRQUERY_URL'],
            headers=new_headers,
            params={'fl': fl, 'rows': rows, 'q': query},
            timeout=current_app.config.get('API_TIMEOUT', 60)
        )

    response.raise_for_status()

    from_solr = response.json()
    num_docs = from_solr['response'].get('numFound', 0)
    if num_docs > 0:
        current_app.logger.debug('Got {num_docs} records from solr.'.format(num_docs=num_docs))
        for doc in from_solr['response']['docs']:
            if fl == 'bibcode':
                result.append(doc['bibcode'])
            else:
                result.append(doc)
        return result, response.status_code
    return result, response.status_code

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


re_hyphenated_word = re.compile(r'\w+\-\w+\s*')
re_punctuation = re.compile(r'[^\w\s]')
def get_solr_data_match(abstract, title, doctype, extra_filter):
    """

    :param abstract:
    :param title:
    :param doctype:
    :param extra_filter:
    :return:
    """
    rows = 10
    # if there is an abstract, query solr on abstract, otherwise query on title
    if len(abstract) > 0  and not abstract.lower().startswith('not available'):
        # there is a limit on number of characters that can be send
        abstract = abstract[:2500]
        query = 'topn({rows}, similar("{abstract}", input abstract, {number_matched_terms_abstract}, 1, 1)) doctype:({doctype}) {extra_filter}'.format(rows=rows,
                          abstract=abstract, number_matched_terms_abstract=max(1, int(abstract.count(' ') * 0.3)), doctype=doctype, extra_filter=extra_filter)
    elif len(title) > 0:
        title = re_punctuation.sub('', re_hyphenated_word.sub('', title)).strip()
        query = 'topn({rows}, similar("{title}", input title, {number_matched_terms_title}, 1, 1)) doctype:({doctype}) {extra_filter}'.format(rows=rows,
                          title=title, number_matched_terms_title=max(1, int(title.count(' ') * 0.9)), doctype=doctype, extra_filter=extra_filter)
    else:
        return [], '', 200

    try:
        query = query.strip()
        result, status_code = get_solr_data(rows, query, fl='bibcode,abstract,title,author_norm,year,doctype,doi,identifier,property')
    except requests.exceptions.HTTPError as e:
        current_app.logger.error(e)
        result = {'error from solr':'%d: %s'%(e.response.status_code, e.response.reason)}
        status_code = e.response.status_code

    return result, query, status_code

def get_solr_data_match_doi(doi, doctype):
    """

    :param doi:
    :param doctype:
    :return:
    """
    try:
        # remove REFEREED for now, but return the property in the results to used it in scoring
        # also remove the doctype, if there is a doi, just query doi for now
        # query = 'doi:"{doi}" doctype:({doctype}) property:REFEREED'.format(doi=doi, doctype=doctype)
        query = 'identifier:({doi})'.format(doi=doi)
        result, status_code = get_solr_data(rows=1, query=query, fl='bibcode,doi,abstract,title,author_norm,year,doctype,doi,identifier,property')
    except requests.exceptions.HTTPError as e:
        current_app.logger.error(e)
        result = {'error from solr':'%d: %s'%(e.response.status_code, e.response.reason)}
        status_code = e.response.status_code

    return result, query, status_code

def get_solr_data_match_doctype_case(author, year, doctype):
    """

    :param author:
    :param year:
    :return:
    """
    if 'thesis' in doctype:
        year_delta = current_app.config['ORACLE_SERVICE_THESIS_YEAR_DELTA']
        year = int(year)
        year_filter = '[{year_start} TO {year_end}]'.format(year_start=year-year_delta, year_end=year+year_delta)
    else:
        year_delta = current_app.config['ORACLE_SERVICE_GENERAL_YEAR_DELTA']
        year = int(year)
        year_filter = '[{year_start} TO {year_end}]'.format(year_start=year-year_delta, year_end=year+year_delta)

    # note that this could be thesis with one author, or erratum or bookreview with many authors
    # query only on the first author
    try:
        # if multiple authors, need only the first author
        if ';' in author:
            author = author.split(';')[0]
        author = author.split(',')
        # if only last name
        if len(author) == 1:
            author_norm = '{}'.format(author[0].strip()).lower()
        else:
            author_norm = '{}, {}'.format(author[0].strip(), author[1].strip()[0]).lower()
        query = 'author_norm:"{author}" year:{year_filter} doctype:({doctype})'.format(author=author_norm, year_filter=year_filter, doctype=doctype)
        result, status_code = get_solr_data(rows=3, query=query, fl='bibcode,doi,abstract,title,author_norm,year,doctype,doi,identifier')
    except requests.exceptions.HTTPError as e:
        current_app.logger.error(e)
        result = {'error from solr': '%d: %s' % (e.response.status_code, e.response.reason)}
        status_code = e.response.status_code

    return result, query, status_code

def add_a_record(protobuf_docmatch, source_bibcode_doctype=None):
    """

    :param protobuf_docmatch:
    :param source_bibcode_doctype:
    :return:
    """
    try:
        with current_app.session_scope() as session:
            docmatch = DocMatch(protobuf_docmatch['source_bibcode'], protobuf_docmatch['matched_bibcode'], protobuf_docmatch['confidence'], None, source_bibcode_doctype)
            found = session.query(exists().where(and_(DocMatch.eprint_bibcode == docmatch.eprint_bibcode,
                                                      DocMatch.pub_bibcode == docmatch.pub_bibcode,
                                                      DocMatch.confidence == docmatch.confidence))).scalar()
            if found:
                return True, 'record already in db'
            session.add(docmatch)
            session.commit()
        current_app.logger.debug('updated db with a new record successfully')
        return True, 'updated db with a new record successfully'
    except SQLAlchemyError as e:
        current_app.logger.error('SQLAlchemy: ' + str(e))
        return False, 'SQLAlchemy: ' + str(e)

def get_a_record(source_bibcode, matched_bibcode):
    """

    :param source_bibcode:
    :param matched_bibcode:
    :return:
    """
    with current_app.session_scope() as session:
        docmatch = DocMatch(source_bibcode, matched_bibcode, confidence=-1)
        row = session.query(DocMatch).filter(or_(DocMatch.eprint_bibcode == docmatch.eprint_bibcode,
                                                 DocMatch.pub_bibcode == docmatch.pub_bibcode)).order_by(desc(DocMatch.confidence)).first()
        if row:
            current_app.logger.debug("Fetched a record for matched bibcodes = (%s, %s)."  % (source_bibcode, matched_bibcode))
            return row.toJSON()

    current_app.logger.debug("No record for matched bibcodes = (%s, %s)."  % (source_bibcode, matched_bibcode))
    return None

def add_records(protobuf_docmatches):
    """
    upserts records into db

    :param docmatches:
    :return: success boolean, plus a status text for retuning error message, if any, to the calling program
    """
    rows = []
    for protobuf_docmatch in protobuf_docmatches.docmatch_records:
        # convert to DocMatch so that eprint and pub bibcodes can be identified
        docmatch = DocMatch(protobuf_docmatch.source_bibcode, protobuf_docmatch.matched_bibcode, protobuf_docmatch.confidence)
        rows.append({"eprint_bibcode":docmatch.eprint_bibcode,
                     "pub_bibcode": docmatch.pub_bibcode,
                     "confidence": docmatch.confidence})

    if len(rows) > 0:
        table = DocMatch.__table__
        stmt = insert(table).values(rows)

        # get list of fields making up primary key
        primary_keys = [c.name for c in list(table.primary_key.columns)]
        # define dict of non-primary keys for updating
        update_dict = {c.name: c for c in stmt.excluded if not c.primary_key}

        on_conflict_stmt = stmt.on_conflict_do_update(index_elements=primary_keys, set_=update_dict)

        try:
            with current_app.session_scope() as session:
                session.execute(on_conflict_stmt)
            current_app.logger.info('updated db with new data successfully')
            return True, 'updated db with new data successfully'
        except SQLAlchemyError as e:
            session.rollback()
            current_app.logger.error('SQLAlchemy: ' + str(e))
            return False, 'SQLAlchemy: ' + str(e)
    return False, 'unable to add records to the database'

def del_records(docmatches):
    """
    delete records from db

    :param docmatches:
    :return:
    """
    try:
        with current_app.session_scope() as session:
            count = 0
            for doc in docmatches.docmatch_records:
                # convert to DocMatch so that eprint and pub bibcodes can be identified
                docmatch = DocMatch(doc.source_bibcode, doc.matched_bibcode, doc.confidence)
                count += session.query(DocMatch).filter(and_(DocMatch.eprint_bibcode == docmatch.eprint_bibcode,
                                                             DocMatch.pub_bibcode == docmatch.pub_bibcode,
                                                             DocMatch.confidence == docmatch.confidence)).delete(synchronize_session=False)
            session.commit()
    except SQLAlchemyError as e:
        session.rollback()
        current_app.logger.error('SQLAlchemy: ' + str(e))
        return False, 'SQLAlchemy: ' + str(e)
    return True, count, 'removed ' + str(count) + ' records of ' + str(len(docmatches.docmatch_records)) + ' requested'

def query_docmatch(params):
    """

    :param params:
    :return:
    """
    try:

        with current_app.session_scope() as session:
            # setup subquery to extract the published records with the highest confidence
            highest_confidence = session.query(DocMatch.pub_bibcode, func.max(DocMatch.confidence).label('confidence')) \
                .group_by(DocMatch.pub_bibcode).distinct().offset(params['start']).limit(params['rows']).subquery()
            # get full records with the highest confidence
            result = session.query(DocMatch.eprint_bibcode, DocMatch.pub_bibcode, DocMatch.confidence, DocMatch.date) \
                .filter(and_(DocMatch.pub_bibcode == highest_confidence.c.pub_bibcode,
                             DocMatch.confidence == highest_confidence.c.confidence,
                             DocMatch.date >= params['date_cutoff'])).all()

            if len(result) > 0:
                # remove the last field, which is datetime, is not needed to be returned
                result = [r[0:3] for r in result]
            return result, 200
        return [], 200
    except SQLAlchemyError as e:
        current_app.logger.error('SQLAlchemy: ' + str(e))
        return [], 404
