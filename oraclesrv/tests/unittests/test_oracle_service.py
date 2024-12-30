# -*- coding: utf-8 -*-
import sys
import os
PROJECT_HOME = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(PROJECT_HOME)

import unittest
import json
import mock
import requests
from requests.exceptions import HTTPError
from requests.models import Response

import oraclesrv.app as app
from oraclesrv.tests.unittests.base import TestCaseDatabase
from oraclesrv.score import get_matches, to_unicode, get_db_match, count_matching_authors, get_year_score, \
    encode_author, get_doi_match, get_author_score
from oraclesrv.doc_matching import DocMatching
from oraclesrv.utils import get_solr_data_recommend, get_solr_data_match, get_solr_data_match_doi, get_solr_data_match_pubnote, \
    get_solr_data_match_doctype_case, get_solr_data_chunk, get_solr_data


class test_oracle(TestCaseDatabase):

    @mock.patch('oraclesrv.utils.query_eprint_bibstem')
    def test_get_matches(self, mock_query_eprint_bibstem):
        """
        Test get_matches function of the score module
        """
        # mock the eprint_bibstem patterns
        mock_query_eprint_bibstem.return_value = (
            [
                {'name': 'arXiv', 'pattern': r'^(\d\d\d\d(?:arXiv|acc\.phys|adap\.org|alg\.geom|ao\.sci|astro\.ph|atom\.ph|bayes\.an|chao\.dyn|chem\.ph|cmp\.lg|comp\.gas|cond\.mat|cs\.|dg\.ga|funct\.an|gr\.qc|hep\.ex|hep\.lat|hep\.ph|hep\.th|math\.|math\.ph|mtrl\.th|nlin\.|nucl\.ex|nucl\.th|patt\.sol|physics\.|plasm\.ph|q\.alg|q\.bio|quant\.ph|solv\.int|supr\.con))'},
                {'name': 'Earth Science', 'pattern': r'^(\d\d\d\d(?:EaArX|esoar))'},
            ],
            200
        )

        source_bibcode = '2022arXiv220606316S'
        abstract = 'In the present paper, discussion of the canonical quantization of a weakly nonideal Bose gas at zero temperature along the lines of the famous Bogolyubov approach is continued. Contrary to the previous paper on this subject, here the two-body interaction potential is considered in the general form. It is shown that consideration of the first nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach, without any modification of the resulting effective Hamiltonian.'
        title = 'Nonlinear corrections in the quantization of a weakly nonideal Bose gas   at zero temperature. II. The general case'
        author = 'Smolyakov, Mikhail N.'
        year = 2022
        doi = ['10.1016/j.chaos.2021.111505']
        doctype = 'eprint'

        matched_docs = [{'bibcode': '2021CSF...15311505S',
                         'abstract': 'In the present paper, quantization of a weakly nonideal Bose gas at zero temperature along the lines of the well-known Bogolyubov approach is performed. The analysis presented in this paper is based, in addition to the steps of the original Bogolyubov approach, on the use of nonoscillation modes (which are also solutions of the linearized Heisenberg equation) for recovering the canonical commutation relations in the linear approximation, as well as on the calculation of the first nonlinear correction to the solution of the linearized Heisenberg equation which satisfies the canonical commutation relations at the next order. It is shown that, at least in the case of free quasi-particles, consideration of the nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach.',
                         'author_norm': ['Smolyakov, M'],
                         'doctype': 'article',
                         'doi': ['10.1016/j.chaos.2021.111505'],
                         'identifier': ['10.1016/j.chaos.2021.111505', 'arXiv:2103.12030', '2021CSF...15311505S', '2021arXiv210312030S'],
                         'title': ['Nonlinear corrections in the quantization of a weakly nonideal Bose gas at zero temperature'],
                         'year': '2021',
                         'property': ['ARTICLE','EPRINT_OPENACCESS','ESOURCE','OPENACCESS','REFEREED']}]

        # abstract, no doi
        match = get_matches(source_bibcode, doctype, abstract, title, author, year, None, matched_docs)
        self.assertEqual(len(match), 1)
        self.assertDictEqual(match[0], {'source_bibcode': '2022arXiv220606316S',
                                        'matched_bibcode': '2021CSF...15311505S',
                                        'confidence': 0.7936664,
                                        'matched': 1,
                                        'scores': {'abstract': 0.76, 'title': 0.98, 'author': 1, 'year': 1}})

        # no abstract, no doi
        match = get_matches(source_bibcode, doctype, '', title, author, year, None, matched_docs)
        self.assertEqual(len(match), 1)
        self.assertDictEqual(match[0], {'source_bibcode': '2022arXiv220606316S',
                                        'matched_bibcode': '2021CSF...15311505S',
                                        'confidence': 0.9986353,
                                        'matched': 1,
                                        'scores': {'abstract': None, 'title': 0.98, 'author': 1, 'year': 1}})

        # abstract, doi
        match = get_matches(source_bibcode, doctype, abstract, title, author, year, doi, matched_docs)
        self.assertEqual(len(match), 1)
        self.assertDictEqual(match[0], {'source_bibcode': '2022arXiv220606316S',
                                        'matched_bibcode': '2021CSF...15311505S',
                                        'confidence': 0.9946523,
                                        'matched': 1,
                                        'scores': {'abstract': 0.76, 'title': 0.98, 'author': 1, 'year': 1, 'doi': 1}})

        # no abstract, doi
        match = get_matches(source_bibcode, doctype, '', title, author, year, doi, matched_docs)
        self.assertEqual(len(match), 1)
        self.assertDictEqual(match[0], {'source_bibcode': '2022arXiv220606316S',
                                        'matched_bibcode': '2021CSF...15311505S',
                                        'confidence': 0.9899692,
                                        'matched': 1,
                                        'scores': {'abstract': None, 'title': 0.98, 'author': 1, 'year': 1, 'doi': 1}})

    @mock.patch('oraclesrv.utils.query_eprint_bibstem')
    def test_get_matches_multi_hits(self, mock_query_eprint_bibstem):
        """
        Test get_matches function of the score module when there are multiple matches
        """
        # mock the eprint_bibstem patterns
        mock_query_eprint_bibstem.return_value = (
            [
                {'name': 'arXiv', 'pattern': r'^(\d\d\d\d(?:arXiv|acc\.phys|adap\.org|alg\.geom|ao\.sci|astro\.ph|atom\.ph|bayes\.an|chao\.dyn|chem\.ph|cmp\.lg|comp\.gas|cond\.mat|cs\.|dg\.ga|funct\.an|gr\.qc|hep\.ex|hep\.lat|hep\.ph|hep\.th|math\.|math\.ph|mtrl\.th|nlin\.|nucl\.ex|nucl\.th|patt\.sol|physics\.|plasm\.ph|q\.alg|q\.bio|quant\.ph|solv\.int|supr\.con))'},
                {'name': 'Earth Science', 'pattern': r'^(\d\d\d\d(?:EaArX|esoar))'},
            ],
            200
        )

        source_bibcode = '2022arXiv220606316S'
        abstract = 'In the present paper, discussion of the canonical quantization of a weakly nonideal Bose gas at zero temperature along the lines of the famous Bogolyubov approach is continued. Contrary to the previous paper on this subject, here the two-body interaction potential is considered in the general form. It is shown that consideration of the first nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach, without any modification of the resulting effective Hamiltonian.'
        title = 'Nonlinear corrections in the quantization of a weakly nonideal Bose gas   at zero temperature. II. The general case'
        author = 'Smolyakov, Mikhail N.'
        year = 2022
        doi = ['10.1016/j.chaos.2021.111505']
        doctype = 'eprint'

        # when multiple matches are found, and one record is returned
        matched_docs = [{'bibcode': '2021CSF...15311505S',
                         'abstract': 'In the present paper, quantization of a weakly nonideal Bose gas at zero temperature along the lines of the well-known Bogolyubov approach is performed. The analysis presented in this paper is based, in addition to the steps of the original Bogolyubov approach, on the use of nonoscillation modes (which are also solutions of the linearized Heisenberg equation) for recovering the canonical commutation relations in the linear approximation, as well as on the calculation of the first nonlinear correction to the solution of the linearized Heisenberg equation which satisfies the canonical commutation relations at the next order. It is shown that, at least in the case of free quasi-particles, consideration of the nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach.',
                         'author_norm': ['Smolyakov, M'],
                         'doctype': 'article',
                         'doi': ['10.1016/j.chaos.2021.111505'],
                         'identifier': ['10.1016/j.chaos.2021.111505', 'arXiv:2103.12030', '2021CSF...15311505S', '2021arXiv210312030S'],
                         'title': ['Nonlinear corrections in the quantization of a weakly nonideal Bose gas at zero temperature'],
                         'year': '2021',
                         'property': ['ARTICLE','EPRINT_OPENACCESS','ESOURCE','OPENACCESS','REFEREED']},
                        {'bibcode': '2024NYASA1531...15S',
                         'abstract': 'In the present paper, quantization of a weakly nonideal Bose gas at zero temperature along the lines of the well-known Bogolyubov approach is performed. The analysis presented in this paper is based, in addition to the steps of the original Bogolyubov approach, on the use of nonoscillation modes (which are also solutions of the linearized Heisenberg equation) for recovering the canonical commutation relations in the linear approximation, as well as on the calculation of the first nonlinear correction to the solution of the linearized Heisenberg equation which satisfies the canonical commutation relations at the next order. It is shown that, at least in the case of free quasi-particles, consideration of the nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach.',
                         'author_norm': ['Smolyakov, M'],
                         'doctype': 'article',
                         'identifier': ['10.1016/j.chaos.2021.111505', 'arXiv:2103.12030', '2021CSF...15311505S', '2021arXiv210312030S'],
                         'title': ['Nonlinear corrections in the quantization of a weakly nonideal Bose gas at zero temperature'],
                         'year': '2024',
                         'property': ['ARTICLE', 'ESOURCE', 'NOT REFEREED']}
                        ]

        match = get_matches(source_bibcode, doctype, '', title, author, year, doi, matched_docs)
        self.assertEqual(len(match), 1)
        self.assertDictEqual(match[0], {'source_bibcode': '2022arXiv220606316S',
                                        'matched_bibcode': '2021CSF...15311505S',
                                        'confidence': 0.9899692,
                                        'matched': 1,
                                        'scores': {'abstract': None, 'title': 0.98, 'author': 1, 'year': 1, 'doi': 1}})

        # when multiple matches are found by solr, but too close to call
        matched_docs = [{'bibcode': '2001CSF...15311505S',
                         'abstract': 'In the present paper, quantization of a weakly Bose gas at zero along the lines of the well-known Bogolyubov is performed. The analysis presented in this paper is based, in addition to the steps of the original Bogolyubov, on the use of nonoscillation modes (which are solutions of the linearized Heisenberg equation) for recovering the canonical commutation in the linear approximation, as well as on the of the first nonlinear correction to the solution of the Heisenberg equation which satisfies the canonical commutation relations at the next order. It is that, at least in the case of quasi-particles, consideration of the nonlinear correction solves the problem of nonconserved particle number, which is inherent to the original approach.',
                         'author_norm': ['Smolyakov, M'],
                         'doctype': 'article',
                         'title': ['Nonlinear corrections in the quantization of a weakly nonideal Bose gas at zero temperature'],
                         'year': '2001',
                         'property': ['ARTICLE','EPRINT_OPENACCESS','ESOURCE','OPENACCESS','REFEREED']},
                        {'bibcode': '2004NYASA1531...15S',
                         'abstract': 'In the present paper, quantization of a weakly nonideal Bose gas at zero temperature along the lines of the well-known Bogolyubov approach is performed. The analysis presented in this paper is based, in addition to the steps of the original Bogolyubov approach, on the use of modes (which are also solutions of the linearized Heisenberg equation) for recovering the canonical commutation relations in the linear approximation, as well as on the calculation of the first nonlinear correction to the solution of the linearized Heisenberg equation which satisfies the commutation relations at the next order. It is shown that, at least in the case of free quasi-particles, consideration of the correction automatically solves the problem of particle number, which is inherent to the approach.',
                         'author_norm': ['Smolyakov, M'],
                         'doctype': 'article',
                         'title': ['Nonlinear corrections in the quantization of a weakly nonideal Bose gas at zero temperature'],
                         'year': '2004',
                         'property': ['ARTICLE', 'ESOURCE', 'NOT REFEREED']}
                        ]

        match = get_matches(source_bibcode, doctype, abstract, title, author, year, doi, matched_docs)

        self.assertEqual(len(match), 2)
        self.assertEqual(match[0], {'source_bibcode': '2022arXiv220606316S',
                                    'matched_bibcode': '2004NYASA1531...15S',
                                    'confidence': 0.0225319,
                                    'matched': 0,
                                    'scores': {'abstract': 0.75, 'title': 0.98, 'author': 1, 'year': 0}})
        self.assertEqual(match[1], {'source_bibcode': '2022arXiv220606316S',
                                    'matched_bibcode': '2001CSF...15311505S',
                                    'confidence': 0.0164414,
                                    'matched': 0,
                                    'scores': {'abstract': 0.73, 'title': 0.98, 'author': 1, 'year': 0}})

    @mock.patch('oraclesrv.score.confidence_model.predict')
    @mock.patch('oraclesrv.score.get_a_record')
    @mock.patch('oraclesrv.utils.query_eprint_bibstem')
    def test_get_matches_when_prev_match_exist_source_eprint(self, mock_query_eprint_bibstem, mock_get_a_record, mock_confidence_model_predict):
        """
        Test get_matches function of the score module when there is a prev match and source bibcode is eprint
        """
        # mock the eprint_bibstem patterns
        mock_query_eprint_bibstem.return_value = (
            [
                {'name': 'arXiv', 'pattern': r'^(\d\d\d\d(?:arXiv|acc\.phys|adap\.org|alg\.geom|ao\.sci|astro\.ph|atom\.ph|bayes\.an|chao\.dyn|chem\.ph|cmp\.lg|comp\.gas|cond\.mat|cs\.|dg\.ga|funct\.an|gr\.qc|hep\.ex|hep\.lat|hep\.ph|hep\.th|math\.|math\.ph|mtrl\.th|nlin\.|nucl\.ex|nucl\.th|patt\.sol|physics\.|plasm\.ph|q\.alg|q\.bio|quant\.ph|solv\.int|supr\.con))'},
                {'name': 'Earth Science', 'pattern': r'^(\d\d\d\d(?:EaArX|esoar))'},
            ],
            200
        )

        source_bibcode = '2022arXiv220606316S'
        abstract = 'In the present paper, discussion of the canonical quantization of a weakly nonideal Bose gas at zero temperature along the lines of the famous Bogolyubov approach is continued. Contrary to the previous paper on this subject, here the two-body interaction potential is considered in the general form. It is shown that consideration of the first nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach, without any modification of the resulting effective Hamiltonian.'
        title = 'Nonlinear corrections in the quantization of a weakly nonideal Bose gas   at zero temperature. II. The general case'
        author = 'Smolyakov, Mikhail N.'
        year = 2022
        doi = ['10.1016/j.chaos.2021.111505']
        doctype = 'eprint'

        matched_docs = [{'bibcode': '2021CSF...15311505S',
                         'abstract': 'In the present paper, quantization of a weakly nonideal Bose gas at zero temperature along the lines of the well-known Bogolyubov approach is performed. The analysis presented in this paper is based, in addition to the steps of the original Bogolyubov approach, on the use of nonoscillation modes (which are also solutions of the linearized Heisenberg equation) for recovering the canonical commutation relations in the linear approximation, as well as on the calculation of the first nonlinear correction to the solution of the linearized Heisenberg equation which satisfies the canonical commutation relations at the next order. It is shown that, at least in the case of free quasi-particles, consideration of the nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach.',
                         'author_norm': ['Smolyakov, M'],
                         'doctype': 'article',
                         'doi': ['10.1016/j.chaos.2021.111505'],
                         'identifier': ['10.1016/j.chaos.2021.111505', 'arXiv:2103.12030', '2021CSF...15311505S', '2021arXiv210312030S'],
                         'title': ['Nonlinear corrections in the quantization of a weakly nonideal Bose gas at zero temperature'],
                         'year': '2021',
                         'property': ['ARTICLE','EPRINT_OPENACCESS','ESOURCE','OPENACCESS','REFEREED']}]

        # mock current match being lower than what is in database
        mock_confidence_model_predict.return_value = 0.88

        # mock the previous match with higher confidence
        mock_get_a_record.return_value = {
            'eprint_bibcode': '2022arXiv220606316S',
            'pub_bibcode': '2022CSF...27421615S',
            'confidence': 0.9
        }

        match = get_matches(source_bibcode, doctype, abstract, title, author, year, None, matched_docs)
        self.assertEqual(len(match), 1)
        self.assertDictEqual(match[0], {'source_bibcode': '2022arXiv220606316S',
                                        'matched_bibcode': '2022CSF...27421615S',
                                        'confidence': 0.9,
                                        'matched': 1,
                                        'scores': {}})

    @mock.patch('oraclesrv.score.confidence_model.predict')
    @mock.patch('oraclesrv.score.get_a_record')
    @mock.patch('oraclesrv.utils.query_eprint_bibstem')
    def test_get_matches_when_prev_match_exist_source_pub(self, mock_query_eprint_bibstem, mock_get_a_record, mock_confidence_model_predict):
        """
        Test get_matches function of the score module when there is a prev match and source bibcode is pub
        """
        # mock the eprint_bibstem patterns
        mock_query_eprint_bibstem.return_value = (
            [
                {'name': 'arXiv', 'pattern': r'^(\d\d\d\d(?:arXiv|acc\.phys|adap\.org|alg\.geom|ao\.sci|astro\.ph|atom\.ph|bayes\.an|chao\.dyn|chem\.ph|cmp\.lg|comp\.gas|cond\.mat|cs\.|dg\.ga|funct\.an|gr\.qc|hep\.ex|hep\.lat|hep\.ph|hep\.th|math\.|math\.ph|mtrl\.th|nlin\.|nucl\.ex|nucl\.th|patt\.sol|physics\.|plasm\.ph|q\.alg|q\.bio|quant\.ph|solv\.int|supr\.con))'},
                {'name': 'Earth Science', 'pattern': r'^(\d\d\d\d(?:EaArX|esoar))'},
            ],
            200
        )

        source_bibcode = '2021CSF...15311505S'
        abstract = 'In the present paper, discussion of the canonical quantization of a weakly nonideal Bose gas at zero temperature along the lines of the famous Bogolyubov approach is continued. Contrary to the previous paper on this subject, here the two-body interaction potential is considered in the general form. It is shown that consideration of the first nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach, without any modification of the resulting effective Hamiltonian.'
        title = 'Nonlinear corrections in the quantization of a weakly nonideal Bose gas   at zero temperature. II. The general case'
        author = 'Smolyakov, Mikhail N.'
        year = 2022
        doi = ['10.1016/j.chaos.2021.111505']
        doctype = 'article'

        matched_docs = [{'bibcode': '2022arXiv220606316S',
                         'abstract': 'In the present paper, quantization of a weakly nonideal Bose gas at zero temperature along the lines of the well-known Bogolyubov approach is performed. The analysis presented in this paper is based, in addition to the steps of the original Bogolyubov approach, on the use of nonoscillation modes (which are also solutions of the linearized Heisenberg equation) for recovering the canonical commutation relations in the linear approximation, as well as on the calculation of the first nonlinear correction to the solution of the linearized Heisenberg equation which satisfies the canonical commutation relations at the next order. It is shown that, at least in the case of free quasi-particles, consideration of the nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach.',
                         'author_norm': ['Smolyakov, M'],
                         'doctype': 'eprint',
                         'identifier': ['2021arXiv210312030S', 'arXiv:2103.12030'],
                         'title': ['Nonlinear corrections in the quantization of a weakly nonideal Bose gas at zero temperature'],
                         'year': '2021',
                         'property': ['ARTICLE','EPRINT_OPENACCESS','ESOURCE','OPENACCESS','REFEREED']}]

        # mock current match being lower than what is in database
        mock_confidence_model_predict.return_value = 0.88

        # mock the previous match with higher confidence
        mock_get_a_record.return_value = {
            'eprint_bibcode': '2018arXiv181105526S',
            'pub_bibcode': '2021CSF...15311505S',
            'confidence': 0.9
        }

        match = get_matches(source_bibcode, doctype, abstract, title, author, year, None, matched_docs)
        self.assertEqual(len(match), 1)
        self.assertDictEqual(match[0], {'source_bibcode': '2021CSF...15311505S',
                                        'matched_bibcode': '2018arXiv181105526S',
                                        'confidence': 0.9,
                                        'matched': 1,
                                        'scores': {}})

    @mock.patch('oraclesrv.score.confidence_model.predict')
    @mock.patch('oraclesrv.score.get_a_record')
    @mock.patch('oraclesrv.utils.query_eprint_bibstem')
    def test_get_matches_when_prev_match_exist_but_not_a_match_source_eprint(self,
                                                                             mock_query_eprint_bibstem,
                                                                             mock_get_a_record,
                                                                             mock_confidence_model_predict):
        """
        Test get_matches function of the score module when there is a prev match and source bibcode is eprint
        but the match is for another eprint bibcode
        """
        # mock the eprint_bibstem patterns
        mock_query_eprint_bibstem.return_value = (
            [
                {'name': 'arXiv',
                 'pattern': r'^(\d\d\d\d(?:arXiv|acc\.phys|adap\.org|alg\.geom|ao\.sci|astro\.ph|atom\.ph|bayes\.an|chao\.dyn|chem\.ph|cmp\.lg|comp\.gas|cond\.mat|cs\.|dg\.ga|funct\.an|gr\.qc|hep\.ex|hep\.lat|hep\.ph|hep\.th|math\.|math\.ph|mtrl\.th|nlin\.|nucl\.ex|nucl\.th|patt\.sol|physics\.|plasm\.ph|q\.alg|q\.bio|quant\.ph|solv\.int|supr\.con))'},
                {'name': 'Earth Science', 'pattern': r'^(\d\d\d\d(?:EaArX|esoar))'},
            ],
            200
        )

        source_bibcode = '2022arXiv220606316S'
        abstract = 'In the present paper, discussion of the canonical quantization of a weakly nonideal Bose gas at zero temperature along the lines of the famous Bogolyubov approach is continued. Contrary to the previous paper on this subject, here the two-body interaction potential is considered in the general form. It is shown that consideration of the first nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach, without any modification of the resulting effective Hamiltonian.'
        title = 'Nonlinear corrections in the quantization of a weakly nonideal Bose gas   at zero temperature. II. The general case'
        author = 'Smolyakov, Mikhail N.'
        year = 2022
        doi = ['10.1016/j.chaos.2021.111505']
        doctype = 'eprint'

        matched_docs = [{'bibcode': '2021CSF...15311505S',
                         'abstract': 'In the present paper, quantization of a weakly nonideal Bose gas at zero temperature along the lines of the well-known Bogolyubov approach is performed. The analysis presented in this paper is based, in addition to the steps of the original Bogolyubov approach, on the use of nonoscillation modes (which are also solutions of the linearized Heisenberg equation) for recovering the canonical commutation relations in the linear approximation, as well as on the calculation of the first nonlinear correction to the solution of the linearized Heisenberg equation which satisfies the canonical commutation relations at the next order. It is shown that, at least in the case of free quasi-particles, consideration of the nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach.',
                         'author_norm': ['Smolyakov, M'],
                         'doctype': 'article',
                         'doi': ['10.1016/j.chaos.2021.111505'],
                         'identifier': ['10.1016/j.chaos.2021.111505', 'arXiv:2103.12030', '2021CSF...15311505S',
                                        '2021arXiv210312030S'],
                         'title': [
                             'Nonlinear corrections in the quantization of a weakly nonideal Bose gas at zero temperature'],
                         'year': '2021',
                         'property': ['ARTICLE', 'EPRINT_OPENACCESS', 'ESOURCE', 'OPENACCESS', 'REFEREED']}]

        # mock current match being lower than what is in database
        mock_confidence_model_predict.return_value = 0.88

        # mock the previous match with higher confidence
        mock_get_a_record.return_value = {
            'eprint_bibcode': '2018arXiv181105526S',
            'pub_bibcode': '2021CSF...15311505S',
            'confidence': 0.9
        }

        match = get_matches(source_bibcode, doctype, abstract, title, author, year, None, matched_docs)
        self.assertEqual(len(match), 0)

    @mock.patch('oraclesrv.score.confidence_model.predict')
    @mock.patch('oraclesrv.score.get_a_record')
    @mock.patch('oraclesrv.utils.query_eprint_bibstem')
    def test_get_matches_when_prev_match_exist_but_not_a_match_source_pub(self,
                                                                          mock_query_eprint_bibstem,
                                                                          mock_get_a_record,
                                                                          mock_confidence_model_predict):
        """
        Test get_matches function of the score module when there is a prev match and source bibcode is pub
        but the match is for another pub bibcode
        """
        # mock the eprint_bibstem patterns
        mock_query_eprint_bibstem.return_value = (
            [
                {'name': 'arXiv',
                 'pattern': r'^(\d\d\d\d(?:arXiv|acc\.phys|adap\.org|alg\.geom|ao\.sci|astro\.ph|atom\.ph|bayes\.an|chao\.dyn|chem\.ph|cmp\.lg|comp\.gas|cond\.mat|cs\.|dg\.ga|funct\.an|gr\.qc|hep\.ex|hep\.lat|hep\.ph|hep\.th|math\.|math\.ph|mtrl\.th|nlin\.|nucl\.ex|nucl\.th|patt\.sol|physics\.|plasm\.ph|q\.alg|q\.bio|quant\.ph|solv\.int|supr\.con))'},
                {'name': 'Earth Science', 'pattern': r'^(\d\d\d\d(?:EaArX|esoar))'},
            ],
            200
        )

        source_bibcode = '2021CSF...15311505S'
        abstract = 'In the present paper, discussion of the canonical quantization of a weakly nonideal Bose gas at zero temperature along the lines of the famous Bogolyubov approach is continued. Contrary to the previous paper on this subject, here the two-body interaction potential is considered in the general form. It is shown that consideration of the first nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach, without any modification of the resulting effective Hamiltonian.'
        title = 'Nonlinear corrections in the quantization of a weakly nonideal Bose gas   at zero temperature. II. The general case'
        author = 'Smolyakov, Mikhail N.'
        year = 2022
        doi = ['10.1016/j.chaos.2021.111505']
        doctype = 'article'

        matched_docs = [{'bibcode': '2022arXiv220606316S',
                         'abstract': 'In the present paper, quantization of a weakly nonideal Bose gas at zero temperature along the lines of the well-known Bogolyubov approach is performed. The analysis presented in this paper is based, in addition to the steps of the original Bogolyubov approach, on the use of nonoscillation modes (which are also solutions of the linearized Heisenberg equation) for recovering the canonical commutation relations in the linear approximation, as well as on the calculation of the first nonlinear correction to the solution of the linearized Heisenberg equation which satisfies the canonical commutation relations at the next order. It is shown that, at least in the case of free quasi-particles, consideration of the nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach.',
                         'author_norm': ['Smolyakov, M'],
                         'doctype': 'eprint',
                         'identifier': ['2021arXiv210312030S', 'arXiv:2103.12030'],
                         'title': [
                             'Nonlinear corrections in the quantization of a weakly nonideal Bose gas at zero temperature'],
                         'year': '2021',
                         'property': ['ARTICLE', 'EPRINT_OPENACCESS', 'ESOURCE', 'OPENACCESS', 'REFEREED']}]

        # mock current match being lower than what is in database
        mock_confidence_model_predict.return_value = 0.88

        # mock the previous match with higher confidence
        mock_get_a_record.return_value = {
            'eprint_bibcode': '2022arXiv220606316S',
            'pub_bibcode': '2022CSF...27421615S',
            'confidence': 0.9
        }

        match = get_matches(source_bibcode, doctype, abstract, title, author, year, None, matched_docs)
        self.assertEqual(len(match), 0)

    def test_get_matches_when_source_and_match_equal(self):
        """
        Test get_matches function of the score module when source bibcode and match bibcode are the same
        """
        source_bibcode = '2022arXiv220606316S'
        abstract = 'In the present paper, discussion of the canonical quantization of a weakly nonideal Bose gas at zero temperature along the lines of the famous Bogolyubov approach is continued. Contrary to the previous paper on this subject, here the two-body interaction potential is considered in the general form. It is shown that consideration of the first nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach, without any modification of the resulting effective Hamiltonian.'
        title = 'Nonlinear corrections in the quantization of a weakly nonideal Bose gas   at zero temperature. II. The general case'
        author = 'Smolyakov, Mikhail N.'
        year = 2022
        doi = ['10.1016/j.chaos.2021.111505']
        doctype = 'eprint'

        # when match and source are the same
        matched_docs = [{'bibcode': '2022arXiv220606316S',
                         'abstract': 'In the present paper, discussion of the canonical quantization of a weakly nonideal Bose gas at zero temperature along the lines of the famous Bogolyubov approach is continued. Contrary to the previous paper on this subject, here the two-body interaction potential is considered in the general form. It is shown that consideration of the first nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach, without any modification of the resulting effective Hamiltonian.',
                         'author_norm': ['Smolyakov, M'],
                         'doctype': 'article',
                         'doi': ['10.1016/j.chaos.2021.111505'],
                         'identifier': ['10.1016/j.chaos.2021.111505', 'arXiv:2103.12030', '2021CSF...15311505S', '2021arXiv210312030S'],
                         'title': ['Nonlinear corrections in the quantization of a weakly nonideal Bose gas   at zero temperature. II. The general case'],
                         'year': '2022',
                         'property': ['ARTICLE', 'ESOURCE', 'NOT REFEREED']}
                        ]
        match = get_matches(source_bibcode, doctype, abstract, title, author, year, None, matched_docs)
        self.assertEqual(match, [])

    @mock.patch('oraclesrv.utils.query_eprint_bibstem')
    def test_get_match_for_pub_with_doi(self, mock_query_eprint_bibstem):
        """
        Test get_matches function of score module when matching publication with doi
        """
        # mock the eprint_bibstem patterns
        mock_query_eprint_bibstem.return_value = (
            [
                {'name': 'arXiv', 'pattern': r'^(\d\d\d\d(?:arXiv|acc\.phys|adap\.org|alg\.geom|ao\.sci|astro\.ph|atom\.ph|bayes\.an|chao\.dyn|chem\.ph|cmp\.lg|comp\.gas|cond\.mat|cs\.|dg\.ga|funct\.an|gr\.qc|hep\.ex|hep\.lat|hep\.ph|hep\.th|math\.|math\.ph|mtrl\.th|nlin\.|nucl\.ex|nucl\.th|patt\.sol|physics\.|plasm\.ph|q\.alg|q\.bio|quant\.ph|solv\.int|supr\.con))'},
                {'name': 'Earth Science', 'pattern': r'^(\d\d\d\d(?:EaArX|esoar))'},
            ],
            200
        )

        source_bibcode = '2022AcAT....3a..27P'
        abstract = 'Not Available'
        title = 'Revisiting the spectral energy distribution of I Zw 1 under the CaFe Project'
        author = 'Panda, Swayamtrupta; Dias dos Santos, Denimara'
        year = 2022
        doi = ['10.31059/aat.vol3.iss1.pp27-34']
        doctype = 'eprint'

        matched_docs = [{'bibcode': '2021arXiv211101521P',
                         'abstract': 'The CaFe Project involves the study of the properties of the low ionization emission lines (LILs) pertaining to the broad-line region (BLR) in active galaxies. These emission lines, especially the singly-ionized iron (Fe II) in the optical and the corresponding singly-ionized calcium (Ca II) in the near-infrared (NIR) are found to show a strong correlation in their emission strengths, i.e. with respect to the broad H$\\beta$ emission line, the latter also belonging to the same category of LILs. The origin of this correlation is attributed to the similarity in the physical conditions necessary to emit these lines - especially in terms of the strength of the ionization from the central continuum source and the local number density of available matter in these regions. In this paper, we focus on the issue of the spectral energy distribution (SED) characteristic to a prototypical Type-1 Narrow-line Seyfert galaxy (NLS1) - I Zw 1. We extract the continuum from quasi-simultaneous spectroscopic measurements ranging from the near-UV ($\\sim$1200A) to the near-infrared ($\\sim$24000A) to construct the SED and supplement it with archival X-ray measurements available for this source. Using the photoionization code CLOUDY, we assess and compare the contribution of the prominent \"Big Blue Bump\" seen in our SED versus the SED used in our previous work, wherein the latter was constructed from archival, multi-epoch photometric measurements. Following the prescription from our previous work, we constrain the physical parameter space to optimize the emission from these LILs and discuss the implication of the use of a \"better\" SED.',
                         'author_norm': ['Panda, S', 'Dias dos Santos, D'],
                         'doctype': 'eprint',
                         'identifier': ['arXiv:2111.01521', '2021arXiv211101521P'],
                         'title': ['Revisiting the spectral energy distribution of I Zw 1 under the CaFe Project'],
                         'year': '2021',
                         'property': ['ARTICLE','EPRINT_OPENACCESS','ESOURCE','OPENACCESS','NOT REFEREED'],
                         'doi_pubnote': '10.31059/aat.vol3.iss1.pp27-34'}]

        # abstract, no doi
        match = get_matches(source_bibcode, doctype, abstract, title, author, year, doi, matched_docs)
        self.assertEqual(len(match), 1)
        self.assertDictEqual(match[0], {'source_bibcode': '2022AcAT....3a..27P',
                                        'matched_bibcode': '2021arXiv211101521P',
                                        'confidence': 0.9911571,
                                        'matched': 1,
                                        'scores': {'abstract': None, 'title': 1.0, 'author': 1, 'year': 1, 'doi': 1}})

    def test_to_unicode(self):
        """
        Test to_unicode in the score module
        """
        self.assertEqual(to_unicode('a unicode \u018e string \xf1'), 'a unicode Ǝ string ñ')
        self.assertEqual(to_unicode('copyright symbol: &copy; and trademark symbol &trade;'), 'copyright symbol: © and trademark symbol ™')
        self.assertEqual(to_unicode('send &unrecognizable; code to return'), 'send  code to return')

    def test_docmatching_process(self):
        """
        Test DocMatching class's process function
        """
        # when neither title nor abstract is passed in
        results, status_code = DocMatching(payload={'author':'author here', 'year': 2000, 'doctype': 'eprint'}).process()
        self.assertEqual(results, {'error': 'the following parameters are required: `abstract` or `title`, `author`, `year`,  and `doctype`'})
        self.assertEqual(status_code, 400)

        # when doctype is unrecognizable
        results, status_code = DocMatching(payload={'abstract': 'available', 'title': 'available', 'author': 'available', 'year': 2000, 'doctype': 'unrecognizable'}).process()
        self.assertEqual(results, {'error': 'invalid doctype `unrecognizable`'})
        self.assertEqual(status_code, 400)

    def test_sql_alchemy_exception(self):
        """
        Test utils moddule's functions when there is an SQLAlchemyError
        """
        with mock.patch('oraclesrv.utils.get_solr_data') as solr_mock:
            http_error = HTTPError()
            http_error.response = Response()
            http_error.response.status_code = 404
            http_error.response.reason = "not found"
            solr_mock.side_effect = http_error

            # exception within get_solr_data_recommend
            result, _, _ = get_solr_data_recommend(function='function to execute', reader='reader id')
            self.assertEqual(result, {'error from solr': '404: not found'})

            # exception within get_solr_data_match
            result, _, _ = get_solr_data_match('abstract here', 'title here', doctype='eprint', match_doctype='article', extra_filter='')
            self.assertEqual(result, {'error from solr': '404: not found'})

            # exception within get_solr_data_match_doi
            result, _, _ = get_solr_data_match_doi('doi here', doctype='eprint', match_doctype='article')
            self.assertEqual(result, {'error from solr': '404: not found'})

            # exception within get_solr_data_match_pubnote
            result, _, _ = get_solr_data_match_pubnote('doi here', doctype='eprint', match_doctype='article')
            self.assertEqual(result, {'error from solr': '404: not found'})

            # exception within get_solr_data_match_doctype_case
            result, _, _ = get_solr_data_match_doctype_case('author here', 2000, doctype='eprint', match_doctype='article')
            self.assertEqual(result, {'error from solr': '404: not found'})

    def test_get_solr_data_chunk(self):
        """
        Test get_solr_data_chunk function of the utils module
        """

        def create_response(text):
            """ create a response object """
            response = requests.Response()
            response.status_code = 200
            response._content = bytes(json.dumps(text).encode('utf-8'))
            return response

        # verify that a chunk is now 2
        max_bibcodes = self.current_app.config['ORACLE_SERVICE_MAX_RECORDS_SOLRQUERY']
        self.assertEqual(max_bibcodes, 2)

        # sending 7 bibcodes that should get processed in four chunks
        bibcodes = [
            '2023MNRAS.tmp.1609L', '2023MNRAS.tmp.1679S', '2023MNRAS.tmp.1683W', '2023MNRAS.tmpL..73C',
            '2023MNRAS.tmp.1729N', '2023MNRAS.tmp.1672V', '2023MNRAS.tmp.1673T',
        ]

        results = [
            {
                'responseHeader': {'status': 0, 'QTime': 3,
                                'params': {'q': 'identifier:("2023MNRAS.tmp.1609L" OR "2023MNRAS.tmp.1679S")',
                                           'fl': 'bibcode,identifier', 'start': '0',
                                           'internal_logging_params': 'X-Amzn-Trace-Id=Root=1-64c3d594-219029c018b8392d240bc153',
                                           'sort': 'date desc,bibcode desc', 'rows': '2', 'wt': 'json'}},
                'response': {'numFound': 2, 'start': 0, 'docs': [{'bibcode': '2023MNRAS.523.4739S',
                                                               'identifier': ['2023arXiv230601119S',
                                                                              '10.1093/mnras/stad1711',
                                                                              'arXiv:2306.01119', '2023MNRAS.523.4739S',
                                                                              '10.48550/arXiv.2306.01119',
                                                                              '2023MNRAS.tmp.1679S']},
                                                              {'bibcode': '2023MNRAS.523.4029L',
                                                               'identifier': ['2023MNRAS.523.4029L',
                                                                              '2023arXiv230600447L',
                                                                              '10.48550/arXiv.2306.00447',
                                                                              'arXiv:2306.00447', '2023MNRAS.tmp.1609L',
                                                                              '10.1093/mnras/stad1670']}]}
            }, {
                'responseHeader': {'status': 0, 'QTime': 2,
                                'params': {'q': 'identifier:("2023MNRAS.tmp.1683W" OR "2023MNRAS.tmpL..73C")',
                                           'fl': 'bibcode,identifier', 'start': '0',
                                           'internal_logging_params': 'X-Amzn-Trace-Id=Root=1-64c3d595-207244706e35b4d43ed7937e',
                                           'sort': 'date desc,bibcode desc', 'rows': '2', 'wt': 'json'}},
                'response': {'numFound': 2, 'start': 0, 'docs': [{'bibcode': '2023MNRAS.524L..61C',
                                                               'identifier': ['arXiv:2306.02536',
                                                                              '10.1093/mnrasl/slad072',
                                                                              '2023arXiv230602536C',
                                                                              '10.48550/arXiv.2306.02536',
                                                                              '2023MNRAS.524L..61C',
                                                                              '2023MNRAS.tmpL..73C']},
                                                              {'bibcode': '2023MNRAS.523.4801W',
                                                               'identifier': ['2023MNRAS.tmp.1683W',
                                                                              '10.48550/arXiv.2306.01283',
                                                                              '2023arXiv230601283W',
                                                                              '2023MNRAS.523.4801W',
                                                                              '10.1093/mnras/stad1673',
                                                                              'arXiv:2306.01283']}]}
            }, {
                'responseHeader': {'status': 0, 'QTime': 3,
                                'params': {'q': 'identifier:("2023MNRAS.tmp.1729N" OR "2023MNRAS.tmp.1672V")',
                                           'fl': 'bibcode,identifier', 'start': '0',
                                           'internal_logging_params': 'X-Amzn-Trace-Id=Root=1-64c3d595-5c97bb2f4abdcc827feb81aa',
                                           'sort': 'date desc,bibcode desc', 'rows': '2', 'wt': 'json'}},
                'response': {'numFound': 2, 'start': 0, 'docs': [{'bibcode': '2023MNRAS.524.1156V',
                                                               'identifier': ['2023MNRAS.524.1156V',
                                                                              '2023MNRAS.tmp.1729N',
                                                                              '2023arXiv230602945V',
                                                                              '10.48550/arXiv.2306.02945',
                                                                              'arXiv:2306.02945',
                                                                              '10.1093/mnras/stad1742']},
                                                              {'bibcode': '2023MNRAS.523.4624V',
                                                               'identifier': ['10.1093/mnras/stad1719',
                                                                              '2023arXiv230603140V',
                                                                              '10.48550/arXiv.2306.03140',
                                                                              '2023MNRAS.tmp.1672V',
                                                                              '2023MNRAS.523.4624V',
                                                                              'arXiv:2306.03140']}]}
            }, {
                'responseHeader': {'status': 0, 'QTime': 2,
                                'params': {'q': 'identifier:("2023MNRAS.tmp.1673T")', 'fl': 'bibcode,identifier',
                                           'start': '0',
                                           'internal_logging_params': 'X-Amzn-Trace-Id=Root=1-64c3d595-678ad03e73888fb700a8416c',
                                           'sort': 'date desc,bibcode desc', 'rows': '1', 'wt': 'json'}},
                'response': {'numFound': 1, 'start': 0, 'docs': [{'bibcode': '2023MNRAS.523.4520T',
                                                               'identifier': ['2023MNRAS.tmp.1673T',
                                                                              '10.1093/mnras/stad1729',
                                                                              '10.48550/arXiv.2306.04691',
                                                                              '2023arXiv230604691T', 'arXiv:2306.04691',
                                                                              '2023MNRAS.523.4520T']}]}
            }

        ]

        return_values = []
        for result in results:
            return_values.append(create_response(result))

        expected = [
            {'bibcode': '2023MNRAS.523.4739S', 'identifier': ['2023arXiv230601119S', '10.1093/mnras/stad1711', 'arXiv:2306.01119', '2023MNRAS.523.4739S', '10.48550/arXiv.2306.01119', '2023MNRAS.tmp.1679S']},
            {'bibcode': '2023MNRAS.523.4029L', 'identifier': ['2023MNRAS.523.4029L', '2023arXiv230600447L', '10.48550/arXiv.2306.00447', 'arXiv:2306.00447', '2023MNRAS.tmp.1609L', '10.1093/mnras/stad1670']},
            {'bibcode': '2023MNRAS.524L..61C', 'identifier': ['arXiv:2306.02536', '10.1093/mnrasl/slad072', '2023arXiv230602536C', '10.48550/arXiv.2306.02536', '2023MNRAS.524L..61C', '2023MNRAS.tmpL..73C']},
            {'bibcode': '2023MNRAS.523.4801W', 'identifier': ['2023MNRAS.tmp.1683W', '10.48550/arXiv.2306.01283', '2023arXiv230601283W', '2023MNRAS.523.4801W', '10.1093/mnras/stad1673', 'arXiv:2306.01283']},
            {'bibcode': '2023MNRAS.524.1156V', 'identifier': ['2023MNRAS.524.1156V', '2023MNRAS.tmp.1729N', '2023arXiv230602945V', '10.48550/arXiv.2306.02945', 'arXiv:2306.02945', '10.1093/mnras/stad1742']},
            {'bibcode': '2023MNRAS.523.4624V', 'identifier': ['10.1093/mnras/stad1719', '2023arXiv230603140V', '10.48550/arXiv.2306.03140', '2023MNRAS.tmp.1672V', '2023MNRAS.523.4624V', 'arXiv:2306.03140']},
            {'bibcode': '2023MNRAS.523.4520T', 'identifier': ['2023MNRAS.tmp.1673T', '10.1093/mnras/stad1729', '10.48550/arXiv.2306.04691', '2023arXiv230604691T', 'arXiv:2306.04691', '2023MNRAS.523.4520T']}
        ]

        with mock.patch('requests.get', side_effect=return_values):
            docs, status = get_solr_data_chunk(bibcodes)

            # all info in returned in one chunk
            self.assertEqual(len(bibcodes), len(expected))
            self.assertEqual(docs, expected)

    def test_query_doi(self):
        """
        Test the query_doi function of DocMatching when solr returns no results or no matches are found.
        """
        payload = {
            'doi': ['10.1234/mock.doi'],
            'doctype': 'eprint',
            'match_doctype': ['article']
        }
        comment = 'some DOI query'
        doc_match = DocMatching(payload)

        with mock.patch('oraclesrv.doc_matching.get_solr_data_match_doi') as mock_get_solr_data_match_doi:
            with mock.patch.object(self.current_app.logger, 'debug') as mock_debug:

                # when solr returns no results
                mock_get_solr_data_match_doi.return_value = ([], 'mock_query', 200)
                result, updated_comment = doc_match.query_doi(comment)

                self.assertIsNone(result)
                self.assertIn('No result from solr with DOI', updated_comment)
                mock_debug.assert_any_call('No result from solr with DOI %s.' % payload['doi'])

                # when solr returns results, but no matches are found
                mock_get_solr_data_match_doi.return_value = ([{'bibcode': '2000Bibcode.......A'}], 'mock_query', 200)
                with mock.patch('oraclesrv.doc_matching.get_doi_match') as mock_get_doi_match:
                    mock_get_doi_match.return_value = None

                    result, updated_comment = doc_match.query_doi(comment)

                    self.assertIsNone(result)
                    self.assertIn('No matches with DOI', updated_comment)
                    mock_debug.assert_any_call('No matches with DOI %s, trying Abstract.' % payload['doi'])

    def test_query_pubnote(self):
        """
        Test the query_pubnote function of DocMatching when solr returns no results or no matches are found.
        """
        payload = {
            'doi': ['10.1234/mock.doi'],
            'doctype': 'article',
            'match_doctype': ['eprint']
        }
        comment = 'some pubnote query'
        doc_match = DocMatching(payload)

        with mock.patch('oraclesrv.doc_matching.get_solr_data_match_pubnote') as mock_get_solr_data_match_pubnote:
             with mock.patch.object(self.current_app.logger, 'debug') as mock_debug:

                # when solr call to return no results
                mock_get_solr_data_match_pubnote.return_value = ([], 'mock_query', 200)

                # Test the first `else` block (no results from Solr)
                result, updated_comment = doc_match.query_pubnote(comment)
                self.assertIsNone(result)
                self.assertIn('No result from solr with DOI', updated_comment)
                mock_debug.assert_any_call('No result from solr with DOI %s in pubnote.' % payload['doi'])

                with mock.patch('oraclesrv.doc_matching.get_doi_match') as mock_get_doi_match:

                    # when solr call to return results but no match is found
                    mock_get_solr_data_match_pubnote.return_value = ([{'mock': 'data'}], 'mock_query', 200)
                    mock_get_doi_match.return_value = None

                    # Test the second `else` block (no matches found)
                    result, updated_comment = doc_match.query_pubnote(comment)
                    self.assertIsNone(result)
                    self.assertIn('No matches with DOI', updated_comment)
                    mock_debug.assert_any_call('No matches with DOI %s in pubnote, trying Abstract.' % payload['doi'])

    def test_query_abstract_or_title(self):
        """
        Test query_abstract_or_title of DocMatching when no matches are found with abstract, and it retries with title.
        """
        payload = {
            'abstract': 'Mock abstract text.',
            'title': 'Mock title text.',
            'doctype': 'article',
            'match_doctype': ['eprint'],
        }
        comment = 'some abstract/title query'
        doc_match = DocMatching(payload)

        with mock.patch('oraclesrv.doc_matching.get_solr_data_match') as mock_get_solr_data_match, \
                mock.patch('oraclesrv.doc_matching.get_matches', return_value=[]), \
                mock.patch.object(self.current_app.logger, 'debug') as mock_debug:

            # twice calling,
            # first some results with abstract, but no match
            # second no results with title
            mock_get_solr_data_match.side_effect = [
                ([{'bibcode': '2000Bibcode.......A'}], 'mock_query_with_abstract', 200),
                ([], 'mock_query_with_abstract', 400)
            ]

            result = doc_match.query_abstract_or_title(comment)
            mock_debug.assert_any_call('No matches with Abstract, trying Title.')

    def test_query_doctype(self):
        """
        Test query_doctype function of DocMatching when no matches are found from Solr results
        """
        payload = {
            'author': 'Mock Author',
            'year': 2021,
            'doctype': 'article',
            'match_doctype': ['eprint']
        }
        comment = 'some doctype query'
        doc_match = DocMatching(payload)

        with mock.patch('oraclesrv.doc_matching.get_solr_data_match_doctype_case') as mock_get_solr_data_match_doctype_case, \
                mock.patch('oraclesrv.doc_matching.get_matches', return_value=None), \
                mock.patch.object(self.current_app.logger, 'debug') as mock_debug, \
                mock.patch.object(doc_match, 'create_and_return_response') as mock_create_response:

            mock_get_solr_data_match_doctype_case.return_value = ([{'bibcode': '2021MockBibcode.......A'}], 'mock_query_with_doctype', 200)

            result = doc_match.query_doctype(comment)

            mock_debug.assert_any_call('No result from solr for eprint.')
            mock_get_solr_data_match_doctype_case.assert_called_once_with(payload['author'], payload['year'], payload['doctype'], '"%s"' % '" OR "'.join(payload['match_doctype']))
            mock_create_response.assert_called_once_with(match=None, query='mock_query_with_doctype', comment='some doctype query No result from solr for eprint.')

    def test_query_abstract_or_title(self):
        """
        Test query_abstract_or_title function of DocMatching for several scenarios
        """
        payload = {
            'abstract': 'Mock abstract text.',
            'title': 'Mock title text.',
            'doctype': 'article',
            'match_doctype': ['eprint'],
            'extra_filter': ''
        }
        comment = 'some query'
        doc_match = DocMatching(payload)

        with mock.patch('oraclesrv.doc_matching.get_solr_data_match') as mock_get_solr_data_match, \
                mock.patch('oraclesrv.doc_matching.get_db_match') as mock_get_db_match, \
                mock.patch('oraclesrv.doc_matching.get_matches') as mock_get_matches, \
                mock.patch.object(self.current_app.logger, 'debug') as mock_debug, \
                mock.patch.object(doc_match, 'create_and_return_response') as mock_create_response:

            # when solr return error with abstract query
            mock_get_solr_data_match.return_value = ([], 'mock_query_with_abstract', 400)
            result = doc_match.query_abstract_or_title(comment)
            mock_create_response.assert_any_call([], 'mock_query_with_abstract', 'status code: 400')

            # when solr errors no records with abstract but then errors on title query
            mock_get_solr_data_match.side_effect = [
                ([], 'mock_query_with_abstract', 200),
                ([], 'mock_query_with_title', 400),
            ]
            result = doc_match.query_abstract_or_title(comment)
            mock_create_response.assert_any_call([], 'mock_query_with_title', 'status code: 400')

            # when there are results from solr, but there are no matches, after no matches, query again with title, and error
            mock_get_solr_data_match.side_effect = [
                ([{'bibcode': '2000Bibcode.......A'}], 'mock_query_with_abstract', 200),
                ([], 'mock_query_with_title', 400),
            ]
            mock_get_matches.return_value = []
            result = doc_match.query_abstract_or_title(comment)
            mock_create_response.assert_any_call([], 'mock_query_with_title', 'status code: 400')

            # when abstract matches are returned from solr, but no match is found, query again with title, and no matches are found
            # also no matches in the database
            mock_get_solr_data_match.side_effect = [
                ([{'bibcode': '2000Bibcode.......A'}], 'mock_query_with_abstract', 200),
                ([], 'mock_query_with_title', 200),
            ]
            mock_get_matches.return_value = []
            mock_get_db_match.return_value = []
            result = doc_match.query_abstract_or_title(comment)
            mock_create_response.assert_any_call(match='', query='mock_query_with_title', comment='some query No matches with Abstract, trying Title. No result from solr with Title. No matches in database either.')

            # when abstract matches are returned from solr, but no match is found, query again with title, and no matches are found
            # then query database and there is a matches in the database
            mock_get_solr_data_match.side_effect = [
                ([{'bibcode': '2000Bibcode.......A'}], 'mock_query_with_abstract', 200),
                ([], 'mock_query_with_title', 200),
            ]
            mock_get_matches.return_value = []
            mock_get_db_match.return_value = [{'bibcode': '2000Bibcode.......A'}]
            result = doc_match.query_abstract_or_title(comment)
            mock_create_response.assert_any_call([{'bibcode': '2000Bibcode.......A'}], 'mock_query_with_title', 'some query No matches with Abstract, trying Title. No result from solr with Title. Fetched from database.')

            # when abstract matches are returned from solr, but no match is found, query again with title, there are matches
            mock_get_solr_data_match.side_effect = [
                ([{'bibcode': '2000Bibcode.......A'}], 'mock_query_with_abstract', 200),
                ([{'bibcode': '2001Bibcode.......A'}], 'mock_query_with_title', 200),
            ]
            mock_get_matches.side_effect = [[], [{'bibcode': '2001Bibcode.......A'}]]
            result = doc_match.query_abstract_or_title(comment)
            mock_create_response.assert_any_call([{'bibcode': '2001Bibcode.......A'}], 'mock_query_with_title', 'some query No matches with Abstract, trying Title.')

    def test_get_db_match(self):
        """
        Test get_db_match function of the score module
        """
        # mocked record returned by get_a_matched_record
        with mock.patch('oraclesrv.score.get_a_matched_record') as mock_get_a_matched_record:
            mock_get_a_matched_record.return_value = {
                'pub_bibcode': '2021arXiv210312030S',
                'eprint_bibcode': '2021CSF...15311505S',
                'confidence': 0.9829099}

            match = get_db_match(source_bibcode='2021arXiv210312030S')
            self.assertEqual(len(match), 1)
            self.assertDictEqual(match[0], {'source_bibcode': '2021arXiv210312030S',
                                             'matched_bibcode': '2021CSF...15311505S',
                                             'confidence': 0.9829099,
                                             'matched': 1,
                                             'scores': {}})

    def test_count_matching_authors(self):
        """
        Test count_matching_authors function of the score module
        """
        # invalid reference authors
        result = count_matching_authors(ref_authors=None, ads_authors=["Smith, J", "Jones, S"])
        self.assertEqual(result, (0, 0, 0, False))

        # test when matching_authors can match the last names
        result = count_matching_authors(ref_authors="Brown", ads_authors=["Smith, J", "Jones, S", "Brown, A"])
        self.assertEqual(result, (0, 2, 1, True))

    def test_get_year_score(self):
        """
        Test get_year_score function of the score module
        """
        self.assertEqual(get_year_score(2024-2024), 1)
        self.assertEqual(get_year_score(2024-2023), 1)
        self.assertEqual(get_year_score(2024-2022), 0.75)
        self.assertEqual(get_year_score(2024-2021), 0.5)
        self.assertEqual(get_year_score(2024-2020), 0.25)
        self.assertEqual(get_year_score(2024-2019), 0)
        self.assertEqual(get_year_score(2019-2025), 1)

    def test_encode_author(self):
        """
        Test encode_author function of the score module when author is invalid
        """
        self.assertIsNone(encode_author(None))

    def test_get_doi_match(self):
        """
        Test get_doi_match function of the score module when there are no matches, or there are more than two matches
        """
        source_bibcode = '2022arXiv220606316S'
        abstract = 'In the present paper, discussion of the canonical quantization of a weakly nonideal Bose gas at zero temperature along the lines of the famous Bogolyubov approach is continued. Contrary to the previous paper on this subject, here the two-body interaction potential is considered in the general form. It is shown that consideration of the first nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach, without any modification of the resulting effective Hamiltonian.'
        title = 'Nonlinear corrections in the quantization of a weakly nonideal Bose gas   at zero temperature. II. The general case'
        author = 'Smolyakov, Mikhail N.'
        year = 2022
        doi = ['10.1016/j.chaos.2021.111505']
        doctype = 'eprint'

        # when there are no matches with doi
        with mock.patch('oraclesrv.score.get_doi_match') as mock_get_doi_match:
            mock_get_doi_match.return_value = None
            self.assertEqual(get_doi_match(source_bibcode, doctype, abstract, title, author, year, doi, matched_docs=[]), [])

        matched_docs = [{'bibcode': '2021CSF...15311505S',
                         'abstract': 'In the present paper, quantization of a weakly nonideal Bose gas at zero temperature along the lines of the well-known Bogolyubov approach is performed. The analysis presented in this paper is based, in addition to the steps of the original Bogolyubov approach, on the use of nonoscillation modes (which are also solutions of the linearized Heisenberg equation) for recovering the canonical commutation relations in the linear approximation, as well as on the calculation of the first nonlinear correction to the solution of the linearized Heisenberg equation which satisfies the canonical commutation relations at the next order. It is shown that, at least in the case of free quasi-particles, consideration of the nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach.',
                         'author_norm': ['Smolyakov, M'],
                         'doctype': 'article',
                         'identifier': ['10.1016/j.chaos.2021.111505', 'arXiv:2103.12030', '2021CSF...15311505S', '2021arXiv210312030S'],
                         'title': ['Nonlinear corrections in the quantization of a weakly nonideal Bose gas at zero temperature'],
                         'year': '2021',
                         'doi': ['10.1016/j.chaos.2021.111505']},
                        {'bibcode': '2020PhRvR...2c3276C',
                         'abstract': 'We develop a quantum many-body theory of the Bose-Hubbard model based on the canonical quantization of the action derived from a Gutzwiller mean-field ansatz. Our theory is a systematic generalization of the Bogoliubov theory of weakly interacting gases. The control parameter of the theory, defined as the zero point fluctuations on top of the Gutzwiller mean-field state, remains small in all regimes. The approach provides accurate results throughout the whole phase diagram, from the weakly to the strongly interacting superfluid and into the Mott insulating phase. As specific examples of application, we study the two-point correlation functions, the superfluid stiffness, and the density fluctuations, for which quantitative agreement with available quantum Monte Carlo data is found. In particular, the two different universality classes of the superfluid-insulator quantum phase transition at integer and noninteger filling are recovered.',
                         'author_norm': ['Caleffi, F', 'Capone, M', 'Menotti, C', 'Carusotto, I', 'Recati, A'],
                         'doctype': 'article',
                         'identifier': ['arXiv:1908.03470', '2019arXiv190803470C', '10.1103/PhysRevResearch.2.033276', '2020PhRvR...2c3276C'],
                         'title': ['Quantum fluctuations beyond the Gutzwiller approximation in the Bose-Hubbard model'],
                         'year': '2020',
                         'doi': ['10.1016/j.chaos.2021.111505']}]
        # when there are more than one matches with doi
        with mock.patch('oraclesrv.score.get_doi_match') as mock_get_doi_match:
            mock_get_doi_match.return_value = matched_docs
            self.assertEqual(get_doi_match(source_bibcode, doctype, abstract, title, author, year, doi, matched_docs=[]), [])

    def test_get_solr_data_match(self):
        """
        Test get_solr_data_match function of the utils module
        """
        result, query, status_code = get_solr_data_match(abstract='', title='', doctype='eprint', match_doctype='article', extra_filter='')
        self.assertEqual(result, [])
        self.assertEqual(query, '')
        self.assertEqual(status_code, 200)

    def test_get_author_score(self):
        """
        Test get_author_score function of the score module when either or both authors are invalid
        """
        self.assertEqual(get_author_score(ref_authors='', ads_authors='Smith, J'), 0)
        self.assertEqual(get_author_score(ref_authors='Smith, J', ads_authors=''), 0)
        self.assertEqual(get_author_score(ref_authors='Smith, J', ads_authors=''), 0)

    def test_get_solr_data(self):
        """
        Test get_solr_data function of the utils module
        """
        # test when connection pool is enabled
        with mock.patch('oraclesrv.utils.current_app.client.get') as mock_requests_get:
            # mock response from requests.get
            mock_response = mock.Mock()
            mock_response.raise_for_status = mock.Mock()
            mock_response.json.return_value = {'response': {'numFound': 1,'docs': [{'bibcode': '2022TEST..........S'}]}}
            mock_requests_get.return_value = mock_response

            result, status_code = get_solr_data(rows=1, query='2022TEST..........S', fl='bibcode')

            self.assertEqual(result, ['2022TEST..........S'])
            self.assertEqual(status_code, mock_response.status_code)

        # test when connection pool is disabled
        self.current_app.config['REQUESTS_CONNECTION_POOL_ENABLED'] = False

        # mock has_request_context and request.headers.get
        with mock.patch('oraclesrv.utils.flask.has_request_context', return_value=True), \
             mock.patch('oraclesrv.utils.flask.request') as mock_request, \
             mock.patch('oraclesrv.utils.requests.get') as mock_requests_get:

            # mock request headers
            mock_request.headers.get.side_effect = lambda key, default=None: f"mock-{key}"

            # mock response from requests.get
            mock_response = mock.Mock()
            mock_response.raise_for_status = mock.Mock()
            mock_response.json.return_value = {'response': {'numFound': 1, 'docs': [{'bibcode': '2022TEST..........S'}]}}
            mock_requests_get.return_value = mock_response

            result, status_code = get_solr_data(rows=1, query='bibcode:2024TEST..........S', fl='bibcode')

            self.assertEqual(result, ['2022TEST..........S'])
            self.assertEqual(status_code, mock_response.status_code)

if __name__ == "__main__":
    unittest.main()
