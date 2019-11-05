
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

    def test_route_post(self):
        """
        Tests POST endpoint when no optional param passed in, so default is returned
        """
        # the mock is for solr call
        with mock.patch.object(self.current_app.client, 'get'):
            r= self.client.post(path='/readhist', data='{"function":"trending", "reader":"0000000000000000"}')
            self.assertEqual(json.loads(r.data)['query'],
                             "(trending(topn(10, reader:0000000000000000, entry_date desc)) entdate:[NOW-5DAYS TO *])")

    def test_route_get(self):
        """
        Tests GET endpoint with default params
        """
        # the mock is for solr call
        with mock.patch.object(self.current_app.client, 'get'):
            r= self.client.get(path='/readhist/similar/0000000000000000')
            self.assertEqual(json.loads(r.data)['query'],
                             "(similar(topn(10, reader:0000000000000000, entry_date desc)) entdate:[NOW-5DAYS TO *])")

    def test_optional_params_post(self):
        """
        Test optional params with POST
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

    def test_optional_params_get(self):
        """
        Test optional params with GET
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

    def test_route_with_session(self):
        """
        Test with session when adsws is not available
        """
        # the mock is for adsws call
        with mock.patch.object(self.current_app.client, 'get'):
            cookie = 'session=.eJw9j02LgzAYhP_K8p576HbpVoQeCqGiEENdQ9ZcpKtJ_ExLjOtH6X9fEbaHgWFgnmEekEojugJca3qxgbTMwX3A2w-4wCt_i72gTlreclTUSZxXmOEPgtQUIn-3aI9nOvJYHeG5dO_CtFcttP2nZZ2Rqb3VQr-gmPGGV3TAMZ3C-TQRz98T5k-4DSo8qyVXQ8h4weOoIYvnCI-JOq4Dt2tvizRrynUCDPUk0Xd7-drK7PBbDtn3KZBOeR4jNtJop51PZ0D5GTbQd8Ks1-Adnn_261Ge.Xa8Ckw.88nMjVOHNu90gSpkY16da5SMtTA'
            r= self.client.post(path='/readhist', data={'sort': 'date'}, headers={"Cookie": cookie})
            self.assertEqual(r.status_code, 400)
            self.assertEqual(json.loads(r.data)['error'], "unable to obtain reader id")

    def test_no_required_param(self):
        """
        Test when neither reader nor session were passed in
        """
        r= self.client.post(path='/readhist', data=json.dumps({'missingReader':''}))
        self.assertEqual(json.loads(r.data)['error'],
                         "neither reader found in payload (parameter name is `reader`) nor session information received")

    def test_no_data(self):
        """
        Test with no payload
        """
        r= self.client.post(path='/readhist', data=None)
        self.assertEqual(json.loads(r.data)['error'], "no information received")

    def test_adsws_call(self):
        """
        Test adsws call directly with session
        """
        with mock.patch.object(self.current_app.client, 'get') as get_mock:
            client_id = 'aaaaaaaabbbbbbbbccccccccddddddddeeeeeeeeffffffffgggggggghhhhhhhh'
            session = '.eJw9j02LgzAYhP_K8p576HbpVoQeCqGiEENdQ9ZcpKtJ_ExLjOtH6X9fEbaHgWFgnmEekEojugJca3qxgbTMwX3A2w-4wCt_i72gTlreclTUSZxXmOEPgtQUIn-3aI9nOvJYHeG5dO_CtFcttP2nZZ2Rqb3VQr-gmPGGV3TAMZ3C-TQRz98T5k-4DSo8qyVXQ8h4weOoIYvnCI-JOq4Dt2tvizRrynUCDPUk0Xd7-drK7PBbDtn3KZBOeR4jNtJop51PZ0D5GTbQd8Ks1-Adnn_261Ge.Xa8Ckw.88nMjVOHNu90gSpkY16da5SMtTA'
            get_mock.return_value = mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'hashed_client_id': client_id}
            account = get_user_info_from_adsws(session)
            self.assertEqual(account['hashed_client_id'], client_id)

    def test_adsws_call_no_session(self):
        """

        """
        with mock.patch.object(self.current_app.client, 'get') as get_mock:
            get_mock.return_value = mock_response = mock.Mock()
            mock_response.status_code = 404
            account = get_user_info_from_adsws('???')
            self.assertEqual(account, None)


    def test_adsws_call_exception(self):
        """
        Test adsws call directly with no session
        """
        with mock.patch.object(self.current_app.client, 'get') as get_mock:
            get_mock.return_value = mock_response = mock.Mock()
            mock_response.status_code = 500
            mock_response.raiseError.side_effect = Exception('Test')
            account = get_user_info_from_adsws('???')
            self.assertEqual(account, None)

if __name__ == "__main__":
    unittest.main()
