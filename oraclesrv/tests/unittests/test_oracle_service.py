# -*- coding: utf-8 -*-
import sys
import os
PROJECT_HOME = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
sys.path.append(PROJECT_HOME)

import unittest
import json
import mock

import oraclesrv.app as app
from oraclesrv.tests.unittests.base import TestCaseDatabase
from oraclesrv.views import get_user_info_from_adsws
from oraclesrv.score import clean_data, get_matches


class test_oracle(TestCaseDatabase):
    def create_app(self):
        self.current_app = app.create_app(**{
            'TESTING': True,
            'SQLALCHEMY_DATABASE_URI': self.postgresql_url,
        })
        return self.current_app

    def test_readhist_endpoint_post(self):
        """
        Tests POST for readhist endpoint when no optional param passed in, so default is returned
        """
        # the mock is for solr call
        with mock.patch.object(self.current_app.client, 'get') as get_mock:
            get_mock.return_value = mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {u'responseHeader': {u'status': 0, u'QTime': 60, u'params': {}},
                                               u'response': {u'start': 0, u'numFound': 0, u'docs': []}
            }
            r= self.client.post(path='/readhist', data='{"function":"trending", "reader":"0000000000000000"}')
            self.assertEqual(json.loads(r.data)['query'],
                             "(trending(topn(10, reader:0000000000000000, entry_date desc)) entdate:[NOW-5DAYS TO *])")

    def test_readhist_endpoint_get(self):
        """
        Tests GET endpoint for readhist endpoint with default params
        """
        # the mock is for solr call
        with mock.patch.object(self.current_app.client, 'get') as get_mock:
            get_mock.return_value = mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {u'responseHeader': {u'status': 0, u'QTime': 60, u'params': {}},
                                               u'response': {u'start': 0, u'numFound': 0, u'docs': []}
            }
            r= self.client.get(path='/readhist/similar/0000000000000000')
            self.assertEqual(json.loads(r.data)['query'],
                             "(similar(topn(10, reader:0000000000000000, entry_date desc)) entdate:[NOW-5DAYS TO *])")

    def test_readhist_endpoint_optional_params_post(self):
        """
        Test optional params with POST for readhist endpoint
        """
        # the mock is for solr call
        with mock.patch.object(self.current_app.client, 'get') as get_mock:
            get_mock.return_value = mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {u'responseHeader': {u'status': 0, u'QTime': 60, u'params': {}},
                                               u'response': {u'start': 0, u'numFound': 0, u'docs': []}
            }
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
        with mock.patch.object(self.current_app.client, 'get') as get_mock:
            get_mock.return_value = mock_response = mock.Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {u'responseHeader': {u'status': 0, u'QTime': 60, u'params': {}},
                                               u'response': {u'start': 0, u'numFound': 0, u'docs': []}
            }
            params = {'sort': 'date',
                      'num_docs': 10,
                      'cutoff_days': 12,
                      'top_n_reads' : 14}
            r= self.client.get(path='/readhist/similar/0000000000000000', query_string=params)
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
        self.assertEqual(json.loads(r.data)['error'], "unable to obtain reader id")

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

    def test_docmatch_endpoint_metadata(self):
        """
        Tests docmatch endpoint using metadata abstract/title to query solr
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
                                                                               u'fl': u'bibcode,abstract,title,author_norm,year,doctype,identifier'}},
                                               u'response': {u'start': 0,
                                                             u'numFound': 1,
                                                             u'docs': [{u'title': [u'Statistical analysis of Curiosity data shows no evidence for a strong seasonal cycle of Martian methane'],
                                                                        u'abstract': u'Using Gaussian process regression to analyze the Martian surface methane Tunable Laser Spectrometer (TLS) data reported by Webster et al. (2018), we find that the TLS data, taken as a whole, do not indicate seasonal variability. Enrichment protocol CH<SUB>4</SUB> data are consistent with either stochastic variation or a spread of periods without seasonal preference.',
                                                                        u'bibcode': u'2020Icar..33613407G',
                                                                        u'author_norm': [u'Gillen, E', u'Rimmer, P', u'Catling, D'],
                                                                        u'year': u'2020',
                                                                        u'doctype': u'article',
                                                                        u'identifier': [u'2019arXiv190802041G', u'2020Icar..33613407G', u'10.1016/j.icarus.2019.113407', u'10.1016/j.icarus.2019.113407', u'arXiv:1908.02041', u'2019arXiv190802041G'],
                                                                        },
                                                                       {u'title': [u'Radiometric Calibration of Tls Intensity: Application to Snow Cover Change Detection'],
                                                                        u'abstract': u'This paper reports on the radiometric calibration and the use of calibrated intensity data in applications related to snow cover monitoring with a terrestrial laser scanner (TLS). An application of the calibration method to seasonal snow cover change detection is investigated. The snow intensity from TLS data was studied in Sodankyl\xe4, Finland during the years 2008-2009 and in Kirkkonummi, Finland in the winter 2010-2011. The results were used to study the behaviour of TLS intensity data on different types of snow and measurement geometry. The results show that the snow type seems to have little or no effect on the incidence angle behaviour of the TLS intensity and that the laser backscatter from the snow surface is not directly related to any of the snow cover properties, but snow structure has a clear effect on TLS intensity.',
                                                                        u'bibcode': u'2011ISPAr3812W.175A',
                                                                        u'author_norm': [u'Anttila, K', u'Kaasalainen, S', u'Krooks, A', u'Kaartinen, H', u'Kukko, A', u'Manninen, T', u'Lahtinen, P', u'Siljamo, N'],
                                                                        u'year': u'2011',
                                                                        u'doctype': u'article',
                                                                        u'identifier': [u'2011ISPAr3812W.175A', u'10.5194/isprsarchives-XXXVIII-5-W12-175-2011', u'10.5194/isprsarchives-XXXVIII-5-W12-175-2011']
                                                                       }]
                                                             }
                                               }
            data = {"bibcode":"2019arXiv190802041G",
                    "abstract":"Using Gaussian Process regression to analyze the Martian surface methane Tunable Laser Spectrometer (TLS) data reported by Webster (2018), we find that the TLS data, taken as a whole, are not statistically consistent with seasonal variability. The subset of data derived from an enrichment protocol of TLS, if considered in isolation, are equally consistent with either stochastic processes or periodic variability, but the latter does not favour seasonal variation.",
                    "title":"Statistical analysis of Curiosity data shows no evidence for a strong seasonal cycle of Martian methane",
                    "author":"Gillen, Ed; Rimmer, Paul B; Catling, David C",
                    "year":"2020",
                    "doctype":"eprint"}
            r= self.client.post(path='/docmatch', data=json.dumps(data))
            result = json.loads(r.data)
            self.assertEqual(result['query'],
                             'topn(10, similar("Using Gaussian Process regression to analyze the Martian surface methane Tunable Laser Spectrometer (TLS) data reported by Webster (2018), we find that the TLS data, taken as a whole, are not statistically consistent with seasonal variability. The subset of data derived from an enrichment protocol of TLS, if considered in isolation, are equally consistent with either stochastic processes or periodic variability, but the latter does not favour seasonal variation.", input abstract, 20, 1, 1)) doctype:(article OR inproceedings OR inbook)')
            self.assertEqual(result['match'],
                             [{'source_bibcode': '2019arXiv190802041G', 'matched_bibcode': '2020Icar..33613407G',
                               'confidence': 0.8766192, 'matched': 1,
                               'scores': {'abstract': 0.9, 'title': 1.0, 'author': 1, 'year': 1}}])

    def test_docmatch_endpoint_no_result_from_solr_metadata(self):
        """
        Tests docmatch endpoint having no result from solr when solr queried with abstract/title
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
                                                                               u'fl': u'bibcode,abstract,title,author_norm,year,doctype,identifier'}},
                                               u'response': {u'start': 0,
                                                             u'numFound': 0}
                                               }
            data = {"bibcode":"2019arXiv190802041G",
                    "abstract":"Using Gaussian Process regression to analyze the Martian surface methane Tunable Laser Spectrometer (TLS) data reported by Webster (2018), we find that the TLS data, taken as a whole, are not statistically consistent with seasonal variability. The subset of data derived from an enrichment protocol of TLS, if considered in isolation, are equally consistent with either stochastic processes or periodic variability, but the latter does not favour seasonal variation.",
                    "title":"Statistical analysis of Curiosity data shows no evidence for a strong seasonal cycle of Martian methane",
                    "author":"Gillen, Ed; Rimmer, Paul B; Catling, David C",
                    "year":"2020",
                    "doctype":"eprint"}
            r= self.client.post(path='/docmatch', data=json.dumps(data))
            result = json.loads(r.data)
            self.assertEqual(result['query'],
                             'topn(10, similar("Statistical analysis of Curiosity data shows no evidence for a strong seasonal cycle of Martian methane", input title, 13, 1, 1)) doctype:(article OR inproceedings OR inbook)')
            self.assertEqual(result['comment'],
                             'No result from solr with Abstract, trying Title. No result from solr with Title.')
            self.assertEqual(result['no match'],
                             'no document was found in solr matching the request.')

    def test_docmatch_endpoint_with_doi_and_collaboration(self):
        """
        Tests docmatch endpoint having doi and being a collaboration
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
                                                                               u'fl': u'bibcode,abstract,title,author_norm,year,doctype,identifier'}},
                                               u'response': {u'start': 0,
                                                             u'numFound': 1,
                                                             u'docs': [{u'bibcode': u'2019JHEP...10..244S',
                                                                        u'title': [u'Search for supersymmetry in proton-proton collisions at 13 TeV in final states with jets and missing transverse momentum'],
                                                                        u'abstract': u'Results are reported from a search for supersymmetric particles in the final state with multiple jets and large missing transverse momentum. The search uses a sample of proton-proton collisions at \u221a{s} = 13 TeV collected with the CMS detector in 2016-2018, corresponding to an integrated luminosity of 137 fb<SUP> -1</SUP>, representing essentially the full LHC Run 2 data sample. The analysis is performed in a four-dimensional search region defined in terms of the number of jets, the number of tagged bottom quark jets, the scalar sum of jet transverse momenta, and the magnitude of the vector sum of jet transverse momenta. No significant excess in the event yield is observed relative to the expected background contributions from standard model processes. Limits on the pair production of gluinos and squarks are obtained in the framework of simplified models for supersymmetric particle production and decay processes. Assuming the lightest supersymmetric particle to be a neutralino, lower limits on the gluino mass as large as 2000 to 2310 GeV are obtained at 95% confidence level, while lower limits on the squark mass as large as 1190 to 1630 GeV are obtained, depending on the production scenario.',
                                                                        u'doctype': u'article',
                                                                        u'doi': [u'10.1007/JHEP10(2019)244'],
                                                                        u'author_norm': [u'Sirunyan, A', u'Tumasyan, A', u'Adam, W', u'Ambrogi, F', u'Bergauer, T', u'Brandstetter, J', u'Dragicevic, M', u'Ero, J', u'Escalante Del Valle, A', u'Flechl, M', u'Fruhwirth, R', u'Jeitler, M', u'Krammer, N', u'Kratschmer, I', u'Liko, D', u'Madlener, T', u'Mikulec, I', u'Rad, N', u'Schieck, J', u'Schofbeck, R', u'Spanring, M', u'Spitzbart, D', u'Waltenberger, W', u'Wulz, C', u'Zarucki, M', u'Drugakov, V', u'Mossolov, V', u'Suarez Gonzalez, J', u'Darwish, M', u'de Wolf, E', u'di Croce, D', u'Janssen, X', u'Lelek, A', u'Pieters, M', u'Rejeb Sfar, H', u'van Haevermaet, H', u'van Mechelen, P', u'van Putte, S', u'van Remortel, N', u'Blekman, F', u'Bols, E', u'Chhibra, S', u"D'Hondt, J", u'de Clercq, J', u'Lontkovskyi, D', u'Lowette, S', u'Marchesini, I', u'Moortgat, S', u'Python, Q', u'Skovpen, K', u'Tavernier, S', u'van Doninck, W', u'van Mulders, P', u'Beghin, D', u'Bilin, B', u'Brun, H', u'Clerbaux, B', u'de Lentdecker, G', u'Delannoy, H', u'Dorney, B', u'Favart, L', u'Grebenyuk, A', u'Kalsi, A', u'Popov, A', u'Postiau, N', u'Starling, E', u'Thomas, L', u'Vander Velde, C', u'Vanlaer, P', u'Vannerom, D', u'Cornelis, T', u'Dobur, D', u'Khvastunov, I', u'Niedziela, M', u'Roskas, C', u'Trocino, D', u'Tytgat, M', u'Verbeke, W', u'Vermassen, B', u'Vit, M', u'Zaganidis, N', u'Bondu, O', u'Bruno, G', u'Caputo, C', u'David, P', u'Delaere, C', u'Delcourt, M', u'Giammanco, A', u'Lemaitre, V', u'Magitteri, A', u'Prisciandaro, J', u'Saggio, A', u'Vidal Marono, M', u'Vischia, P', u'Zobec, J', u'Alves, F', u'Alves, G', u'Correia Silva, G', u'Hensel, C', u'Moraes, A', u'Rebello Teles, P', u'Belchior Batista Das Chagas, E', u'Carvalho, W', u'Chinellato, J', u'Coelho, E', u'da Costa, E', u'da Silveira, G', u'de Jesus Damiao, D', u'de Oliveira Martins, C', u'Fonseca de Souza, S', u'Huertas Guativa, L', u'Malbouisson, H', u'Martins, J', u'Matos Figueiredo, D', u'Medina Jaime, M', u'Melo de Almeida, M', u'Mora Herrera, C', u'Mundim, L', u'Nogima, H', u'Prado da Silva, W', u'Sanchez Rosas, L', u'Santoro, A', u'Sznajder, A', u'Thiel, M', u'Tonelli Manganote, E', u'Torres da Silva de Araujo, F', u'Vilela Pereira, A', u'Bernardes, C', u'Calligaris, L', u'Fernandez Perez Tomei, T', u'Gregores, E', u'Lemos, D', u'Mercadante, P', u'Novaes, S', u'Padula, S', u'Aleksandrov, A', u'Antchev, G', u'Hadjiiska, R', u'Iaydjiev, P', u'Misheva, M', u'Rodozov, M', u'Shopova, M', u'Sultanov, G', u'Bonchev, M', u'Dimitrov, A', u'Ivanov, T', u'Litov, L', u'Pavlov, B', u'Petkov, P', u'Fang, W', u'Gao, X', u'Yuan, L', u'Chen, G', u'Chen, H', u'Chen, M', u'Jiang, C', u'Leggat, D', u'Liao, H', u'Liu, Z', u'Spiezia, A', u'Tao, J', u'Yazgan, E', u'Zhang, H', u'Zhang, S', u'Zhao, J', u'Agapitos, A', u'Ban, Y', u'Chen, G', u'Levin, A', u'Li, J', u'Li, L', u'Li, Q', u'Mao, Y', u'Qian, S', u'Wang, D', u'Wang, Q', u'Ahmad, M', u'Hu, Z', u'Wang, Y', u'Xiao, M', u'Avila, C', u'Cabrera, A', u'Florez, C', u'Gonzalez Hernandez, C', u'Segura Delgado, M', u'Mejia Guisao, J', u'Ruiz Alvarez, J', u'Salazar Gonzalez, C', u'Vanegas Arbelaez, N', u'Giljanovic, D', u'Godinovic, N', u'Lelas, D', u'Puljak, I', u'Sculac, T', u'Antunovic, Z', u'Kovac, M', u'Brigljevic, V', u'Ceci, S', u'Ferencek, D', u'Kadija, K', u'Mesic, B', u'Roguljic, M', u'Starodumov, A', u'Susa, T', u'Ather, M', u'Attikis, A', u'Erodotou, E', u'Ioannou, A', u'Kolosova, M', u'Konstantinou, S', u'Mavromanolakis, G', u'Mousa, J', u'Nicolaou, C', u'Ptochos, F', u'Razis, P', u'Rykaczewski, H', u'Tsiakkouri, D', u'Finger, M', u'Finger, M', u'Kveton, A', u'Tomsa, J', u'Ayala, E', u'Carrera Jarrin, E', u'Abu Zeid, S', u'Khalil, S', u'Bhowmik, S', u'Carvalho Antunes de Oliveira, A', u'Dewanjee, R', u'Ehataht, K', u'Kadastik, M', u'Raidal, M', u'Veelken, C', u'Eerola, P', u'Forthomme, L', u'Kirschenmann, H', u'Osterberg, K', u'Voutilainen, M', u'Garcia, F', u'Havukainen, J', u'Heikkila, J', u'Jarvinen, T', u'Karimaki, V', u'Kim, M', u'Kinnunen, R', u'Lampen, T', u'Lassila-Perini, K', u'Laurila, S', u'Lehti, S', u'Linden, T', u'Luukka, P', u'Maenpaa, T', u'Siikonen, H', u'Tuominen, E', u'Tuominiemi, J', u'Tuuva, T', u'Besancon, M', u'Couderc, F', u'Dejardin, M', u'Denegri, D', u'Fabbro, B', u'Faure, J', u'Ferri, F', u'Ganjour, S', u'Givernaud, A', u'Gras, P', u'Hamel de Monchenault, G', u'Jarry, P', u'Leloup, C', u'Locci, E', u'Malcles, J', u'Rander, J', u'Rosowsky, A', u'Sahin, M', u'Savoy-Navarro, A', u'Titov, M', u'Ahuja, S', u'Amendola, C', u'Beaudette, F', u'Busson, P', u'Charlot, C', u'Diab, B', u'Falmagne, G', u'Granier de Cassagnac, R', u'Kucher, I', u'Lobanov, A', u'Martin Perez, C', u'Nguyen, M', u'Ochando, C', u'Paganini, P', u'Rembser, J', u'Salerno, R', u'Sauvan, J', u'Sirois, Y', u'Zabi, A', u'Zghiche, A', u'Agram, J', u'Andrea, J', u'Bloch, D', u'Bourgatte, G', u'Brom, J', u'Chabert, E', u'Collard, C', u'Conte, E', u'Fontaine, J', u'Gele, D', u'Goerlach, U', u'Jansova, M', u'Le Bihan, A', u'Tonon, N', u'van Hove, P', u'Gadrat, S', u'Beauceron, S', u'Bernet, C', u'Boudoul, G', u'Camen, C', u'Carle, A', u'Chanon, N', u'Chierici, R', u'Contardo, D', u'Depasse, P', u'El Mamouni, H', u'Fay, J', u'Gascon, S', u'Gouzevitch, M', u'Ille, B', u'Jain, S', u'Lagarde, F', u'Laktineh, I', u'Lattaud, H', u'Lesauvage, A', u'Lethuillier, M', u'Mirabito, L', u'Perries, S', u'Sordini, V', u'Torterotot, L', u'Touquet, G', u'Vander Donckt, M', u'Viret, S', u'Khvedelidze, A', u'Tsamalaidze, Z', u'Autermann, C', u'Feld, L', u'Kiesel, M', u'Klein, K', u'Lipinski, M', u'Meuser, D', u'Pauls, A', u'Preuten, M', u'Rauch, M', u'Schulz, J', u'Teroerde, M', u'Wittmer, B', u'Albert, A', u'Erdmann, M', u'Fischer, B', u'Ghosh, S', u'Hebbeker, T', u'Hoepfner, K', u'Keller, H', u'Mastrolorenzo, L', u'Merschmeyer, M', u'Meyer, A', u'Millet, P', u'Mocellin, G', u'Mondal, S', u'Mukherjee, S', u'Noll, D', u'Novak, A', u'Pook, T', u'Pozdnyakov, A', u'Quast, T', u'Radziej, M', u'Rath, Y', u'Reithler, H', u'Roemer, J', u'Schmidt, A', u'Schuler, S', u'Sharma, A', u'Wiedenbeck, S', u'Zaleski, S', u'Flugge, G', u'Haj Ahmad, W', u'Hlushchenko, O', u'Kress, T', u'Muller, T', u'Nehrkorn, A', u'Nowack, A', u'Pistone, C', u'Pooth, O', u'Roy, D', u'Sert, H', u'Stahl, A', u'Aldaya Martin, M', u'Asmuss, P', u'Babounikau, I', u'Bakhshiansohi, H', u'Beernaert, K', u'Behnke, O', u'Bermudez Martinez, A', u'Bertsche, D', u'Bin Anuar, A', u'Borras, K', u'Botta, V', u'Campbell, A', u'Cardini, A', u'Connor, P', u'Consuegra Rodriguez, S', u'Contreras-Campana, C', u'Danilov, V', u'de Wit, A', u'Defranchis, M', u'Diez Pardos, C', u'Dominguez Damiani, D', u'Eckerlin, G', u'Eckstein, D', u'Eichhorn, T', u'Elwood, A', u'Eren, E', u'Gallo, E', u'Geiser, A', u'Grohsjean, A', u'Guthoff, M', u'Haranko, M', u'Harb, A', u'Jafari, A', u'Jomhari, N', u'Jung, H', u'Kasem, A', u'Kasemann, M', u'Kaveh, H', u'Keaveney, J', u'Kleinwort, C', u'Knolle, J', u'Krucker, D', u'Lange, W', u'Lenz, T', u'Lidrych, J', u'Lipka, K', u'Lohmann, W', u'Mankel, R', u'Melzer-Pellmann, I', u'Meyer, A', u'Meyer, M', u'Missiroli, M', u'Mittag, G', u'Mnich, J', u'Mussgiller, A', u'Myronenko, V', u'Perez Adan, D', u'Pflitsch, S', u'Pitzl, D', u'Raspereza, A', u'Saibel, A', u'Savitskyi, M', u'Scheurer, V', u'Schutze, P', u'Schwanenberger, C', u'Shevchenko, R', u'Singh, A', u'Tholen, H', u'Turkot, O', u'Vagnerini, A', u'van de Klundert, M', u'Walsh, R', u'Wen, Y', u'Wichmann, K', u'Wissing, C', u'Zenaiev, O', u'Zlebcik, R', u'Aggleton, R', u'Bein, S', u'Benato, L', u'Benecke, A', u'Blobel, V', u'Dreyer, T', u'Ebrahimi, A', u'Feindt, F', u'Frohlich, A', u'Garbers, C', u'Garutti, E', u'Gonzalez, D', u'Gunnellini, P', u'Haller, J', u'Hinzmann, A', u'Karavdina, A', u'Kasieczka, G', u'Klanner, R', u'Kogler, R', u'Kovalchuk, N', u'Kurz, S', u'Kutzner, V', u'Lange, J', u'Lange, T', u'Malara, A', u'Multhaup, J', u'Niemeyer, C', u'Perieanu, A', u'Reimers, A', u'Rieger, O', u'Scharf, C', u'Schleper, P', u'Schumann, S', u'Schwandt, J', u'Sonneveld, J', u'Stadie, H', u'Steinbruck, G', u'Stober, F', u'Vormwald, B', u'Zoi, I', u'Akbiyik, M', u'Barth, C', u'Baselga, M', u'Baur, S', u'Berger, T', u'Butz, E', u'Caspart, R', u'Chwalek, T', u'de Boer, W', u'Dierlamm, A', u'El Morabit, K', u'Faltermann, N', u'Giffels, M', u'Goldenzweig, P', u'Gottmann, A', u'Harrendorf, M', u'Hartmann, F', u'Husemann, U', u'Kudella, S', u'Mitra, S', u'Mozer, M', u'Muller, D', u'Muller, T', u'Musich, M', u'Nurnberg, A', u'Quast, G', u'Rabbertz, K', u'Schroder, M', u'Shvetsov, I', u'Simonis, H', u'Ulrich, R', u'Wassmer, M', u'Weber, M', u'Wohrmann, C', u'Wolf, R', u'Anagnostou, G', u'Asenov, P', u'Daskalakis, G', u'Geralis, T', u'Kyriakis, A', u'Loukas, D', u'Paspalaki, G', u'Diamantopoulou, M', u'Karathanasis, G', u'Kontaxakis, P', u'Manousakis-Katsikakis, A', u'Panagiotou, A', u'Papavergou, I', u'Saoulidou, N', u'Stakia, A', u'Theofilatos, K', u'Vellidis, K', u'Vourliotis, E', u'Bakas, G', u'Kousouris, K', u'Papakrivopoulos, I', u'Tsipolitis, G', u'Evangelou, I', u'Foudas, C', u'Gianneios, P', u'Katsoulis, P', u'Kokkas, P', u'Mallios, S', u'Manitara, K', u'Manthos, N', u'Papadopoulos, I', u'Strologas, J', u'Triantis, F', u'Tsitsonis, D', u'Bartok, M', u'Chudasama, R', u'Csanad, M', u'Major, P', u'Mandal, K', u'Mehta, A', u'Nagy, M', u'Pasztor, G', u'Suranyi, O', u'Veres, G', u'Bencze, G', u'Hajdu, C', u'Horvath, D', u'Sikler, F', u'Vami, T', u'Veszpremi, V', u'Vesztergombi, G', u'Beni, N', u'Czellar, S', u'Karancsi, J', u'Makovec, A', u'Molnar, J', u'Szillasi, Z', u'Raics, P', u'Teyssier, D', u'Trocsanyi, Z', u'Ujvari, B', u'Csorgo, T', u'Metzger, W', u'Nemes, F', u'Novak, T', u'Choudhury, S', u'Komaragiri, J', u'Tiwari, P', u'Bahinipati, S', u'Kar, C', u'Kole, G', u'Mal, P', u'Mishra, T', u'Muraleedharan Nair Bindhu, V', u'Nayak, A', u'Sahoo, D', u'Swain, S', u'Bansal, S', u'Beri, S', u'Bhatnagar, V', u'Chauhan, S', u'Chawla, R', u'Dhingra, N', u'Gupta, R', u'Kaur, A', u'Kaur, M', u'Kaur, S', u'Kumari, P', u'Lohan, M', u'Meena, M', u'Sandeep, K', u'Sharma, S', u'Singh, J', u'Virdi, A', u'Walia, G', u'Bhardwaj, A', u'Choudhary, B', u'Garg, R', u'Gola, M', u'Keshri, S', u'Kumar, A', u'Naimuddin, M', u'Priyanka, P', u'Ranjan, K', u'Shah, A', u'Sharma, R', u'Bhardwaj, R', u'Bharti, M', u'Bhattacharya, R', u'Bhattacharya, S', u'Bhawandeep, U', u'Bhowmik, D', u'Dutta, S', u'Ghosh, S', u'Maity, M', u'Mondal, K', u'Nandan, S', u'Purohit, A', u'Rout, P', u'Saha, G', u'Sarkar, S', u'Sarkar, T', u'Sharan, M', u'Singh, B', u'Thakur, S', u'Behera, P', u'Kalbhor, P', u'Muhammad, A', u'Pujahari, P', u'Sharma, A', u'Sikdar, A', u'Dutta, D', u'Jha, V', u'Kumar, V', u'Mishra, D', u'Netrakanti, P', u'Pant, L', u'Shukla, P', u'Aziz, T', u'Bhat, M', u'Dugad, S', u'Mohanty, G', u'Sur, N', u'Verma, R', u'Banerjee, S', u'Bhattacharya, S', u'Chatterjee, S', u'Das, P', u'Guchait, M', u'Karmakar, S', u'Kumar, S', u'Majumder, G', u'Mazumdar, K', u'Sahoo, N', u'Sawant, S', u'Chauhan, S', u'Dube, S', u'Hegde, V', u'Kansal, B', u'Kapoor, A', u'Kothekar, K', u'Pandey, S', u'Rane, A', u'Rastogi, A', u'Sharma, S', u'Chenarani, S', u'Eskandari Tadavani, E', u'Etesami, S', u'Khakzad, M', u'Mohammadi Najafabadi, M', u'Naseri, M', u'Rezaei Hosseinabadi, F', u'Felcini, M', u'Grunewald, M', u'Abbrescia, M', u'Aly, R', u'Calabria, C', u'Colaleo, A', u'Creanza, D', u'Cristella, L', u'de Filippis, N', u'de Palma, M', u'di Florio, A', u'Elmetenawee, W', u'Fiore, L', u'Gelmi, A', u'Iaselli, G', u'Ince, M', u'Lezki, S', u'Maggi, G', u'Maggi, M', u'Miniello, G', u'My, S', u'Nuzzo, S', u'Pompili, A', u'Pugliese, G', u'Radogna, R', u'Ranieri, A', u'Selvaggi, G', u'Silvestris, L', u'Simone, F', u'Venditti, R', u'Verwilligen, P', u'Abbiendi, G', u'Battilana, C', u'Bonacorsi, D', u'Borgonovi, L', u'Braibant-Giacomelli, S', u'Campanini, R', u'Capiluppi, P', u'Castro, A', u'Cavallo, F', u'Ciocca, C', u'Codispoti, G', u'Cuffiani, M', u'Dallavalle, G', u'Fabbri, F', u'Fanfani, A', u'Fontanesi, E', u'Giacomelli, P', u'Grandi, C', u'Guiducci, L', u'Iemmi, F', u'Meo, S', u'Marcellini, S', u'Masetti, G', u'Navarria, F', u'Perrotta, A', u'Primavera, F', u'Rossi, A', u'Rovelli, T', u'Siroli, G', u'Tosi, N', u'Albergo, S', u'Costa, S', u'di Mattia, A', u'Potenza, R', u'Tricomi, A', u'Tuve, C', u'Barbagli, G', u'Cassese, A', u'Ceccarelli, R', u'Ciulli, V', u'Civinini, C', u"D'Alessandro, R", u'Focardi, E', u'Latino, G', u'Lenzi, P', u'Meschini, M', u'Paoletti, S', u'Sguazzoni, G', u'Viliani, L', u'Benussi, L', u'Bianco, S', u'Piccolo, D', u'Bozzo, M', u'Ferro, F', u'Mulargia, R', u'Robutti, E', u'Tosi, S', u'Benaglia, A', u'Beschi, A', u'Brivio, F', u'Ciriolo, V', u'di Guida, S', u'Dinardo, M', u'Dini, P', u'Gennai, S', u'Ghezzi, A', u'Govoni, P', u'Guzzi, L', u'Malberti, M', u'Malvezzi, S', u'Menasce, D', u'Monti, F', u'Moroni, L', u'Paganoni, M', u'Pedrini, D', u'Ragazzi, S', u'Tabarelli de Fatis, T', u'Zuolo, D', u'Buontempo, S', u'Cavallo, N', u'de Iorio, A', u'di Crescenzo, A', u'Fabozzi, F', u'Fienga, F', u'Galati, G', u'Iorio, A', u'Lista, L', u'Meola, S', u'Paolucci, P', u'Rossi, B', u'Sciacca, C', u'Voevodina, E', u'Azzi, P', u'Bacchetta, N', u'Bisello, D', u'Boletti, A', u'Bragagnolo, A', u'Carlin, R', u'Checchia, P', u'de Castro Manzano, P', u'Dorigo, T', u'Dosselli, U', u'Gasparini, F', u'Gasparini, U', u'Gozzelino, A', u'Hoh, S', u'Lujan, P', u'Margoni, M', u'Meneguzzo, A', u'Pazzini, J', u'Presilla, M', u'Ronchese, P', u'Rossin, R', u'Simonetto, F', u'Tiko, A', u'Tosi, M', u'Zanetti, M', u'Zotto, P', u'Zumerle, G', u'Braghieri, A', u'Fiorina, D', u'Montagna, P', u'Ratti, S', u'Re, V', u'Ressegotti, M', u'Riccardi, C', u'Salvini, P', u'Vai, I', u'Vitulo, P', u'Biasini, M', u'Bilei, G', u'Ciangottini, D', u'Fano, L', u'Lariccia, P', u'Leonardi, R', u'Manoni, E', u'Mantovani, G', u'Mariani, V', u'Menichelli, M', u'Rossi, A', u'Santocchia, A', u'Spiga, D', u'Androsov, K', u'Azzurri, P', u'Bagliesi, G', u'Bertacchi, V', u'Bianchini, L', u'Boccali, T', u'Castaldi, R', u'Ciocci, M', u"Dell'Orso, R", u'Fedi, G', u'Giannini, L', u'Giassi, A', u'Grippo, M', u'Ligabue, F', u'Manca, E', u'Mandorli, G', u'Messineo, A', u'Palla, F', u'Rizzi, A', u'Rolandi, G', u'Roy Chowdhury, S', u'Scribano, A', u'Spagnolo, P', u'Tenchini, R', u'Tonelli, G', u'Turini, N', u'Venturi, A', u'Verdini, P', u'Cavallari, F', u'Cipriani, M', u'Del Re, D', u'di Marco, E', u'Diemoz, M', u'Longo, E', u'Meridiani, P', u'Organtini, G', u'Pandolfi, F', u'Paramatti, R', u'Quaranta, C', u'Rahatlou, S', u'Rovelli, C', u'Santanastasio, F', u'Soffi, L', u'Amapane, N', u'Arcidiacono, R', u'Argiro, S', u'Arneodo, M', u'Bartosik, N', u'Bellan, R', u'Bellora, A', u'Biino, C', u'Cappati, A', u'Cartiglia, N', u'Cometti, S', u'Costa, M', u'Covarelli, R', u'Demaria, N', u'Kiani, B', u'Mariotti, C', u'Maselli, S', u'Migliore, E', u'Monaco, V', u'Monteil, E', u'Monteno, M', u'Obertino, M', u'Ortona, G', u'Pacher, L', u'Pastrone, N', u'Pelliccioni, M', u'Pinna Angioni, G', u'Romero, A', u'Ruspa, M', u'Salvatico, R', u'Sola, V', u'Solano, A', u'Soldi, D', u'Staiano, A', u'Belforte, S', u'Candelise, V', u'Casarsa, M', u'Cossutti, F', u'da Rold, A', u'Della Ricca, G', u'Vazzoler, F', u'Zanetti, A', u'Kim, B', u'Kim, D', u'Kim, G', u'Lee, J', u'Lee, S', u'Moon, C', u'Oh, Y', u'Pak, S', u'Sekmen, S', u'Son, D', u'Yang, Y', u'Kim, H', u'Moon, D', u'Oh, G', u'Francois, B', u'Kim, T', u'Park, J', u'Cho, S', u'Choi, S', u'Go, Y', u'Gyun, D', u'Ha, S', u'Hong, B', u'Lee, K', u'Lee, K', u'Lim, J', u'Park, J', u'Park, S', u'Roh, Y', u'Yoo, J', u'Goh, J', u'Kim, H', u'Almond, J', u'Bhyun, J', u'Choi, J', u'Jeon, S', u'Kim, J', u'Kim, J', u'Lee, H', u'Lee, K', u'Lee, S', u'Nam, K', u'Oh, M', u'Oh, S', u'Radburn-Smith, B', u'Yang, U', u'Yoo, H', u'Yoon, I', u'Yu, G', u'Jeon, D', u'Kim, H', u'Kim, J', u'Lee, J', u'Park, I', u'Watson, I', u'Choi, Y', u'Hwang, C', u'Jeong, Y', u'Lee, J', u'Lee, Y', u'Yu, I', u'Veckalns, V', u'Dudenas, V', u'Juodagalvis, A', u'Tamulaitis, G', u'Vaitkus, J', u'Ibrahim, Z', u'Mohamad Idris, F', u'Wan Abdullah, W', u'Yusli, M', u'Zolkapli, Z', u'Benitez, J', u'Castaneda Hernandez, A', u'Murillo Quijada, J', u'Valencia Palomo, L', u'Castilla-Valdez, H', u'de La Cruz-Burelo, E', u'Heredia-de La Cruz, I', u'Lopez-Fernandez, R', u'Sanchez-Hernandez, A', u'Carrillo Moreno, S', u'Oropeza Barrera, C', u'Ramirez-Garcia, M', u'Vazquez Valencia, F', u'Eysermans, J', u'Pedraza, I', u'Salazar Ibarguen, H', u'Uribe Estrada, C', u'Morelos Pineda, A', u'Mijuskovic, J', u'Raicevic, N', u'Krofcheck, D', u'Bheesette, S', u'Butler, P', u'Ahmad, A', u'Ahmad, M', u'Hassan, Q', u'Hoorani, H', u'Khan, W', u'Shah, M', u'Shoaib, M', u'Waqas, M', u'Avati, V', u'Grzanka, L', u'Malawski, M', u'Bialkowska, H', u'Bluj, M', u'Boimska, B', u'Gorski, M', u'Kazana, M', u'Szleper, M', u'Zalewski, P', u'Bunkowski, K', u'Byszuk, A', u'Doroba, K', u'Kalinowski, A', u'Konecki, M', u'Krolikowski, J', u'Misiura, M', u'Olszewski, M', u'Walczak, M', u'Araujo, M', u'Bargassa, P', u'Bastos, D', u'di Francesco, A', u'Faccioli, P', u'Galinhas, B', u'Gallinaro, M', u'Hollar, J', u'Leonardo, N', u'Niknejad, T', u'Seixas, J', u'Shchelina, K', u'Strong, G', u'Toldaiev, O', u'Varela, J', u'Afanasiev, S', u'Bunin, P', u'Gavrilenko, M', u'Golutvin, I', u'Gorbunov, I', u'Kamenev, A', u'Karjavine, V', u'Lanev, A', u'Malakhov, A', u'Matveev, V', u'Moisenz, P', u'Palichik, V', u'Perelygin, V', u'Savina, M', u'Shmatov, S', u'Shulha, S', u'Skatchkov, N', u'Smirnov, V', u'Voytishin, N', u'Zarubin, A', u'Chtchipounov, L', u'Golovtcov, V', u'Ivanov, Y', u'Kim, V', u'Kuznetsova, E', u'Levchenko, P', u'Murzin, V', u'Oreshkin, V', u'Smirnov, I', u'Sosnov, D', u'Sulimov, V', u'Uvarov, L', u'Vorobyev, A', u'Andreev, Y', u'Dermenev, A', u'Gninenko, S', u'Golubev, N', u'Karneyeu, A', u'Kirsanov, M', u'Krasnikov, N', u'Pashenkov, A', u'Tlisov, D', u'Toropin, A', u'Epshteyn, V', u'Gavrilov, V', u'Lychkovskaya, N', u'Nikitenko, A', u'Popov, V', u'Pozdnyakov, I', u'Safronov, G', u'Spiridonov, A', u'Stepennov, A', u'Toms, M', u'Vlasov, E', u'Zhokin, A', u'Aushev, T', u'Bychkova, O', u'Chistov, R', u'Danilov, M', u'Polikarpov, S', u'Tarkovskii, E', u'Andreev, V', u'Azarkin, M', u'Dremin, I', u'Kirakosyan, M', u'Terkulov, A', u'Belyaev, A', u'Boos, E', u'Dubinin, M', u'Dudko, L', u'Ershov, A', u'Gribushin, A', u'Klyukhin, V', u'Kodolova, O', u'Lokhtin, I', u'Obraztsov, S', u'Petrushanko, S', u'Savrin, V', u'Snigirev, A', u'Barnyakov, A', u'Blinov, V', u'Dimova, T', u'Kardapoltsev, L', u'Skovpen, Y', u'Azhgirey, I', u'Bayshev, I', u'Bitioukov, S', u'Kachanov, V', u'Konstantinov, D', u'Mandrik, P', u'Petrov, V', u'Ryutin, R', u'Slabospitskii, S', u'Sobol, A', u'Troshin, S', u'Tyurin, N', u'Uzunian, A', u'Volkov, A', u'Babaev, A', u'Iuzhakov, A', u'Okhotnikov, V', u'Borchsh, V', u'Ivanchenko, V', u'Tcherniaev, E', u'Adzic, P', u'Cirkovic, P', u'Devetak, D', u'Dordevic, M', u'Milenovic, P', u'Milosevic, J', u'Stojanovic, M', u'Aguilar-Benitez, M', u'Alcaraz Maestre, J', u'Alvarez Fernandez, A', u'Bachiller, I', u'Barrio Luna, M', u'Brochero Cifuentes, J', u'Carrillo Montoya, C', u'Cepeda, M', u'Cerrada, M', u'Colino, N', u'de La Cruz, B', u'Delgado Peris, A', u'Fernandez Bedoya, C', u'Fernandez Ramos, J', u'Flix, J', u'Fouz, M', u'Gonzalez Lopez, O', u'Goy Lopez, S', u'Hernandez, J', u'Josa, M', u'Moran, D', u'Navarro Tobar, A', u'Perez-Calero Yzquierdo, A', u'Puerta Pelayo, J', u'Redondo, I', u'Romero, L', u'Sanchez Navas, S', u'Soares, M', u'Triossi, A', u'Willmott, C', u'Albajar, C', u'de Troconiz, J', u'Reyes-Almanza, R', u'Alvarez Gonzalez, B', u'Cuevas, J', u'Erice, C', u'Fernandez Menendez, J', u'Folgueras, S', u'Gonzalez Caballero, I', u'Gonzalez Fernandez, J', u'Palencia Cortezon, E', u'Rodriguez Bouza, V', u'Sanchez Cruz, S', u'Cabrillo, I', u'Calderon, A', u'Chazin Quero, B', u'Duarte Campderros, J', u'Fernandez, M', u'Fernandez Manteca, P', u'Garcia Alonso, A', u'Gomez, G', u'Martinez Rivero, C', u'Martinez Ruiz Del Arbol, P', u'Matorras, F', u'Piedra Gomez, J', u'Prieels, C', u'Rodrigo, T', u'Ruiz-Jimeno, A', u'Russo, L', u'Scodellaro, L', u'Trevisani, N', u'Vila, I', u'Vizan Garcia, J', u'Malagalage, K', u'Dharmaratna, W', u'Wickramage, N', u'Abbaneo, D', u'Akgun, B', u'Auffray, E', u'Auzinger, G', u'Baechler, J', u'Baillon, P', u'Ball, A', u'Barney, D', u'Bendavid, J', u'Bianco, M', u'Bocci, A', u'Bortignon, P', u'Bossini, E', u'Botta, C', u'Brondolin, E', u'Camporesi, T', u'Caratelli, A', u'Cerminara, G', u'Chapon, E', u'Cucciati, G', u"D'Enterria, D", u'Dabrowski, A', u'Daci, N', u'Daponte, V', u'David, A', u'Davignon, O', u'de Roeck, A', u'Deile, M', u'Dobson, M', u'Dunser, M', u'Dupont, N', u'Elliott-Peisert, A', u'Emriskova, N', u'Fallavollita, F', u'Fasanella, D', u'Fiorendi, S', u'Franzoni, G', u'Fulcher, J', u'Funk, W', u'Giani, S', u'Gigi, D', u'Gilbert, A', u'Gill, K', u'Glege, F', u'Gruchala, M', u'Guilbaud, M', u'Gulhan, D', u'Hegeman, J', u'Heidegger, C', u'Iiyama, Y', u'Innocente, V', u'Janot, P', u'Karacheban, O', u'Kaspar, J', u'Kieseler, J', u'Krammer, M', u'Kratochwil, N', u'Lange, C', u'Lecoq, P', u'Lourenco, C', u'Malgeri, L', u'Mannelli, M', u'Massironi, A', u'Meijers, F', u'Merlin, J', u'Mersi, S', u'Meschi, E', u'Moortgat, F', u'Mulders, M', u'Ngadiuba, J', u'Niedziela, J', u'Nourbakhsh, S', u'Orfanelli, S', u'Orsini, L', u'Pantaleo, F', u'Pape, L', u'Perez, E', u'Peruzzi, M', u'Petrilli, A', u'Petrucciani, G', u'Pfeiffer, A', u'Pierini, M', u'Pitters, F', u'Rabady, D', u'Racz, A', u'Rieger, M', u'Rovere, M', u'Sakulin, H', u'Schafer, C', u'Schwick, C', u'Selvaggi, M', u'Sharma, A', u'Silva, P', u'Snoeys, W', u'Sphicas, P', u'Steggemann, J', u'Summers, S', u'Tavolaro, V', u'Treille, D', u'Tsirou, A', u'van Onsem, G', u'Vartak, A', u'Verzetti, M', u'Zeuner, W', u'Caminada, L', u'Deiters, K', u'Erdmann, W', u'Horisberger, R', u'Ingram, Q', u'Kaestli, H', u'Kotlinski, D', u'Langenegger, U', u'Rohe, T', u'Wiederkehr, S', u'Backhaus, M', u'Berger, P', u'Chernyavskaya, N', u'Dissertori, G', u'Dittmar, M', u'Donega, M', u'Dorfer, C', u'Gomez Espinosa, T', u'Grab, C', u'Hits, D', u'Klijnsma, T', u'Lustermann, W', u'Manzoni, R', u'Marionneau, M', u'Meinhard, M', u'Micheli, F', u'Musella, P', u'Nessi-Tedaldi, F', u'Pauss, F', u'Perrin, G', u'Perrozzi, L', u'Pigazzini, S', u'Ratti, M', u'Reichmann, M', u'Reissel, C', u'Reitenspiess, T', u'Ruini, D', u'Sanz Becerra, D', u'Schonenberger, M', u'Shchutska, L', u'Vesterbacka Olsson, M', u'Wallny, R', u'Zhu, D', u'Aarrestad, T', u'Amsler, C', u'Brzhechko, D', u'Canelli, M', u'de Cosa, A', u'Del Burgo, R', u'Donato, S', u'Kilminster, B', u'Leontsinis, S', u'Mikuni, V', u'Neutelings, I', u'Rauco, G', u'Robmann, P', u'Salerno, D', u'Schweiger, K', u'Seitz, C', u'Takahashi, Y', u'Wertz, S', u'Zucchetta, A', u'Doan, T', u'Kuo, C', u'Lin, W', u'Roy, A', u'Yu, S', u'Chang, P', u'Chao, Y', u'Chen, K', u'Chen, P', u'Hou, W', u'Li, Y', u'Lu, R', u'Paganis, E', u'Psallidas, A', u'Steen, A', u'Asavapibhop, B', u'Asawatangtrakuldee, C', u'Srimanobhas, N', u'Suwonjandee, N', u'Bat, A', u'Boran, F', u'Celik, A', u'Cerci, S', u'Damarseckin, S', u'Demiroglu, Z', u'Dolek, F', u'Dozen, C', u'Dumanoglu, I', u'Gokbulut, G', u'Guler, E', u'Guler, Y', u'Hos, I', u'Isik, C', u'Kangal, E', u'Kara, O', u'Kayis Topaksu, A', u'Kiminsu, U', u'Onengut, G', u'Ozdemir, K', u'Ozturk, S', u'Simsek, A', u'Sunar Cerci, D', u'Tok, U', u'Turkcapar, S', u'Zorbakir, I', u'Zorbilmez, C', u'Isildak, B', u'Karapinar, G', u'Yalvac, M', u'Atakisi, I', u'Gulmez, E', u'Kaya, M', u'Kaya, O', u'Ozcelik, O', u'Tekten, S', u'Yetkin, E', u'Cakir, A', u'Cankocak, K', u'Komurcu, Y', u'Sen, S', u'Kaynak, B', u'Ozkorucuklu, S', u'Grynyov, B', u'Levchuk, L', u'Bhal, E', u'Bologna, S', u'Brooke, J', u'Burns, D', u'Clement, E', u'Cussans, D', u'Flacher, H', u'Goldstein, J', u'Heath, G', u'Heath, H', u'Kreczko, L', u'Paramesvaran, S', u'Penning, B', u'Sakuma, T', u'Seif El Nasr-Storey, S', u'Smith, V', u'Taylor, J', u'Titterton, A', u'Bell, K', u'Belyaev, A', u'Brew, C', u'Brown, R', u'Cieri, D', u'Cockerill, D', u'Coughlan, J', u'Harder, K', u'Harper, S', u'Linacre, J', u'Manolopoulos, K', u'Newbold, D', u'Olaiya, E', u'Petyt, D', u'Reis, T', u'Schuh, T', u'Shepherd-Themistocleous, C', u'Thea, A', u'Tomalin, I', u'Williams, T', u'Womersley, W', u'Bainbridge, R', u'Bloch, P', u'Borg, J', u'Breeze, S', u'Buchmuller, O', u'Bundock, A', u'Chahal, G', u'Colling, D', u'Dauncey, P', u'Davies, G', u'Della Negra, M', u'di Maria, R', u'Everaerts, P', u'Hall, G', u'Iles, G', u'James, T', u'Komm, M', u'Laner, C', u'Lyons, L', u'Magnan, A', u'Malik, S', u'Martelli, A', u'Milosevic, V', u'Nash, J', u'Palladino, V', u'Pesaresi, M', u'Raymond, D', u'Richards, A', u'Rose, A', u'Scott, E', u'Seez, C', u'Shtipliyski, A', u'Stoye, M', u'Strebler, T', u'Tapper, A', u'Uchida, K', u'Virdee, T', u'Wardle, N', u'Winterbottom, D', u'Wright, J', u'Zecchinelli, A', u'Zenz, S', u'Cole, J', u'Hobson, P', u'Khan, A', u'Kyberd, P', u'Mackay, C', u'Morton, A', u'Reid, I', u'Teodorescu, L', u'Zahid, S', u'Call, K', u'Caraway, B', u'Dittmann, J', u'Hatakeyama, K', u'Madrid, C', u'McMaster, B', u'Pastika, N', u'Smith, C', u'Bartek, R', u'Dominguez, A', u'Uniyal, R', u'Vargas Hernandez, A', u'Buccilli, A', u'Cooper, S', u'Henderson, C', u'Rumerio, P', u'West, C', u'Arcaro, D', u'Demiragli, Z', u'Gastler, D', u'Richardson, C', u'Rohlf, J', u'Sperka, D', u'Suarez, I', u'Sulak, L', u'Zou, D', u'Benelli, G', u'Burkle, B', u'Coubez, X', u'Cutts, D', u'Duh, Y', u'Hadley, M', u'Hakala, J', u'Heintz, U', u'Hogan, J', u'Kwok, K', u'Laird, E', u'Landsberg, G', u'Lee, J', u'Mao, Z', u'Narain, M', u'Sagir, S', u'Syarif, R', u'Usai, E', u'Yu, D', u'Zhang, W', u'Band, R', u'Brainerd, C', u'Breedon, R', u'Calderon de La Barca Sanchez, M', u'Chertok, M', u'Conway, J', u'Conway, R', u'Cox, P', u'Erbacher, R', u'Flores, C', u'Funk, G', u'Jensen, F', u'Ko, W', u'Kukral, O', u'Lander, R', u'Mulhearn, M', u'Pellett, D', u'Pilot, J', u'Shi, M', u'Taylor, D', u'Tos, K', u'Tripathi, M', u'Wang, Z', u'Zhang, F', u'Bachtis, M', u'Bravo, C', u'Cousins, R', u'Dasgupta, A', u'Florent, A', u'Hauser, J', u'Ignatenko, M', u'McColl, N', u'Nash, W', u'Regnard, S', u'Saltzberg, D', u'Schnaible, C', u'Stone, B', u'Valuev, V', u'Burt, K', u'Chen, Y', u'Clare, R', u'Gary, J', u'Ghiasi Shirazi, S', u'Hanson, G', u'Karapostoli, G', u'Kennedy, E', u'Long, O', u'Olmedo Negrete, M', u'Paneva, M', u'Si, W', u'Wang, L', u'Wimpenny, S', u'Yates, B', u'Zhang, Y', u'Branson, J', u'Chang, P', u'Cittolin, S', u'Cooperstein, S', u'Deelen, N', u'Derdzinski, M', u'Gerosa, R', u'Gilbert, D', u'Hashemi, B', u'Klein, D', u'Krutelyov, V', u'Letts, J', u'Masciovecchio, M', u'May, S', u'Padhi, S', u'Pieri, M', u'Sharma, V', u'Tadel, M', u'Wurthwein, F', u'Yagil, A', u'Zevi Della Porta, G', u'Amin, N', u'Bhandari, R', u'Campagnari, C', u'Citron, M', u'Dutta, V', u'Franco Sevilla, M', u'Gouskos, L', u'Incandela, J', u'Marsh, B', u'Mei, H', u'Ovcharova, A', u'Qu, H', u'Richman, J', u'Sarica, U', u'Stuart, D', u'Wang, S', u'Anderson, D', u'Bornheim, A', u'Cerri, O', u'Dutta, I', u'Lawhorn, J', u'Lu, N', u'Mao, J', u'Newman, H', u'Nguyen, T', u'Pata, J', u'Spiropulu, M', u'Vlimant, J', u'Xie, S', u'Zhang, Z', u'Zhu, R', u'Andrews, M', u'Ferguson, T', u'Mudholkar, T', u'Paulini, M', u'Sun, M', u'Vorobiev, I', u'Weinberg, M', u'Cumalat, J', u'Ford, W', u'Johnson, A', u'MacDonald, E', u'Mulholland, T', u'Patel, R', u'Perloff, A', u'Stenson, K', u'Ulmer, K', u'Wagner, S', u'Alexander, J', u'Chaves, J', u'Cheng, Y', u'Chu, J', u'Datta, A', u'Frankenthal, A', u'McDermott, K', u'Patterson, J', u'Quach, D', u'Rinkevicius, A', u'Ryd, A', u'Tan, S', u'Tao, Z', u'Thom, J', u'Wittich, P', u'Zientek, M', u'Abdullin, S', u'Albrow, M', u'Alyari, M', u'Apollinari, G', u'Apresyan, A', u'Apyan, A', u'Banerjee, S', u'Bauerdick, L', u'Beretvas, A', u'Berry, D', u'Berryhill, J', u'Bhat, P', u'Burkett, K', u'Butler, J', u'Canepa, A', u'Cerati, G', u'Cheung, H', u'Chlebana, F', u'Cremonesi, M', u'Duarte, J', u'Elvira, V', u'Freeman, J', u'Gecse, Z', u'Gottschalk, E', u'Gray, L', u'Green, D', u'Grunendahl, S', u'Gutsche, O', u'Hall, A', u'Hanlon, J', u'Harris, R', u'Hasegawa, S', u'Heller, R', u'Hirschauer, J', u'Jayatilaka, B', u'Jindariani, S', u'Johnson, M', u'Joshi, U', u'Klima, B', u'Kortelainen, M', u'Kreis, B', u'Lammel, S', u'Lewis, J', u'Lincoln, D', u'Lipton, R', u'Liu, M', u'Liu, T', u'Lykken, J', u'Maeshima, K', u'Marraffino, J', u'Mason, D', u'McBride, P', u'Merkel, P', u'Mrenna, S', u'Nahn, S', u"O'Dell, V", u'Papadimitriou, V', u'Pedro, K', u'Pena, C', u'Rakness, G', u'Ravera, F', u'Ristori, L', u'Schneider, B', u'Sexton-Kennedy, E', u'Smith, N', u'Soha, A', u'Spalding, W', u'Spiegel, L', u'Stoynev, S', u'Strait, J', u'Strobbe, N', u'Taylor, L', u'Tkaczyk, S', u'Tran, N', u'Uplegger, L', u'Vaandering, E', u'Vernieri, C', u'Vidal, R', u'Wang, M', u'Weber, H', u'Acosta, D', u'Avery, P', u'Bourilkov, D', u'Brinkerhoff, A', u'Cadamuro, L', u'Carnes, A', u'Cherepanov, V', u'Errico, F', u'Field, R', u'Gleyzer, S', u'Joshi, B', u'Kim, M', u'Konigsberg, J', u'Korytov, A', u'Lo, K', u'Ma, P', u'Matchev, K', u'Menendez, N', u'Mitselmakher, G', u'Rosenzweig, D', u'Shi, K', u'Wang, J', u'Wang, S', u'Zuo, X', u'Joshi, Y', u'Adams, T', u'Askew, A', u'Hagopian, S', u'Hagopian, V', u'Johnson, K', u'Khurana, R', u'Kolberg, T', u'Martinez, G', u'Perry, T', u'Prosper, H', u'Schiber, C', u'Yohay, R', u'Zhang, J', u'Baarmand, M', u'Hohlmann, M', u'Noonan, D', u'Rahmani, M', u'Saunders, M', u'Yumiceva, F', u'Adams, M', u'Apanasevich, L', u'Betts, R', u'Cavanaugh, R', u'Chen, X', u'Dittmer, S', u'Evdokimov, O', u'Gerber, C', u'Hangal, D', u'Hofman, D', u'Jung, K', u'Mills, C', u'Roy, T', u'Tonjes, M', u'Varelas, N', u'Viinikainen, J', u'Wang, H', u'Wang, X', u'Wu, Z', u'Alhusseini, M', u'Bilki, B', u'Clarida, W', u'Dilsiz, K', u'Durgut, S', u'Gandrajula, R', u'Haytmyradov, M', u'Khristenko, V', u'Koseyan, O', u'Merlo, J', u'Mestvirishvili, A', u'Moeller, A', u'Nachtman, J', u'Ogul, H', u'Onel, Y', u'Ozok, F', u'Penzo, A', u'Snyder, C', u'Tiras, E', u'Wetzel, J', u'Blumenfeld, B', u'Cocoros, A', u'Eminizer, N', u'Gritsan, A', u'Hung, W', u'Kyriacou, S', u'Maksimovic, P', u'Roskes, J', u'Swartz, M', u'Baldenegro Barrera, C', u'Baringer, P', u'Bean, A', u'Boren, S', u'Bowen, J', u'Bylinkin, A', u'Isidori, T', u'Khalil, S', u'King, J', u'Krintiras, G', u'Kropivnitskaya, A', u'Lindsey, C', u'Majumder, D', u'McBrayer, W', u'Minafra, N', u'Murray, M', u'Rogan, C', u'Royon, C', u'Sanders, S', u'Schmitz, E', u'Tapia Takaki, J', u'Wang, Q', u'Williams, J', u'Wilson, G', u'Duric, S', u'Ivanov, A', u'Kaadze, K', u'Kim, D', u'Maravin, Y', u'Mendis, D', u'Mitchell, T', u'Modak, A', u'Mohammadi, A', u'Rebassoo, F', u'Wright, D', u'Baden, A', u'Baron, O', u'Belloni, A', u'Eno, S', u'Feng, Y', u'Hadley, N', u'Jabeen, S', u'Jeng, G', u'Kellogg, R', u'Kunkle, J', u'Mignerey, A', u'Nabili, S', u'Ricci-Tam, F', u'Seidel, M', u'Shin, Y', u'Skuja, A', u'Tonwar, S', u'Wong, K', u'Abercrombie, D', u'Allen, B', u'Baty, A', u'Bi, R', u'Brandt, S', u'Busza, W', u'Cali, I', u"D'Alfonso, M", u'Gomez Ceballos, G', u'Goncharov, M', u'Harris, P', u'Hsu, D', u'Hu, M', u'Klute, M', u'Kovalskyi, D', u'Lee, Y', u'Luckey, P', u'Maier, B', u'Marini, A', u'McGinn, C', u'Mironov, C', u'Narayanan, S', u'Niu, X', u'Paus, C', u'Rankin, D', u'Roland, C', u'Roland, G', u'Shi, Z', u'Stephans, G', u'Sumorok, K', u'Tatar, K', u'Velicanu, D', u'Wang, J', u'Wang, T', u'Wyslouch, B', u'Chatterjee, R', u'Evans, A', u'Guts, S', u'Hansen, P', u'Hiltbrand, J', u'Kubota, Y', u'Lesko, Z', u'Mans, J', u'Rusack, R', u'Wadud, M', u'Acosta, J', u'Oliveros, S', u'Bloom, K', u'Claes, D', u'Fangmeier, C', u'Finco, L', u'Golf, F', u'Kamalieddin, R', u'Kravchenko, I', u'Siado, J', u'Snow, G', u'Stieger, B', u'Tabb, W', u'Agarwal, G', u'Harrington, C', u'Iashvili, I', u'Kharchilava, A', u'McLean, C', u'Nguyen, D', u'Parker, A', u'Pekkanen, J', u'Rappoccio, S', u'Roozbahani, B', u'Alverson, G', u'Barberis, E', u'Freer, C', u'Haddad, Y', u'Hortiangtham, A', u'Madigan, G', u'Marzocchi, B', u'Morse, D', u'Orimoto, T', u'Skinnari, L', u'Tishelman-Charny, A', u'Wamorkar, T', u'Wang, B', u'Wisecarver, A', u'Wood, D', u'Bhattacharya, S', u'Bueghly, J', u'Gunter, T', u'Hahn, K', u'Odell, N', u'Schmitt, M', u'Sung, K', u'Trovato, M', u'Velasco, M', u'Bucci, R', u'Dev, N', u'Goldouzian, R', u'Hildreth, M', u'Hurtado Anampa, K', u'Jessop, C', u'Karmgard, D', u'Lannon, K', u'Li, W', u'Loukas, N', u'Marinelli, N', u'McAlister, I', u'Meng, F', u'Mueller, C', u'Musienko, Y', u'Planer, M', u'Ruchti, R', u'Siddireddy, P', u'Smith, G', u'Taroni, S', u'Wayne, M', u'Wightman, A', u'Wolf, M', u'Woodard, A', u'Alimena, J', u'Bylsma, B', u'Durkin, L', u'Flowers, S', u'Francis, B', u'Hill, C', u'Ji, W', u'Lefeld, A', u'Ling, T', u'Winer, B', u'Dezoort, G', u'Elmer, P', u'Hardenbrook, J', u'Haubrich, N', u'Higginbotham, S', u'Kalogeropoulos, A', u'Kwan, S', u'Lange, D', u'Lucchini, M', u'Luo, J', u'Marlow, D', u'Mei, K', u'Ojalvo, I', u'Olsen, J', u'Palmer, C', u'Piroue, P', u'Salfeld-Nebgen, J', u'Stickland, D', u'Tully, C', u'Wang, Z', u'Malik, S', u'Norberg, S', u'Barker, A', u'Barnes, V', u'Das, S', u'Gutay, L', u'Jones, M', u'Jung, A', u'Khatiwada, A', u'Mahakud, B', u'Miller, D', u'Negro, G', u'Neumeister, N', u'Peng, C', u'Piperov, S', u'Qiu, H', u'Schulte, J', u'Sun, J', u'Wang, F', u'Xiao, R', u'Xie, W', u'Cheng, T', u'Dolen, J', u'Parashar, N', u'Behrens, U', u'Ecklund, K', u'Freed, S', u'Geurts, F', u'Kilpatrick, M', u'Kumar, A', u'Li, W', u'Padley, B', u'Redjimi, R', u'Roberts, J', u'Rorie, J', u'Shi, W', u'Stahl Leiton, A', u'Tu, Z', u'Zhang, A', u'Bodek, A', u'de Barbaro, P', u'Demina, R', u'Dulemba, J', u'Fallon, C', u'Ferbel, T', u'Galanti, M', u'Garcia-Bellido, A', u'Hindrichs, O', u'Khukhunaishvili, A', u'Ranken, E', u'Taus, R', u'Chiarito, B', u'Chou, J', u'Gandrakota, A', u'Gershtein, Y', u'Halkiadakis, E', u'Hart, A', u'Heindl, M', u'Hughes, E', u'Kaplan, S', u'Laflotte, I', u'Lath, A', u'Montalvo, R', u'Nash, K', u'Osherson, M', u'Saka, H', u'Salur, S', u'Schnetzer, S', u'Somalwar, S', u'Stone, R', u'Thomas, S', u'Acharya, H', u'Delannoy, A', u'Riley, G', u'Spanier, S', u'Bouhali, O', u'Dalchenko, M', u'de Mattia, M', u'Delgado, A', u'Dildick, S', u'Eusebi, R', u'Gilmore, J', u'Huang, T', u'Kamon, T', u'Luo, S', u'Malhotra, S', u'Marley, D', u'Mueller, R', u'Overton, D', u'Pernie, L', u'Rathjens, D', u'Safonov, A', u'Akchurin, N', u'Damgov, J', u'de Guio, F', u'Kunori, S', u'Lamichhane, K', u'Lee, S', u'Mengke, T', u'Muthumuni, S', u'Peltola, T', u'Undleeb, S', u'Volobouev, I', u'Wang, Z', u'Whitbeck, A', u'Greene, S', u'Gurrola, A', u'Janjam, R', u'Johns, W', u'Maguire, C', u'Melo, A', u'Ni, H', u'Padeken, K', u'Romeo, F', u'Sheldon, P', u'Tuo, S', u'Velkovska, J', u'Verweij, M', u'Arenton, M', u'Barria, P', u'Cox, B', u'Cummings, G', u'Hirosky, R', u'Joyce, M', u'Ledovskoy, A', u'Neu, C', u'Tannenwald, B', u'Wang, Y', u'Wolfe, E', u'Xia, F', u'Harr, R', u'Karchin, P', u'Poudyal, N', u'Sturdy, J', u'Thapa, P', u'Bose, T', u'Buchanan, J', u'Caillol, C', u'Carlsmith, D', u'Dasu, S', u'de Bruyn, I', u'Dodd, L', u'Fiori, F', u'Galloni, C', u'Gomber, B', u'He, H', u'Herndon, M', u'Herve, A', u'Hussain, U', u'Klabbers, P', u'Lanaro, A', u'Loeliger, A', u'Long, K', u'Loveless, R', u'Madhusudanan Sreekala, J', u'Pinna, D', u'Ruggles, T', u'Savin, A', u'Sharma, V', u'Smith, W', u'Teague, D', u'Trembath-Reichert, S', u'Woods, N', u'CMS Collaboration'],
                                                                        u'year': u'2019',
                                                                        u'identifier': [u'2019JHEP...10..244S', u'10.1007/JHEP10(2019)244', u'10.1007/JHEP10(2019)244']}]
                                                             }
                                               }
            data = {"bibcode": "2019arXiv190804722C",
                    "abstract": "Results are reported from a search for supersymmetric particles in the final\nstate with multiple jets and large missing transverse momentum. The search uses\na sample of proton-proton collisions at $\\sqrt{s} =$ 13 TeV collected with the\nCMS detector in 2016-2018, corresponding to an integrated luminosity of 137\nfb$^{-1}$, representing essentially the full LHC Run 2 data sample. The\nanalysis is performed in a four-dimensional search region defined in terms of\nthe number of jets, the number of tagged bottom quark jets, the scalar sum of\njet transverse momenta, and the magnitude of the vector sum of jet transverse\nmomenta. No significant excess in the event yield is observed relative to the\nexpected background contributions from standard model processes. Limits on the\npair production of gluinos and squarks are obtained in the framework of\nsimplified models for supersymmetric particle production and decay processes.\nAssuming the lightest supersymmetric particle to be a neutralino, lower limits\non the gluino mass as large as 2000 to 2310 GeV are obtained at 95% confidence\nlevel, while lower limits on the squark mass as large as 1190 to 1630 GeV are\nobtained, depending on the production scenario.",
                    "title": "Search for supersymmetry in proton-proton collisions at 13 TeV in final\n  states with jets and missing transverse momentum",
                    "author": "CMS Collaboration",
                    "year": "2019",
                    "doi": ["10.1007/JHEP10(2019)244"],
                    "doctype":"eprint"}
            r= self.client.post(path='/docmatch', data=json.dumps(data))
            result = json.loads(r.data)
            # since some records do not have REFEREED removed this filter for now from the doi query
            # 'doi:"10.1007/JHEP10(2019)244" doctype:(article OR inproceedings OR inbook) property:REFEREED'
            # also remove doctype for now
            self.assertEqual(result['query'],
                             'identifier:("10.1007/JHEP10(2019)244")')
            self.assertEqual(result['match'],
                             [{'source_bibcode': '2019arXiv190804722C', 'matched_bibcode': '2019JHEP...10..244S',
                               'confidence': 0.8865355, 'matched': 1,
                               'scores': {'abstract': 0.94, 'title': 0.99, 'author': 0.3, 'year': 1, 'doi': 1}}])

    def test_docmatch_endpoint_with_doi_not_matching(self):
        """
        Tests docmatch endpoint having erroneous doi
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
                                                                               u'fl': u'bibcode,abstract,title,author_norm,year,doctype,identifier,doi'}},
                                               u'response': {u'start': 0,
                                                             u'numFound': 1,
                                                             u'docs': [{u'identifier':[u'2019arXiv190500882A', u'2019JHEP...06..121A', u'10.1007/JHEP06(2019)121', u'10.1007/JHEP06(2019)121', u'arXiv:1905.00882', u'2019arXiv190500882A'],
                                                                        u'abstract':u"We describe in detail the implementation of a systematic perturbative approach to observables in the QCD gradient-flow formalism. This includes a collection of all relevant Feynman rules of the five-dimensional field theory and the composite operators considered in this paper. Tools from standard perturbative calculations are used to obtain Green's functions at finite flow time t at higher orders in perturbation theory. The three-loop results for the quark condensate at finite t and the conversion factor for the \"ringed\" quark fields to the \\overline{MS} scheme are presented as applications. We also re-evaluate an earlier result for the three-loop gluon condensate, improving on its accuracy.",
                                                                        u'year':u'2019',
                                                                        u'bibcode':u'2019JHEP...06..121A',
                                                                        u'doctype':u'article',
                                                                        u'doi': [u'10.1007/JHEP06(2019)121'],
                                                                        u'title':[u'Results and techniques for higher order calculations within the gradient-flow formalism'],
                                                                        u'author_norm':[u'Artz, J', u'Harlander, R', u'Lange, F', u'Neumann, T', u'Prausa, M']}],
                                                             }
                                               }
            data = {"bibcode": "2019arXiv190500882A",
                    "abstract": 'We describe in detail the implementation of a systematic perturbative\napproach to observables in the QCD gradient-flow formalism. This includes a\ncollection of all relevant Feynman rules of the five-dimensional field theory\nand the composite operators considered in this paper. Tools from standard\nperturbative calculations are used to obtain Green\'s functions at finite flow\ntime $t$ at higher orders in perturbation theory. The three-loop results for\nthe quark condensate at finite $t$ and the conversion factor for the "ringed"\nquark fields to the $\\overline{\\mbox{MS}}$ scheme are presented as\napplications. We also re-evaluate an earlier result for the three-loop gluon\ncondensate, improving on its accuracy.',
                    "title": "Results and techniques for higher order calculations within the\n  gradient-flow formalism",
                    "author": "Artz, Johannes; Harlander, Robert V.; Lange, Fabian; Neumann, Tobias; Prausa, Mario",
                    "year": "2019",
                    "doi": ["10.1007/JHEP06(2019)121"],
                    "doctype":"eprint"}
            r= self.client.post(path='/docmatch', data=json.dumps(data))
            result = json.loads(r.data)
            self.assertEqual(result['query'],
                             'identifier:("10.1007/JHEP06(2019)121")')
            self.assertEqual(result['match'],
                             [{'source_bibcode': '2019arXiv190500882A', 'matched_bibcode': '2019JHEP...06..121A',
                               'confidence': 0.8960806, 'matched': 1,
                               'scores': {'abstract': 0.92, 'title': 0.99, 'author': 1, 'year': 1, 'doi': 1}}])

    def test_docmatch_endpoint_with_accented_author(self):
        """
        Tests docmatch endpoint having accented author
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
                                                                               u'fl': u'bibcode,abstract,title,author_norm,year,doctype,identifier'}},
                                               u'response': {u'start': 0,
                                                             u'numFound': 1,
                                                             u'docs': [{u'identifier': [u'2017arXiv171011147R', u'2018Natur.556..473R', u'10.1038/s41586-018-0036-z', u'arXiv:1710.11147', u'2017arXiv171011147R', u'10.1038/s41586-018-0036-z'],
                                                                        u'abstract': u'Entanglement, an essential feature of quantum theory that allows for inseparable quantum correlations to be shared between distant parties, is a crucial resource for quantum networks<SUP>1</SUP>. Of particular importance is the ability to distribute entanglement between remote objects that can also serve as quantum memories. This has been previously realized using systems such as warm<SUP>2,3</SUP> and cold atomic vapours<SUP>4,5</SUP>, individual atoms<SUP>6</SUP> and ions<SUP>7,8</SUP>, and defects in solid-state systems<SUP>9-11</SUP>. Practical communication applications require a combination of several advantageous features, such as a particular operating wavelength, high bandwidth and long memory lifetimes. Here we introduce a purely micromachined solid-state platform in the form of chip-based optomechanical resonators made of nanostructured silicon beams. We create and demonstrate entanglement between two micromechanical oscillators across two chips that are separated by 20 centimetres . The entangled quantum state is distributed by an optical field at a designed wavelength near 1,550 nanometres. Therefore, our system can be directly incorporated in a realistic fibre-optic quantum network operating in the conventional optical telecommunication band. Our results are an important step towards the development of large-area quantum networks based on silicon photonics.',
                                                                        u'year': u'2018',
                                                                        u'bibcode': u'2018Natur.556..473R',
                                                                        u'doctype': u'article',
                                                                        u'title': [u'Remote quantum entanglement between two micromechanical oscillators'],
                                                                        u'author_norm': [u'Riedinger, R', u'Wallucks, A', u'Marinkovic,', u', Igor', u'Loschnauer, C', u'Aspelmeyer, M', u'Hong, S', u'Groblacher, S']}]
                                                             }
                                               }
            data = {"bibcode": "2017arXiv171011147R",
                    "abstract": "Entanglement, an essential feature of quantum theory that allows for\ninseparable quantum correlations to be shared between distant parties, is a\ncrucial resource for quantum networks. Of particular importance is the ability\nto distribute entanglement between remote objects that can also serve as\nquantum memories. This has been previously realized using systems such as warm\nand cold atomic vapours, individual atoms and ions, and defects in solid-state\nsystems. Practical communication applications require a combination of several\nadvantageous features, such as a particular operating wavelength, high\nbandwidth and long memory lifetimes. Here we introduce a purely micromachined\nsolid-state platform in the form of chip-based optomechanical resonators made\nof nanostructured silicon beams. We create and demonstrate entanglement between\ntwo micromechanical oscillators across two chips that are separated by 20\ncentimetres. The entangled quantum state is distributed by an optical field at\na designed wavelength near 1550 nanometres. Therefore, our system can be\ndirectly incorporated in a realistic fibre-optic quantum network operating in\nthe conventional optical telecommunication band. Our results are an important\nstep towards the development of large-area quantum networks based on silicon\nphotonics.",
                    "title": "Remote quantum entanglement between two micromechanical oscillators",
                    "author": u"Riedinger, Ralf; Wallucks, Andreas; Marinkovic, Igor; L\xf6schnauer, Clemens; Aspelmeyer, Markus; Hong, Sungkun; Gr\xf6blacher, Simon",
                    "year": "2017",
                    "doctype":"eprint"}
            r= self.client.post(path='/docmatch', data=json.dumps(data))
            result = json.loads(r.data)
            self.assertEqual(result['query'],
                             'topn(10, similar("Entanglement, an essential feature of quantum theory that allows forinseparable quantum correlations to be shared between distant parties, is acrucial resource for quantum networks. Of particular importance is the abilityto distribute entanglement between remote objects that can also serve asquantum memories. This has been previously realized using systems such as warmand cold atomic vapours, individual atoms and ions, and defects in solid-statesystems. Practical communication applications require a combination of severaladvantageous features, such as a particular operating wavelength, highbandwidth and long memory lifetimes. Here we introduce a purely micromachinedsolid-state platform in the form of chip-based optomechanical resonators madeof nanostructured silicon beams. We create and demonstrate entanglement betweentwo micromechanical oscillators across two chips that are separated by 20centimetres. The entangled quantum state is distributed by an optical field ata designed wavelength near 1550 nanometres. Therefore, our system can bedirectly incorporated in a realistic fibre-optic quantum network operating inthe conventional optical telecommunication band. Our results are an importantstep towards the development of large-area quantum networks based on siliconphotonics.", input abstract, 49, 1, 1)) doctype:(article OR inproceedings OR inbook)')
            self.assertEqual(result['match'],
                             [{'source_bibcode': '2017arXiv171011147R', 'matched_bibcode': '2018Natur.556..473R',
                               'confidence': 0.8745491, 'matched': 1,
                               'scores': {'abstract': 0.92, 'title': 1.0, 'author': 0.62, 'year': 1}}])

    def test_docmatch_endpoint_no_abstract_solr_record(self):
        """
        when there is no abstract that title is quarried
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
                                                                               u'fl': u'bibcode,abstract,title,author_norm,year,doctype,identifier'}},
                                               u'response': {u'start': 0,
                                                             u'numFound': 1,
                                                             u'docs': [{"identifier":["2020arXiv200210896G", "2020A&A...635A.193G", "10.1051/0004-6361/202037526", "arXiv:2002.10896", "10.1051/0004-6361/202037526", "2020arXiv200210896G"],
                                                                        "year":"2020",
                                                                        "bibcode":"2020A&A...635A.193G",
                                                                        "doctype":"article",
                                                                        "title":["The population of hot subdwarf stars studied with Gaia. III. Catalogue of known hot subdwarf stars: Data Release 2"],
                                                                        "author_norm":["Geier, S"]}]
                                                             }
                                               }
            data = {"bibcode": "2020arXiv200210896G",
                    "year": "2020",
                    "title": "Population of hot subdwarf stars studied with Gaia III. Catalogue of\n  known hot subdwarf stars: Data Release 2",
                    "abstract": "In light of substantial new discoveries of hot subdwarfs by ongoing spectroscopic surveys and the availability of new all-sky data from ground-based photometric surveys and the Gaia mission Data Release 2, we compiled an updated catalogue of the known hot subdwarf stars. The catalogue contains 5874 unique sources including 528 previously unknown hot subdwarfs and provides multi-band photometry, astrometry from Gaia, and classifications based on spectroscopy and colours. This new catalogue provides atmospheric parameters of 2187 stars and radial velocities of 2790 stars from the literature. Using colour, absolute magnitude, and reduced proper motion criteria, we identified 268 previously misclassified objects, most of which are less luminous white dwarfs or more luminous blue horizontal branch and main-sequence stars. <P />The catalogues are only available at the CDS via anonymous ftp to <A href=\'http://cdsarc.u-strasbg.fr/\'>http://cdsarc.u-strasbg.fr</A> (ftp://130.79.128.5) or via <A href=\'http://cdsarc.u-strasbg.fr/viz-bin/cat/J/A+A/635/A193\'>http://cdsarc.u-strasbg.fr/viz-bin/cat/J/A+A/635/A193</A>",
                    "author": "Geier, S.",
                    "doctype":"eprint"}
            r= self.client.post(path='/docmatch', data=json.dumps(data))
            result = json.loads(r.data)
            self.assertEqual(result['query'],
                             'topn(10, similar("In light of substantial new discoveries of hot subdwarfs by ongoing spectroscopic surveys and the availability of new all-sky data from ground-based photometric surveys and the Gaia mission Data Release 2, we compiled an updated catalogue of the known hot subdwarf stars. The catalogue contains 5874 unique sources including 528 previously unknown hot subdwarfs and provides multi-band photometry, astrometry from Gaia, and classifications based on spectroscopy and colours. This new catalogue provides atmospheric parameters of 2187 stars and radial velocities of 2790 stars from the literature. Using colour, absolute magnitude, and reduced proper motion criteria, we identified 268 previously misclassified objects, most of which are less luminous white dwarfs or more luminous blue horizontal branch and main-sequence stars. <P />The catalogues are only available at the CDS via anonymous ftp to <A href=\'http://cdsarc.u-strasbg.fr/\'>http://cdsarc.u-strasbg.fr</A> (ftp://130.79.128.5) or via <A href=\'http://cdsarc.u-strasbg.fr/viz-bin/cat/J/A+A/635/A193\'>http://cdsarc.u-strasbg.fr/viz-bin/cat/J/A+A/635/A193</A>", input abstract, 41, 1, 1)) doctype:(article OR inproceedings OR inbook)')
            self.assertEqual(result['match'],
                             [{'source_bibcode': '2020arXiv200210896G', 'matched_bibcode': '2020A&A...635A.193G',
                               'confidence': 0.8988905, 'matched': 1,
                               'scores': {'abstract': None, 'title': 0.99, 'author': 1, 'year': 1}}])

    def test_docmatch_endpoint_matching_thesis(self):
        """
        Tests docmatch endpoint having thesis
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
                                                                               u'fl': u'bibcode,abstract,title,author_norm,year,doctype,identifier'}},
                                               u'response': {u'start': 0,
                                                             u'numFound': 1,
                                                             u'docs': [{u'bibcode': u'2017PhDT........67Z',
                                                                        u'title': [u'Density Matrix Embedding Theory and Strongly Correlated Lattice Systems'],
                                                                        u'abstract': u'This thesis describes the development of the density matrix embedding theory (DMET) and its applications to lattice strongly correlated electron problems. We introduced a broken spin and particle-number symmetry DMET formulation to study the high-temperature superconductivity and other low-energy competing states in models of the cuprate superconductors. These applications also relied on (i) the development and adaptation of approximate impurity solvers beyond exact diagonalization, including the density matrix renormalization group, auxiliary-field quantum Monte Carlo and active-space based quantum chemistry techniques, which expanded the sizes of fragments treated in DMET; and (ii) the theoretical development and numerical investigations for the finite size scaling behavior of DMET. Using these numerical tools, we computed a comprehensive ground state phase diagram of the standard and frustrated Hubbard models on the square lattice with well-controlled numerical uncertainties, which confirms the existence of the d-wave superconductivity and various inhomogeneous orders in the Hubbard model. We also investigated the long-sought strong coupling, underdoped regime of the Hubbard model in great detail, using various numerical techniques including DMET, and determined the ground state being a highly-compressible, filled vertical stripe at 1/8 doping in the coupling range commonly considered relevant to cuprates. The findings show both the relevance and limitations of the one-band Hubbard model in studying the cuprate superconductivity. Therefore, we further explored the three-band Hubbard model and downfolded cuprate Hamiltonians from first principles, in an attempt to understand the physics beyond the one-band model. We also extended the DMET formulation to finite temperature using the superoperator representation of the density operators, which is potentially a powerful tool to investigate finite-temperature properties of cuprates and other strongly correlated electronic systems.',
                                                                        u'doctype': u'phdthesis',
                                                                        u'author_norm': [u'Zheng, B'],
                                                                        u'year': u'2017',
                                                                        u'identifier': [u'22018arXiv180310259Z', u'2017PhDT........67Z', u'arXiv:1803.10259', u'2018arXiv180310259Z']}]
                                                             }
                                               }
            data = {"bibcode": "2018arXiv180310259Z",
                    "mustmatch": False,
                    "title": "Density Matrix Embedding Theory and Strongly Correlated Lattice Systems",
                    "match_doctype": ["phdthesis", "mastersthesis"],
                    "abstract": "This thesis describes the development of the density matrix embedding theory (DMET) and its applications to lattice strongly correlated electron problems, including a review of DMET theory and algorithms (Ch 2), investigation of finite size scaling (Ch 3), Applications to high-temperature superconductivity (Ch 4-6), a framework for finite-temperature DMET (Ch 7).",
                    "author": "Zheng, Bo-Xiao",
                    "year": "2018",
                    "doctype": "eprint",
                    "doi": None}
            r= self.client.post(path='/docmatch', data=json.dumps(data))
            result = json.loads(r.data)
            self.assertEqual(result['query'],
                             'author_norm:"zheng, b" year:[2013 TO 2023] doctype:("phdthesis" OR "mastersthesis")')
            self.assertEqual(result['match'],
                             [{'source_bibcode': '2018arXiv180310259Z', 'matched_bibcode': '2017PhDT........67Z',
                               'confidence': 0.8730186, 'matched': 1,
                               'scores': {'abstract': 0.89, 'title': 1.0, 'author': 1, 'year': 1}}])
            self.assertEqual(result['comment'],
                             'Matching doctype `phdthesis;mastersthesis`.')

    def test_docmatch_endpoint_no_result_from_solr_thesis(self):
        """
        Tests docmatch endpoint having no result from solr when solr queried with thesis information
        """
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
                                                                               u'fl': u'bibcode,abstract,title,author_norm,year,doctype,identifier'}},
                                               u'response': {u'start': 0,
                                                             u'numFound': 0}
                                               }
            data = {"bibcode": "2018arXiv180310259Z",
                    "mustmatch": False,
                    "title": "Density Matrix Embedding Theory and Strongly Correlated Lattice Systems",
                    "match_doctype": ["phdthesis", "mastersthesis"],
                    "abstract": "This thesis describes the development of the density matrix embedding theory (DMET) and its applications to lattice strongly correlated electron problems, including a review of DMET theory and algorithms (Ch 2), investigation of finite size scaling (Ch 3), Applications to high-temperature superconductivity (Ch 4-6), a framework for finite-temperature DMET (Ch 7).",
                    "author": "Zheng, Bo-Xiao",
                    "year": "2018",
                    "doctype": "eprint",
                    "doi": None}
            r= self.client.post(path='/docmatch', data=json.dumps(data))
            result = json.loads(r.data)
            self.assertEqual(result['query'],
                             'author_norm:"zheng, b" year:[2013 TO 2023] doctype:("phdthesis" OR "mastersthesis")')
            self.assertEqual(result['no match'],
                             'no document was found in solr matching the request.')
            self.assertEqual(result['comment'],
                             'Matching doctype `phdthesis;mastersthesis`. No matches for phdthesis;mastersthesis.')

    def test_clean_data(self):
        """
        Tests routine that cleans abstract and title
        """
        abstract = "\x01An    investigation"
        self.assertEqual(clean_data(abstract), "An investigation")


    def test_docmatch_endpoint_no_abstract_source(self):
        """
        Tests docmatch endpoint using metadata abstract/title to query solr, when there is no abstract, and we found a match
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
                                                                               u'fl': u'bibcode,abstract,title,author_norm,year,doctype,identifier'}},
                                               u'response': {u'start': 0,
                                                             u'numFound': 1,
                                                             u'docs': [{u'title': [u'Statistical analysis of Curiosity data shows no evidence for a strong seasonal cycle of Martian methane'],
                                                                        u'abstract': u'Using Gaussian process regression to analyze the Martian surface methane Tunable Laser Spectrometer (TLS) data reported by Webster et al. (2018), we find that the TLS data, taken as a whole, do not indicate seasonal variability. Enrichment protocol CH<SUB>4</SUB> data are consistent with either stochastic variation or a spread of periods without seasonal preference.',
                                                                        u'bibcode': u'2020Icar..33613407G',
                                                                        u'author_norm': [u'Gillen, E', u'Rimmer, P', u'Catling, D'],
                                                                        u'year': u'2020',
                                                                        u'doctype': u'article',
                                                                        u'identifier': [u'2019arXiv190802041G', u'2020Icar..33613407G', u'10.1016/j.icarus.2019.113407', u'10.1016/j.icarus.2019.113407', u'arXiv:1908.02041', u'2019arXiv190802041G'],
                                                                        },
                                                                       {u'title': [u'Radiometric Calibration of Tls Intensity: Application to Snow Cover Change Detection'],
                                                                        u'abstract': u'This paper reports on the radiometric calibration and the use of calibrated intensity data in applications related to snow cover monitoring with a terrestrial laser scanner (TLS). An application of the calibration method to seasonal snow cover change detection is investigated. The snow intensity from TLS data was studied in Sodankyl\xe4, Finland during the years 2008-2009 and in Kirkkonummi, Finland in the winter 2010-2011. The results were used to study the behaviour of TLS intensity data on different types of snow and measurement geometry. The results show that the snow type seems to have little or no effect on the incidence angle behaviour of the TLS intensity and that the laser backscatter from the snow surface is not directly related to any of the snow cover properties, but snow structure has a clear effect on TLS intensity.',
                                                                        u'bibcode': u'2011ISPAr3812W.175A',
                                                                        u'author_norm': [u'Anttila, K', u'Kaasalainen, S', u'Krooks, A', u'Kaartinen, H', u'Kukko, A', u'Manninen, T', u'Lahtinen, P', u'Siljamo, N'],
                                                                        u'year': u'2011',
                                                                        u'doctype': u'article',
                                                                        u'identifier': [u'2011ISPAr3812W.175A', u'10.5194/isprsarchives-XXXVIII-5-W12-175-2011', u'10.5194/isprsarchives-XXXVIII-5-W12-175-2011']
                                                                       }]
                                                             }
                                               }
            # this bibcode actually does have abstract, for test purposes, for testing with no abstract and match
            data = {"bibcode":"2019arXiv190802041G",
                    "abstract":"",
                    "title":"Statistical analysis of Curiosity data shows no evidence for a strong seasonal cycle of Martian methane",
                    "author":"Gillen, Ed; Rimmer, Paul B; Catling, David C",
                    "year":"2020",
                    "doctype":"eprint"}
            r= self.client.post(path='/docmatch', data=json.dumps(data))
            result = json.loads(r.data)
            self.assertEqual(result['query'],
                             'topn(10, similar("Statistical analysis of Curiosity data shows no evidence for a strong seasonal cycle of Martian methane", input title, 13, 1, 1)) doctype:(article OR inproceedings OR inbook)')
            self.assertEqual(result['match'],
                             [{'source_bibcode': '2019arXiv190802041G', 'matched_bibcode': '2020Icar..33613407G',
                               'confidence': 0.8989977, 'matched': 1,
                               'scores': {'abstract': None, 'title': 1.0, 'author': 1, 'year': 1}}])


    def test_query_endpoint(self):
        """
        Test query endpoint with and without params passing in
        :return:
        """
        r = self.client.post(path='/query')
        result = json.loads(r.data)
        self.assertDictEqual(result, {'params': {'rows': 2000, 'start': 0, 'date_cutoff': '1972-01-01 00:00:00+00:00'}, 'results': [['2018arXiv180310259Z', '2017PhDT........67Z', 0.8730186], ['2017arXiv171011147R', '2018Natur.556..473R', 0.8745491], ['2019arXiv190500882A', '2019JHEP...06..121A', 0.8960806], ['2019arXiv190804722C', '2019JHEP...10..244S', 0.8865355], ['2020arXiv200210896G', '2020A&A...635A.193G', 0.8988905], ['2019arXiv190802041G', '2020Icar..33613407G', 0.8766192]]})

        # set the rows to a larger number and see that it is reset
        r = self.client.post(path='/query', data=json.dumps({'rows': 3000, 'start': 0}))
        result = json.loads(r.data)
        self.assertDictEqual(result, {'params': {'rows': 2000, 'start': 0, 'date_cutoff': '1972-01-01 00:00:00+00:00'}, 'results': [['2018arXiv180310259Z', '2017PhDT........67Z', 0.8730186], ['2017arXiv171011147R', '2018Natur.556..473R', 0.8745491], ['2019arXiv190500882A', '2019JHEP...06..121A', 0.8960806], ['2019arXiv190804722C', '2019JHEP...10..244S', 0.8865355], ['2020arXiv200210896G', '2020A&A...635A.193G', 0.8988905], ['2019arXiv190802041G', '2020Icar..33613407G', 0.8766192]]})

    def test_get_matches(self):
        """

        :return:
        """
        source_bibcode = '2022arXiv220606316S'
        abstract = 'In the present paper, discussion of the canonical quantization of a weakly nonideal Bose gas at zero temperature along the lines of the famous Bogolyubov approach is continued. Contrary to the previous paper on this subject, here the two-body interaction potential is considered in the general form. It is shown that consideration of the first nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach, without any modification of the resulting effective Hamiltonian.'
        title = 'Nonlinear corrections in the quantization of a weakly nonideal Bose gas   at zero temperature. II. The general case'
        author = 'Smolyakov, Mikhail N.'
        year = 2022
        doi = ['10.1016/j.chaos.2021.111505']

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
        match = get_matches(source_bibcode, abstract, title, author, year, None, matched_docs)
        self.assertEqual(len(match), 1)
        self.assertDictEqual(match[0], {'source_bibcode': '2022arXiv220606316S',
                                        'matched_bibcode': '2021CSF...15311505S',
                                        'confidence': 0.7936664,
                                        'matched': 1,
                                        'scores': {'abstract': 0.76, 'title': 0.98, 'author': 1, 'year': 1}})

        # no abstract, no doi
        match = get_matches(source_bibcode, '', title, author, year, None, matched_docs)
        self.assertEqual(len(match), 1)
        self.assertDictEqual(match[0], {'source_bibcode': '2022arXiv220606316S',
                                        'matched_bibcode': '2021CSF...15311505S',
                                        'confidence': 0.9986353,
                                        'matched': 1,
                                        'scores': {'abstract': None, 'title': 0.98, 'author': 1, 'year': 1}})

        # abstract, doi
        match = get_matches(source_bibcode, abstract, title, author, year, doi, matched_docs)
        self.assertEqual(len(match), 1)
        self.assertDictEqual(match[0], {'source_bibcode': '2022arXiv220606316S',
                                        'matched_bibcode': '2021CSF...15311505S',
                                        'confidence': 0.9946523,
                                        'matched': 1,
                                        'scores': {'abstract': 0.76, 'title': 0.98, 'author': 1, 'year': 1, 'doi': 1}})

        # no abstract, doi
        match = get_matches(source_bibcode, '', title, author, year, doi, matched_docs)
        self.assertEqual(len(match), 1)
        self.assertDictEqual(match[0], {'source_bibcode': '2022arXiv220606316S',
                                        'matched_bibcode': '2021CSF...15311505S',
                                        'confidence': 0.9899692,
                                        'matched': 1,
                                        'scores': {'abstract': None, 'title': 0.98, 'author': 1, 'year': 1, 'doi': 1}})

    def test_get_match_for_pub_with_doi(self):
        """
        Test matching publication with doi
        :return:
        """
        source_bibcode = '2022AcAT....3a..27P'
        abstract = 'Not Available'
        title = 'Revisiting the spectral energy distribution of I Zw 1 under the CaFe Project'
        author = 'Panda, Swayamtrupta; Dias dos Santos, Denimara'
        year = 2022
        doi = ['10.31059/aat.vol3.iss1.pp27-34']

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
        match = get_matches(source_bibcode, abstract, title, author, year, doi, matched_docs)
        self.assertEqual(len(match), 1)
        self.assertDictEqual(match[0], {'source_bibcode': '2022AcAT....3a..27P',
                                        'matched_bibcode': '2021arXiv211101521P',
                                        'confidence': 0.9911571,
                                        'matched': 1,
                                        'scores': {'abstract': None, 'title': 1.0, 'author': 1, 'year': 1, 'doi': 1}})


if __name__ == "__main__":
    unittest.main()
