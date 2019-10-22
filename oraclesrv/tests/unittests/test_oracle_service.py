
import sys
import os
PROJECT_HOME = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(PROJECT_HOME)

from flask_testing import TestCase
import unittest
import json
import Cookie


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
        print json.loads(r.data)
        self.assertEqual(json.loads(r.data)['query'],
                         "(similar(topn(10, reader:0000000000000000, entry_date desc)) entdate:[NOW-5DAYS TO *])")
    def test_optional_params(self):
        """

        """
        params = {'reader': '0000000000000000',
                  'sort': 'date',
                  'num_docs': 10,
                  'cutoff_days': 12,
                  'top_n_reads' : 14}
        r= self.client.post(path='/readhist', data=params)
        self.assertEqual(json.loads(r.data)['query'],
                         "(similar(topn(14, reader:[u'0000000000000000'], date desc)) entdate:[NOW-12DAYS TO *])")

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

        """
        session = '.eJw9j02LgzAYhP_K8p576HbpVoQeCqGiEENdQ9ZcpKtJ_ExLjOtH6X9fEbaHgWFgnmEekEojugJca3qxgbTMwX3A2w-4wCt_i72gTlreclTUSZxXmOEPgtQUIn-3aI9nOvJYHeG5dO_CtFcttP2nZZ2Rqb3VQr-gmPGGV3TAMZ3C-TQRz98T5k-4DSo8qyVXQ8h4weOoIYvnCI-JOq4Dt2tvizRrynUCDPUk0Xd7-drK7PBbDtn3KZBOeR4jNtJop51PZ0D5GTbQd8Ks1-Adnn_261Ge.Xa8Ckw.88nMjVOHNu90gSpkY16da5SMtTA'
        account = get_user_info_from_adsws(session)
        # during test it should return None
        self.assertEqual(account, None)

    def test_adsws_call_no_session(self):
        """

        """
        account = get_user_info_from_adsws(None)
        self.assertEqual(account, None)

