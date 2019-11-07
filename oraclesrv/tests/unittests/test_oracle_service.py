
import sys
import os
PROJECT_HOME = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(PROJECT_HOME)

from flask_testing import TestCase
import unittest
import json
import mock

import oraclesrv.app as app
from oraclesrv.views import get_user_info_from_adsws

class test_oracle(TestCase):
    def create_app(self):
        self.current_app = app.create_app(**{'TESTING': True})
        return self.current_app

    def test_readhist_endpoint_post(self):
        """
        Tests POST for readhist endpoint when no optional param passed in, so default is returned
        """
        # the mock is for solr call
        with mock.patch.object(self.current_app.client, 'get'):
            r= self.client.post(path='/readhist', data='{"function":"trending", "reader":"0000000000000000"}')
            self.assertEqual(json.loads(r.data)['query'],
                             "(trending(topn(10, reader:0000000000000000, entry_date desc)) entdate:[NOW-5DAYS TO *])")

    def test_readhist_endpoint_get(self):
        """
        Tests GET endpoint for readhist endpoint with default params
        """
        # the mock is for solr call
        with mock.patch.object(self.current_app.client, 'get'):
            r= self.client.get(path='/readhist/similar/0000000000000000')
            self.assertEqual(json.loads(r.data)['query'],
                             "(similar(topn(10, reader:0000000000000000, entry_date desc)) entdate:[NOW-5DAYS TO *])")

    def test_readhist_endpoint_optional_params_post(self):
        """
        Test optional params with POST for readhist endpoint
        """
        # the mock is for solr call
        with mock.patch.object(self.current_app.client, 'get'):
            params = {'function': 'trending',
                      'reader': '0000000000000000',
                      'sort': 'date',
                      'num_docs': 10,
                      'cutoff_days': 12,
                      'top_n_reads' : 14}
            r= self.client.post(path='/readhist', data=params)
            self.assertEqual(json.loads(r.data)['query'],
                             "(trending(topn(14, reader:0000000000000000, date desc)) entdate:[NOW-12DAYS TO *])")

    def test_readhist_endpoint_optional_params_get(self):
        """
        Test optional params with GET for readhist endpoint
        """
        # the mock is for solr call
        with mock.patch.object(self.current_app.client, 'get'):
            params = {'function': 'similar',
                      'reader': '0000000000000000',
                      'sort': 'date',
                      'num_docs': 10,
                      'cutoff_days': 12,
                      'top_n_reads' : 14}
            r= self.client.get(path='/readhist', query_string=params)
            self.assertEqual(json.loads(r.data)['query'],
                             "(similar(topn(14, reader:0000000000000000, date desc)) entdate:[NOW-12DAYS TO *])")

    def test_readhist_endpoint_with_session(self):
        """
        Test readhist endpoint with session when adsws is not available
        """
        # the mock is for adsws call
        with mock.patch.object(self.current_app.client, 'get') as get_mock:
            get_mock.return_value = mock_response = mock.Mock()
            mock_response.json.return_value = {'error':'error'}
            mock_response.status_code = 404
            cookie = '.eJw9j02LgzAYhP_K8p576HbpVoQeCqGiEENdQ9ZcpKtJ_ExLjOtH6X9fEbaHgWFgnmEekEojugJca3qxgbTMwX3A2w-4wCt_i72gTlreclTUSZxXmOEPgtQUIn-3aI9nOvJYHeG5dO_CtFcttP2nZZ2Rqb3VQr-gmPGGV3TAMZ3C-TQRz98T5k-4DSo8qyVXQ8h4weOoIYvnCI-JOq4Dt2tvizRrynUCDPUk0Xd7-drK7PBbDtn3KZBOeR4jNtJop51PZ0D5GTbQd8Ks1-Adnn_261Ge.Xa8Ckw.88nMjVOHNu90gSpkY16da5SMtTA'
            self.client.set_cookie('/', 'session', cookie)
            r= self.client.post(path='/readhist', data={'sort': 'date'})
            self.assertEqual(r.status_code, 400)
            self.assertEqual(json.loads(r.data)['error'], "unable to obtain reader id")

    def test_readhist_endpoint_no_required_param(self):
        """
        Test readhist endpoint when neither reader nor session were passed in
        """
        r= self.client.post(path='/readhist', data=json.dumps({'missingReader':''}))
        self.assertEqual(json.loads(r.data)['error'],
                         "neither reader found in payload (parameter name is `reader`) nor session information received")

    def test_readhist_endpoint_no_data(self):
        """
        Test readhist endpoint with no payload
        """
        r= self.client.post(path='/readhist', data=None)
        self.assertEqual(json.loads(r.data)['error'], "no information received")

    def test_readhist_endpoint_adsws_call(self):
        """
        Test readhist endpoint adsws call directly with session
        """
        with mock.patch.object(self.current_app.client, 'get') as get_mock:
            client_id = 'aaaaaaaabbbbbbbbccccccccddddddddeeeeeeeeffffffffgggggggghhhhhhhh'
            session = '.eJw9j02LgzAYhP_K8p576HbpVoQeCqGiEENdQ9ZcpKtJ_ExLjOtH6X9fEbaHgWFgnmEekEojugJca3qxgbTMwX3A2w-4wCt_i72gTlreclTUSZxXmOEPgtQUIn-3aI9nOvJYHeG5dO_CtFcttP2nZZ2Rqb3VQr-gmPGGV3TAMZ3C-TQRz98T5k-4DSo8qyVXQ8h4weOoIYvnCI-JOq4Dt2tvizRrynUCDPUk0Xd7-drK7PBbDtn3KZBOeR4jNtJop51PZ0D5GTbQd8Ks1-Adnn_261Ge.Xa8Ckw.88nMjVOHNu90gSpkY16da5SMtTA'
            get_mock.return_value = mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'hashed_client_id': client_id}
            account = get_user_info_from_adsws(session)
            self.assertEqual(account['hashed_client_id'], client_id)

    def test_readhist_endpoint_adsws_call_no_session(self):
        """
        Test readhist endpoint adsws call with no session
        """
        with mock.patch.object(self.current_app.client, 'get') as get_mock:
            get_mock.return_value = mock_response = mock.Mock()
            mock_response.status_code = 404
            account = get_user_info_from_adsws('???')
            self.assertEqual(account, None)


    def test_readhist_endpoint_adsws_call_exception(self):
        """
        Test readhist endpoint adsws call directly with no session
        """
        with mock.patch.object(self.current_app.client, 'get') as get_mock:
            get_mock.return_value = mock_response = mock.Mock()
            mock_response.status_code = 500
            mock_response.raiseError.side_effect = Exception('Test')
            account = get_user_info_from_adsws('???')
            self.assertEqual(account, None)

    def test_matchdoc_endpoint(self):
        """
        Tests matchdoc endpoint
        """
        # the mock is for solr call
        with mock.patch.object(self.current_app.client, 'get') as get_mock:
            get_mock.return_value = mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {u'responseHeader': {u'status': 0,
                                                                   u'QTime': 282,
                                                                   u'params': {u'x-amzn-trace-id': u'Root=1-5dc34783-7174b614efe519dc61670d30;-',
                                                                               u'rows': u'2',
                                                                               u'q': u'topn(2, similar("Using Gaussian Process regression to analyze the Martian surface methane Tunable Laser Spectrometer (TLS) data reported by Webster (2018), we find that the TLS data, taken as a whole, are not statistically consistent with seasonal variability. The subset of data derived from an enrichment protocol of TLS, if considered in isolation, are equally consistent with either stochastic processes or periodic variability, but the latter does not favour seasonal variation.", input abstract, 20, 2))',
                                                                               u'start': u'0',
                                                                               u'wt': u'json',
                                                                               u'fl': u'bibcode,abstract,title,author'}},
                                               u'response': {u'start': 0,
                                                             u'numFound': 2,
                                                             u'docs': [{u'title': [u'Statistical analysis of Curiosity data shows no evidence for a strong seasonal cycle of Martian methane'],
                                                                        u'abstract': u'Using Gaussian process regression to analyze the Martian surface methane Tunable Laser Spectrometer (TLS) data reported by Webster et al. (2018), we find that the TLS data, taken as a whole, do not indicate seasonal variability. Enrichment protocol CH<SUB>4</SUB> data are consistent with either stochastic variation or a spread of periods without seasonal preference.',
                                                                        u'bibcode': u'2020Icar..33613407G',
                                                                        u'author': [u'Gillen, Edward', u'Rimmer, Paul B.', u'Catling, David C.']},
                                                                       {u'title': [u'Radiometric Calibration of Tls Intensity: Application to Snow Cover Change Detection'],
                                                                        u'abstract': u'This paper reports on the radiometric calibration and the use of calibrated intensity data in applications related to snow cover monitoring with a terrestrial laser scanner (TLS). An application of the calibration method to seasonal snow cover change detection is investigated. The snow intensity from TLS data was studied in Sodankyl\xe4, Finland during the years 2008-2009 and in Kirkkonummi, Finland in the winter 2010-2011. The results were used to study the behaviour of TLS intensity data on different types of snow and measurement geometry. The results show that the snow type seems to have little or no effect on the incidence angle behaviour of the TLS intensity and that the laser backscatter from the snow surface is not directly related to any of the snow cover properties, but snow structure has a clear effect on TLS intensity.',
                                                                        u'bibcode': u'2011ISPAr3812W.175A',
                                                                        u'author': [u'Anttila, K.', u'Kaasalainen, S.', u'Krooks, A.', u'Kaartinen, H.', u'Kukko, A.', u'Manninen, T.', u'Lahtinen, P.', u'Siljamo, N.']}
                                                                       ]
                                                             }
                                               }
            data = {"abstract":"Using Gaussian Process regression to analyze the Martian surface methane Tunable Laser Spectrometer (TLS) data reported by Webster (2018), we find that the TLS data, taken as a whole, are not statistically consistent with seasonal variability. The subset of data derived from an enrichment protocol of TLS, if considered in isolation, are equally consistent with either stochastic processes or periodic variability, but the latter does not favour seasonal variation.",
                    "title":"Statistical analysis of Curiosity data shows no evidence for a strong seasonal cycle of Martian methane",
                    "author":"Ed Gillen, Paul B Rimmer, David C Catling"}
            r= self.client.post(path='/matchdoc', data=json.dumps(data))
            self.assertEqual(json.loads(r.data)['query'],
                             'topn(2, similar("Using Gaussian Process regression to analyze the Martian surface methane Tunable Laser Spectrometer (TLS) data reported by Webster (2018), we find that the TLS data, taken as a whole, are not statistically consistent with seasonal variability. The subset of data derived from an enrichment protocol of TLS, if considered in isolation, are equally consistent with either stochastic processes or periodic variability, but the latter does not favour seasonal variation.", input abstract, 20, 2))')

if __name__ == "__main__":
    unittest.main()
