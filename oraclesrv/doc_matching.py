from flask import current_app

from oraclesrv.utils import get_solr_data_match, get_solr_data_match_doi, get_solr_data_match_thesis
from oraclesrv.score import clean_data, get_matches, encode_author, format_author, get_doi_match
from oraclesrv.utils import add_a_record

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


class DocMatching(object):

    def __init__(self, payload):
        """

        :param payload:
        """
        # read required params
        self.abstract = get_requests_params(payload, 'abstract')
        self.title = get_requests_params(payload, 'title')
        self.author = get_requests_params(payload, 'author')
        self.year = get_requests_params(payload, 'year')
        self.doctype = get_requests_params(payload, 'doctype')
        self.doi = get_requests_params(payload, 'doi', default_type=list)
        self.mustmatch = get_requests_params(payload, 'mustmatch')
        self.match_doctype = get_requests_params(payload, 'match_doctype', default_type=list)
        self.source_bibcode = get_requests_params(payload, 'bibcode')

    def create_and_return_response(self, match, query, comment=None):
        """

        :param match:
        :param query:
        :param comment:
        :return:
        """
        result = {'query': query}
        if comment:
            result.update({'comment': comment.strip()})
        if len(match) > 0:
            result.update({'match': match})
        else:
            result.update({'no match': 'no document was found in solr matching the request.'})
        return result, 200

    def process_thesis(self, comment):
        """
        
        :param comment: 
        :return: 
        """
        results, query, solr_status_code = get_solr_data_match_thesis(self.author, self.year, '"%s"' % '" OR "'.join(self.match_doctype))
        # if any records from solr
        if isinstance(results, list) and len(results) > 0:
            match = get_matches(self.source_bibcode, self.abstract, self.title, self.author, self.year, None, results)
            if not match:
                current_app.logger.debug('No result from solr for thesis.')
                comment += ' No result from solr for thesis.'
        else:
            match = ''
            current_app.logger.debug('No matches for thesis.')
            comment += ' No matches for thesis.'
        return self.create_and_return_response(match=match, query=query, comment=comment)

    def query_doi(self, comment):
        """
        
        :param comment: 
        :return: 
        """
        doi_filter = '"%s"'%'" OR "'.join(self.doi)
        current_app.logger.debug('with parameter: doi=({doi})'.format(doi='"%s"'%'" OR "'.join(self.doi)))
        results, query, solr_status_code = get_solr_data_match_doi(doi_filter, self.match_doctype)
        # if any records from solr
        # compute the score, if score is 0 doi was wrong, so continue on to query using similar
        if isinstance(results, list) and len(results) > 0:
            match = get_doi_match(self.source_bibcode, self.abstract, self.title, self.author, self.year, self.doi, results)
            if match:
                return self.create_and_return_response(match, query), ''
            else:
                current_app.logger.debug('No matches with DOI %s, trying Abstract.' % self.doi)
                comment += ' No matches with DOI %s, trying Abstract.' % self.doi
        else:
            current_app.logger.debug('No result from solr with DOI %s.' % self.doi)
            comment += ' No result from solr with DOI %s.' % self.doi
        
        return None, comment

    def query_abstract_or_title(self, comment):
        """

        :param comment:
        :return:
        """
        # query solr using similar with abstract
        results, query, solr_status_code = get_solr_data_match(self.abstract, self.title, self.match_doctype, self.extra_filter)
        if solr_status_code != 200:
            return self.create_and_return_response([], query, 'status code: %d'%solr_status_code)

        # if solr was not able to find any matches with abstract, attempt it again with title
        # no result from solr
        if len(results) == 0:
            current_app.logger.debug('No result from solr with Abstract, trying Title.')
            comment += ' No result from solr with Abstract, trying Title.'
            results, query, solr_status_code = get_solr_data_match('', self.title, self.match_doctype, self.extra_filter)
            if solr_status_code != 200:
                return self.create_and_return_response([], query, 'status code: %d' % solr_status_code)
        # got records from solr, see if we can get a match
        else:
            match = get_matches(self.source_bibcode, self.abstract, self.title, self.author, self.year, None, results)
            if len(match) > 0:
                return self.create_and_return_response(match, query, comment)
            # otherwise if no match with abstract, and we think we should have this in solr
            # and thus have a much, try with title, this is the case when abstract has changed
            # so drastically between the arXiv version and the publisher version
            current_app.logger.debug('No matches with Abstract, trying Title.')
            comment += ' No matches with Abstract, trying Title.'
            results, query, solr_status_code = get_solr_data_match('', self.title, self.match_doctype, self.extra_filter)
            if solr_status_code != 200:
                return self.create_and_return_response([], query, 'status code: %d' % solr_status_code)

        # no result from title either
        if len(results) == 0 :
            current_app.logger.debug('No result from solr with Title.')
            comment += ' No result from solr with Title.'
            return self.create_and_return_response(match='', query=query, comment=comment)

        match = get_matches(self.source_bibcode, self.abstract, self.title, self.author, self.year, None, results)
        return self.create_and_return_response(match, query, comment)

    def save_match(self, result):
        """

        :param result:
        :return:
        """
        if result and result[0].get('match', []):
            the_match = result[0]['match']
            # if there is only one record, and the confidence is high enough to be considered a match
            if len(the_match) == 1 and the_match[0]['matched'] == 1:
                add_a_record({'source_bibcode': the_match[0]['source_bibcode'],
                              'matched_bibcode': the_match[0]['matched_bibcode'],
                              'confidence': the_match[0]['confidence']},
                             source_bibcode_doctype=self.doctype)

    def process(self):
        """

        :return:
        """
        # need either abstract or title, with author and year and doctype
        if not ((self.abstract or self.title) and self.author and self.year and self.doctype):
            current_app.logger.error('missing required parameter(s)')
            results = {'error': 'the following parameters are required: `abstract` or `title`, `author`, `year`,  and `doctype`'}
            status_code = 400
            return results, status_code

        self.author = format_author(encode_author(self.author))
        comment = ''

        # if matching doctype is specified use that, otherwise go with the default
        if not self.match_doctype:
            self.match_doctype = current_app.config['ORACLE_SERVICE_MATCH_DOCTYPE'].get(self.doctype, None)
            if not self.match_doctype:
                current_app.logger.error('invalid doctype %s'%self.doctype)
                results = {'error': 'invalid doctype %s' % self.doctype}
                status_code = 400
                return results, status_code
        else:
            if isinstance(self.match_doctype, list):
                comment = 'Matching doctype `%s`.'%';'.join(self.match_doctype)
            else:
                comment = 'Matching doctype `%s`.'%(self.match_doctype)

            is_thesis = any(input in self.match_doctype for input in current_app.config['ORACLE_SERVICE_MATCH_DOCTYPE'].get('thesis'))
            if is_thesis:
                result = self.process_thesis(comment)
                if result:
                    if result[0].get('match', None):
                        self.save_match(result)
                        return result
                    # if no doi, return that nothing was found, but if there is a doi, try it
                    elif not self.doi:
                        return result

        self.abstract = clean_data(self.abstract)
        self.title = clean_data(self.title)
        # remove REFEREED for now
        #self.extra_filter = 'property:REFEREED' if 'eprint' not in self.match_doctype else ''
        self.extra_filter = ''
        self.match_doctype = ' OR '.join(self.match_doctype)

        # if doi is available try query on doi first
        if self.doi:
            result, comment = self.query_doi(comment)
            if result:
                self.save_match(result)
                return result

        current_app.logger.debug('with parameters: abstract={abstract}, title={title}, author={author}, year={year}, doctype={doctype}'.format(
            abstract=self.abstract[:100]+'...', title=self.title, author=self.author, year=self.year, doctype=self.doctype))

        result = self.query_abstract_or_title(comment)
        self.save_match(result)
        return result
