
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
        Tests for the existence of a /oracle/readhist route, and that it returns
        properly formatted JSON data when the URL is supplied
        no param is passed, so default is returned
        """
        r= self.client.post(path='/readhist', data='{"reader":"0000000000000000"}')
        self.assertEqual(json.loads(r.data)['query'],
                         "(similar(topn(10, reader:0000000000000000, entry_date desc)) entdate:[NOW-5DAYS TO *])")

    def test_route_get(self):
        """
        Tests for the existence of a /oracle/readhist route, and that it returns
        properly formatted JSON data when the URL is supplied
        """
        r= self.client.get(path='/readhist/0000000000000000')
        self.assertEqual(json.loads(r.data)['query'],
                         "(similar(topn(10, reader:0000000000000000, entry_date desc)) entdate:[NOW-5DAYS TO *])")

    def test_optional_params(self):
        """
        Pass in optional params
        """
        params = {'reader': '0000000000000000',
                  'sort': 'date',
                  'num_docs': 10,
                  'cutoff_days': 12,
                  'top_n_reads' : 14}
        r= self.client.post(path='/readhist', data=params)
        self.assertEqual(json.loads(r.data)['query'],
                         "(similar(topn(14, reader:0000000000000000, date desc)) entdate:[NOW-12DAYS TO *])")

    def test_route_with_session(self):
        """

        """
        # the mock is for getting the user info
        with mock.patch.object(self.current_app.client, 'get'):
            cookie = 'session=.eJw9j02LgzAYhP_K8p576HbpVoQeCqGiEENdQ9ZcpKtJ_ExLjOtH6X9fEbaHgWFgnmEekEojugJca3qxgbTMwX3A2w-4wCt_i72gTlreclTUSZxXmOEPgtQUIn-3aI9nOvJYHeG5dO_CtFcttP2nZZ2Rqb3VQr-gmPGGV3TAMZ3C-TQRz98T5k-4DSo8qyVXQ8h4weOoIYvnCI-JOq4Dt2tvizRrynUCDPUk0Xd7-drK7PBbDtn3KZBOeR4jNtJop51PZ0D5GTbQd8Ks1-Adnn_261Ge.Xa8Ckw.88nMjVOHNu90gSpkY16da5SMtTA'
            r= self.client.post(path='/readhist', data={'sort': 'date'}, headers={"Cookie": cookie})
            self.assertEqual(r.status_code, 400)
            self.assertEqual(json.loads(r.data)['error'], "unable to obtain reader id")

    def test_no_required_param(self):
        """

        """
        r= self.client.post(path='/readhist', data=json.dumps({'missingReader':''}))
        self.assertEqual(json.loads(r.data)['error'],
                         "neither reader found in payload (parameter name is `reader`) nor session information received")

    def test_no_data(self):
        """

        """
        r= self.client.post(path='/readhist', data=None)
        self.assertEqual(json.loads(r.data)['error'], "no information received")

    def test_adsws_call(self):
        """
        {u'source': u'session:client_id',
         u'hashed_client_id': u'bfa86a9d6510ebaab3fd0016ff352c82e083a415e383b9aeeca87f049ad5c169',
         u'anonymous': True,
         u'hashed_user_id': u'cc4cc6139c6ada12ceca56f8319a29ce9d5ec3565baac572445c7ffbbed6da3b'}
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

        """
        with mock.patch.object(self.current_app.client, 'get') as get_mock:
            get_mock.return_value = mock_response = mock.Mock()
            mock_response.status_code = 500
            mock_response.raiseError.side_effect = Exception('Test')
            account = get_user_info_from_adsws('???')
            self.assertEqual(account, None)

if __name__ == "__main__":
    unittest.main()
