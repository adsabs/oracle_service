
import re

from flask import current_app
import requests
import flask
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import or_, and_, desc, func, distinct
from sqlalchemy.sql import exists
from sqlalchemy.dialects.postgresql import insert

from oraclesrv.models import DocMatch, ConfidenceLookup

re_doi = re.compile(r'\bdoi:\s*(10\.[\d\.]{2,9}/\S+\w)', re.IGNORECASE)
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
            # if there is a pubnote, attempt to extract doi from it
            if doc.get('pubnote', None):
                match = re_doi.search(' '.join(doc['pubnote']))
                if match:
                    doc['doi_pubnote'] = match.group(1)
            if fl == 'bibcode':
                result.append(doc['bibcode'])
            else:
                result.append(doc)
        return result, response.status_code
    return result, response.status_code

def get_solr_data_chunk(bibcodes, fl='bibcode, identifier'):
    """
    need to grab bibcodes from solr in chunk because of query length to send to solr

    :param bibcodes:
    :param fl:
    :return:
    """
    url = current_app.config['ORACLE_SERVICE_SOLRQUERY_URL']
    headers = {'Authorization': 'Bearer ' + current_app.config['ORACLE_SERVICE_ADSWS_API_TOKEN']}
    params = {
        'wt': 'json',
        'start': 0,
        'sort': 'date desc, bibcode desc',
        'fl': fl,
    }

    docs = []
    max_bibcodes = current_app.config['ORACLE_SERVICE_MAX_RECORDS_SOLRQUERY']
    for i in range(0, len(bibcodes), max_bibcodes):
        slice_bibcodes = slice(i, i + max_bibcodes, 1)

        params['q'] = 'identifier:("' + '" OR "'.join(bibcodes[slice_bibcodes]) + '")'
        params['rows'] = len(bibcodes[slice_bibcodes])

        try:
            response = requests.get(
                url=url,
                params=params,
                headers=headers,
                timeout=60
            )

            if (response.status_code != 200):
                return None, response.status_code

            # make sure solr found the documents
            from_solr = response.json()
            if (from_solr.get('response')):
                num_rows = len(from_solr['response']['docs'])
                if num_rows > 0:
                    docs += from_solr['response']['docs']

        except requests.exceptions.RequestException as e:
            return None, e

    return docs, 200

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
def get_solr_data_match(abstract, title, doctype, match_doctype, extra_filter):
    """

    :param abstract:
    :param title:
    :param doctype:
    :param match_doctype:
    :param extra_filter:
    :return:
    """
    rows = 10
    # if there is an abstract, query solr on abstract, otherwise query on title
    if len(abstract) > 0  and not abstract.lower().startswith('not available'):
        # there is a limit on number of characters that can be send
        abstract = abstract[:2500]
        query = 'topn({rows}, similar("{abstract}", input abstract, {number_matched_terms_abstract}, 1, 1)) doctype:({match_doctype}) {extra_filter}'.format(rows=rows,
                          abstract=abstract, number_matched_terms_abstract=max(1, int(abstract.count(' ') * 0.3)), match_doctype=match_doctype, extra_filter=extra_filter)
    elif len(title) > 0:
        title = re_punctuation.sub('', re_hyphenated_word.sub('', title)).strip()
        query = 'topn({rows}, similar("{title}", input title, {number_matched_terms_title}, 1, 1)) doctype:({match_doctype}) {extra_filter}'.format(rows=rows,
                          title=title, number_matched_terms_title=max(1, int(title.count(' ') * 0.9)), match_doctype=match_doctype, extra_filter=extra_filter)
    else:
        return [], '', 200

    try:
        query = query.strip()
        result, status_code = get_solr_data(rows, query, fl='bibcode,abstract,title,author_norm,year,doctype,doi,identifier,property,pubnote')
    except requests.exceptions.HTTPError as e:
        current_app.logger.error(e)
        result = {'error from solr':'%d: %s'%(e.response.status_code, e.response.reason)}
        status_code = e.response.status_code

    return result, query, status_code

def get_solr_data_match_doi(doi, doctype, match_doctype):
    """

    :param doi:
    :param doctype:
    :param matched_doctype:
    :return:
    """
    try:
        # remove REFEREED for now, but return the property in the results to used it in scoring
        # also remove the doctype, if there is a doi, just query doi for now
        # query = 'doi:"{doi}" doctype:({doctype}) property:REFEREED'.format(doi=doi, doctype=doctype)
        query = 'identifier:({doi}) doctype:({match_doctype})'.format(doi=doi, match_doctype=match_doctype)
        result, status_code = get_solr_data(rows=1, query=query, fl='bibcode,doi,abstract,title,author_norm,year,doctype,doi,identifier,property,pubnote')
    except requests.exceptions.HTTPError as e:
        current_app.logger.error(e)
        result = {'error from solr':'%d: %s'%(e.response.status_code, e.response.reason)}
        status_code = e.response.status_code

    return result, query, status_code

def get_solr_data_match_pubnote(doi, doctype, match_doctype):
    """
    query pubnote for doi

    :param doi:
    :param doctype:
    :param matched_doctype:
    :return:
    """
    try:
        query = 'pubnote:({doi}) doctype:({match_doctype})'.format(doi=doi, match_doctype=match_doctype)
        result, status_code = get_solr_data(rows=1, query=query, fl='bibcode,doi,abstract,title,author_norm,year,doctype,doi,identifier,property,pubnote')
    except requests.exceptions.HTTPError as e:
        current_app.logger.error(e)
        result = {'error from solr':'%d: %s'%(e.response.status_code, e.response.reason)}
        status_code = e.response.status_code

    return result, query, status_code

def get_solr_data_match_doctype_case(author, year, doctype, match_doctype):
    """
    
    :param author: 
    :param year: 
    :param doctype: 
    :param matched_doctype: 
    :return: 
    """
    if 'thesis' in match_doctype:
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
        query = 'author_norm:"{author}" year:{year_filter} doctype:({match_doctype})'.format(author=author_norm, year_filter=year_filter, match_doctype=match_doctype)
        result, status_code = get_solr_data(rows=3, query=query, fl='bibcode,doi,abstract,title,author_norm,year,doctype,doi,identifier,pubnote')
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
            try:
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
                session.rollback()
                current_app.logger.error('SQLAlchemy: ' + str(e))
                return False, 'SQLAlchemy: ' + str(e)
    except SQLAlchemyError as e:
        current_app.logger.error('SQLAlchemy: ' + str(e))
        return False, 'SQLAlchemy: ' + str(e)

def get_a_record(source_bibcode, matched_bibcode):
    """

    :param source_bibcode:
    :param matched_bibcode:
    :return:
    """
    try:
        with current_app.session_scope() as session:
            docmatch = DocMatch(source_bibcode, matched_bibcode, confidence=-1)
            row = session.query(DocMatch).filter(or_(DocMatch.eprint_bibcode == docmatch.eprint_bibcode,
                                                     DocMatch.pub_bibcode == docmatch.pub_bibcode)).order_by(desc(DocMatch.confidence)).first()
            if row:
                current_app.logger.debug("Fetched a record for matched bibcodes = (%s, %s)."  % (source_bibcode, matched_bibcode))
                return row.toJSON()

        current_app.logger.debug("No record for matched bibcodes = (%s, %s)."  % (source_bibcode, matched_bibcode))
        return {}
    except SQLAlchemyError as e:
        current_app.logger.error('SQLAlchemy: ' + str(e))
        return {}

def get_a_matched_record(source_bibcode):
    """

    :param source_bibcode:
    :return:
    """
    try:
        with current_app.session_scope() as session:
            docmatch = DocMatch(source_bibcode='0000arXiv.........Z', matched_bibcode=source_bibcode, confidence=-1)
            row = session.query(DocMatch).filter(DocMatch.pub_bibcode == docmatch.pub_bibcode).order_by(desc(DocMatch.confidence)).first()
            if row:
                current_app.logger.debug("Fetched a record with matched bibcode only = %s."  % (source_bibcode))
                return row.toJSON()

        current_app.logger.debug("No record with a matched bibcode = %s."  % (source_bibcode))
        return {}
    except SQLAlchemyError as e:
        current_app.logger.error('SQLAlchemy: ' + str(e))
        return {}

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
                try:
                    session.execute(on_conflict_stmt)
                    current_app.logger.info('updated db with new data successfully')
                    return True, 'updated db with new data successfully'
                except SQLAlchemyError as e:
                    session.rollback()
                    current_app.logger.error('SQLAlchemy: ' + str(e))
                    return False, 'SQLAlchemy: ' + str(e)
        except SQLAlchemyError as e:
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
            try:
                count = 0
                for doc in docmatches.docmatch_records:
                    # convert to DocMatch so that eprint and pub bibcodes can be identified
                    docmatch = DocMatch(doc.source_bibcode, doc.matched_bibcode, doc.confidence)
                    count += session.query(DocMatch).filter(and_(DocMatch.eprint_bibcode == docmatch.eprint_bibcode,
                                                                 DocMatch.pub_bibcode == docmatch.pub_bibcode,
                                                                 DocMatch.confidence == docmatch.confidence)).delete(synchronize_session=False)
                session.commit()
                return True, count, 'removed ' + str(count) + ' records of ' + str(len(docmatches.docmatch_records)) + ' requested'
            except SQLAlchemyError as e:
                session.rollback()
                current_app.logger.error('SQLAlchemy: ' + str(e))
                return False, 'SQLAlchemy: ' + str(e)
    except SQLAlchemyError as e:
        current_app.logger.error('SQLAlchemy: ' + str(e))
        return False, 'SQLAlchemy: ' + str(e)

def query_docmatch(params):
    """

    :param params:
    :return:
    """
    try:
        with current_app.session_scope() as session:
            # setup subquery to extract the published records with the highest confidence
            highest_confidence = session.query(DocMatch.pub_bibcode, func.max(DocMatch.confidence).label('confidence')) \
                .order_by(DocMatch.pub_bibcode.asc()).group_by(DocMatch.pub_bibcode).distinct().subquery()
            # get full records with the highest confidence
            result = session.query(DocMatch.eprint_bibcode, DocMatch.pub_bibcode, DocMatch.confidence, DocMatch.date) \
                .filter(and_(DocMatch.pub_bibcode == highest_confidence.c.pub_bibcode,
                             DocMatch.confidence == highest_confidence.c.confidence,
                             DocMatch.date >= params['date_cutoff'].strftime("%Y-%m-%d %H:%M:%S"))) \
                .order_by(DocMatch.pub_bibcode.asc()) \
                .offset(params['start']).limit(params['rows']).all()
            if len(result) > 0:
                # remove the last field, which is datetime, it is not needed to be returned
                result = [r[0:3] for r in result]
            return result, 200
        return [], 200
    except SQLAlchemyError as e:
        current_app.logger.error('SQLAlchemy: ' + str(e))
        return [], 404

def query_source_score():
    """

    :return:
    """
    try:
        with current_app.session_scope() as session:
            rows = session.query(ConfidenceLookup).all()
            results = []
            for row in rows:
                results.append(row.toJSON())
            return results, 200
    except SQLAlchemyError as e:
        current_app.logger.error('SQLAlchemy: ' + str(e))
        return [], 404

def lookup_confidence(source):
    """

    :param source:
    :return:
    """
    try:
        with current_app.session_scope() as session:
            row = session.query(ConfidenceLookup.confidence).filter(ConfidenceLookup.source == source).first()
            if row:
                return row[0], 200
            return 0, 400
    except SQLAlchemyError as e:
        current_app.logger.error('SQLAlchemy: ' + str(e))
        return 0, 404

def delete_tmp_matches():
    """
    if both tmp bibcode and canonical bibcode has been matched against an eprint bibcode
    then remove tmp matches

    :return:
    """
    try:
        with current_app.session_scope() as session:
            try:
                # get the list of multiples
                multiples = session.query(DocMatch.eprint_bibcode, DocMatch.confidence, func.count('*').label('count')) \
                    .group_by(DocMatch.eprint_bibcode, DocMatch.confidence).having(func.count('*') > 1).subquery()
                # now remove multiple rows that is a tmp bibcode
                count = session.query(DocMatch).filter(
                    and_(DocMatch.eprint_bibcode == multiples.c.eprint_bibcode,
                         DocMatch.confidence == multiples.c.confidence,
                         or_(DocMatch.pub_bibcode.like('%.tmp.%'), DocMatch.pub_bibcode.like('%.tmpL.%')))) \
                    .delete(synchronize_session=False)
                session.commit()
                return count, ''
            except SQLAlchemyError as e:
                session.rollback()
                current_app.logger.error('SQLAlchemy: ' + str(e))
                return -1, 'SQLAlchemy: ' + str(e)
    except SQLAlchemyError as e:
        current_app.logger.error('SQLAlchemy: ' + str(e))
        return False, 'SQLAlchemy: ' + str(e)

def replace_tmp_with_canonical():
    """
    if there are distinct tmp matches (no canonical matches), grab the bibcode and identifier from solr
    and update the tmp bibcode with their canonical bibcode counterpart

    :return:
    """
    try:
        marked_delete, _ = lookup_confidence('incorrect')
        with current_app.session_scope() as session:
            try:
                # get the tmp bibcodes that are not marked as deleted
                rows = session.query(DocMatch).distinct(DocMatch.eprint_bibcode, DocMatch.pub_bibcode, DocMatch.confidence) \
                    .filter(and_(or_(DocMatch.pub_bibcode.like('%.tmp.%'), DocMatch.pub_bibcode.like('%.tmpL.%')),
                                 DocMatch.confidence != -1)).all()

                # get bibcode and identifier list for these tmp bibcodes
                bibcodes = []
                for row in rows:
                    bibcodes.append(row.pub_bibcode)

                count = 0
                if bibcodes:
                    # go through the lists, if pub_bibcode is different from bibcode, then update pub_bibcode only if
                    # the update does not cause duplicate records, in that case do  not update the pub_bibcode, instead
                    # set confidence to -1 signaling that this is a delete
                    docs, status = get_solr_data_chunk(bibcodes)
                    if docs:
                        for row in rows:
                            for doc in docs:
                                if row.pub_bibcode in doc.get('identifier', []):
                                    canonical = doc.get('bibcode')
                                    if row.pub_bibcode != canonical:
                                        # is the match with canonical in db already
                                        with session.no_autoflush:
                                            mark_as_delete = len(session.query(DocMatch) \
                                                                 .filter(and_(DocMatch.eprint_bibcode == row.eprint_bibcode,
                                                                              DocMatch.pub_bibcode == canonical)).all()) > 0
                                        if mark_as_delete:
                                            row.confidence = marked_delete
                                        else:
                                            row.pub_bibcode = doc.get('bibcode')
                                        count += 1
                                    docs.remove(doc)
                                    break

                    session.commit()
                return count, ''
            except SQLAlchemyError as e:
                session.rollback()
                current_app.logger.error('SQLAlchemy: ' + str(e))
                return -1, 'SQLAlchemy: ' + str(e)
    except SQLAlchemyError as e:
        current_app.logger.error('SQLAlchemy: ' + str(e))
        return False, 'SQLAlchemy: ' + str(e)

def delete_multi_matches():
    """

    :return:
    """
    try:
        with current_app.session_scope() as session:
            try:
                # get the list of multiples of eprint_bibcode
                multiples = session.query(DocMatch.eprint_bibcode, func.max(DocMatch.confidence).label('confidence')) \
                    .group_by(DocMatch.eprint_bibcode) \
                    .having(func.count(distinct(DocMatch.confidence)) > 1).subquery()
                # get all the matches with confidence smaller then the multiples to remove them
                count_eprint = session.query(DocMatch).filter(
                    and_(DocMatch.eprint_bibcode == multiples.c.eprint_bibcode,
                         DocMatch.confidence < multiples.c.confidence)) \
                    .delete(synchronize_session=False)

                # now get the list of multiples of pub_bibcode
                multiples = session.query(DocMatch.pub_bibcode, func.max(DocMatch.confidence).label('confidence')) \
                    .group_by(DocMatch.pub_bibcode) \
                    .having(func.count(distinct(DocMatch.confidence)) > 1).subquery()
                # get all the matches with confidence smaller then the multiples to remove them
                count_pub = session.query(DocMatch).filter(
                    and_(DocMatch.pub_bibcode == multiples.c.pub_bibcode,
                         DocMatch.confidence < multiples.c.confidence)) \
                    .delete(synchronize_session=False)

                session.commit()
                return count_eprint + count_pub, ''
            except SQLAlchemyError as e:
                session.rollback()
                current_app.logger.error('SQLAlchemy: ' + str(e))
                return -1, 'SQLAlchemy: ' + str(e)
    except SQLAlchemyError as e:
        current_app.logger.error('SQLAlchemy: ' + str(e))
        return False, 'SQLAlchemy: ' + str(e)

def clean_db():
    """

    :return:
    """
    # init
    counts = {
        'count_deleted_tmp': -1,
        'count_updated_canonical': -1,
        'count_deleted_multi_matches': -1,
    }
    status_updated_canonical = status_deleted_multi_matches = ''

    # delete tmp matches
    count_deleted_tmp, status_deleted_tmp = delete_tmp_matches()
    if count_deleted_tmp >= 0:
        counts['count_deleted_tmp'] = count_deleted_tmp
        # now update any tmp bibcode matches with their canonical counterpart, if available in solr
        count_updated_canonical, status_updated_canonical = replace_tmp_with_canonical()
        if count_updated_canonical >= 0:
            counts['count_updated_canonical'] = count_updated_canonical
            # finally remove the lower confidence matches of the multiple matches
            count_deleted_multi_matches, status_deleted_multi_matches = delete_multi_matches()
            if count_deleted_multi_matches >= 0:
                counts['count_deleted_multi_matches'] = count_deleted_multi_matches
                return counts, ''
    return counts, '%s %s %s'%(status_deleted_tmp, status_updated_canonical, status_deleted_multi_matches)

def get_tmp_bibcodes():
    """

    :return:
    """
    try:
        with current_app.session_scope() as session:
            result = session.query(DocMatch.eprint_bibcode, DocMatch.pub_bibcode, DocMatch.confidence, DocMatch.date) \
                .filter(or_(DocMatch.pub_bibcode.like('%.tmp.%'), DocMatch.pub_bibcode.like('%.tmpL.%'))) \
                .order_by(DocMatch.date.asc()).all()
            if len(result) > 0:
                # remove the last field, which is datetime, it is not needed to be returned
                result = [r[0:3] for r in result]
            return result, 200
        return [], 200
    except SQLAlchemyError as e:
        current_app.logger.error('SQLAlchemy: ' + str(e))
        return None, 'SQLAlchemy: ' + str(e)

def get_muti_matches():
    """

    :return:
    """
    try:
        with current_app.session_scope() as session:
            # get the list of multi matched eprints
            multi_eprints = session.query(DocMatch.eprint_bibcode) \
                .group_by(DocMatch.eprint_bibcode).having(func.count('*') > 1).subquery()
            # get the list of multi matched pubs
            multi_pubs = session.query(DocMatch.pub_bibcode) \
                .group_by(DocMatch.pub_bibcode).having(func.count('*') > 1).subquery()
            # now get full records
            result = session.query(DocMatch.eprint_bibcode, DocMatch.pub_bibcode, DocMatch.confidence) \
                .filter(or_(DocMatch.eprint_bibcode == multi_eprints.c.eprint_bibcode, DocMatch.pub_bibcode == multi_pubs.c.pub_bibcode)) \
                .group_by(DocMatch.eprint_bibcode, DocMatch.pub_bibcode, DocMatch.confidence) \
                .order_by(DocMatch.eprint_bibcode.asc(), DocMatch.pub_bibcode.asc()).all()
            return result, 200
        return [], 200
    except SQLAlchemyError as e:
        current_app.logger.error('SQLAlchemy: ' + str(e))
        return None, 'SQLAlchemy: ' + str(e)
