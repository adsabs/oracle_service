from flask import current_app

from oraclesrv.utils import get_solr_data_match, get_solr_data_match_doi, get_solr_data_match_thesis
from oraclesrv.score import clean_data, get_matches, encode_author, format_author, get_doi_match

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
        self.doi = get_requests_params(payload, 'doi')
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

        results, query, solr_status_code = get_solr_data_match_thesis(self.author, self.year, ' OR '.join(self.match_doctype))
        # if any records from solr
        if isinstance(results, list) and len(results) > 0:
            match = get_matches(self.source_bibcode, self.abstract, self.title, self.author, self.year, results)
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
        current_app.logger.debug('with parameter: doi={doi}'.format(doi=self.doi))
        results, query, solr_status_code = get_solr_data_match_doi(self.doi, self.match_doctype)
        # if any records from solr
        # compute the score, if score is 0 doi was wrong, so continue on to query using similar
        if isinstance(results, list) and len(results) > 0:
            match = get_doi_match(self.source_bibcode, self.abstract, self.title, self.author, self.year, results)
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

        # if solr was not able to find any matches with abstract, attempt it again with title
        if solr_status_code == 200:
            # no result from solr
            if len(results) == 0:
                current_app.logger.debug('No result from solr with Abstract, trying Title.')
                comment += ' No result from solr with Abstract, trying Title.'
                results, query, solr_status_code = get_solr_data_match('', self.title, self.match_doctype, self.extra_filter)
            # got records from solr, see if we can get a match
            else:
                match = get_matches(self.source_bibcode, self.abstract, self.title, self.author, self.year, results)
                if len(match) > 0:
                    return self.create_and_return_response(match, query, comment)
                # otherwise if no match with abstract, and we think we should have this in solr
                # and thus have a much, try with title, this is the case when abstract has changed
                # so drastically between the arXiv version and the publisher version
                current_app.logger.debug('No matches with Abstract, trying Title.')
                comment += ' No matches with Abstract, trying Title.'
                results, query, solr_status_code = get_solr_data_match('', self.title, self.match_doctype, self.extra_filter)

        # no result from title either
        if len(results) == 0 and solr_status_code == 200:
            current_app.logger.debug('No result from solr with Title.')
            comment += ' No result from solr with Title.'
            return self.create_and_return_response(match='', query=query, comment=comment)

        match = get_matches(self.source_bibcode, self.abstract, self.title, self.author, self.year, results)
        return self.create_and_return_response(match, query, comment)

    def process(self):
        """

        :return:
        """
        if not (self.abstract and self.title and self.author and self.year and self.doctype):
            current_app.logger.error('missing required parameter(s)')
            results = {'error': 'all five parameters are required: `abstract`, `title`, `author`, `year`,  and `doctype`'}
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
            comment = 'Matching doctype `%s`.'%';'.join(self.match_doctype)
            is_thesis = any(input in self.match_doctype for input in current_app.config['ORACLE_SERVICE_MATCH_DOCTYPE'].get('thesis'))
            if is_thesis:
                return self.process_thesis(comment)

        self.abstract = clean_data(self.abstract)
        self.title = clean_data(self.title)
        self.extra_filter = 'property:REFEREED' if 'eprint' not in self.match_doctype else ''
        self.match_doctype = ' OR '.join(self.match_doctype)

        # if doi is available try query on doi first
        if self.doi:
            result, comment = self.query_doi(comment)
            if result:
                return result

        current_app.logger.debug('with parameters: abstract={abstract}, title={title}, author={author}, year={year}, doctype={doctype}'.format(
            abstract=self.abstract[:100]+'...', title=self.title, author=self.author, year=self.year, doctype=self.doctype))

        return self.query_abstract_or_title(comment)