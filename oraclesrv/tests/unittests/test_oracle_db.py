import sys, os
project_home = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

import unittest
import json
import mock

from adsmutils import get_date

from oraclesrv.tests.unittests.base import TestCaseDatabase
from oraclesrv.utils import get_a_record, del_records, add_a_record, query_docmatch, query_source_score, lookup_confidence, \
    get_a_matched_record, query_docmatch, query_source_score, lookup_confidence, delete_tmp_matches, replace_tmp_with_canonical, \
    delete_multi_matches, clean_db, get_tmp_bibcodes, get_muti_matches
from oraclesrv.score import get_matches, get_doi_match
from oraclesrv.models import DocMatch, ConfidenceLookup, EPrintBibstemLookup

from sqlalchemy.exc import SQLAlchemyError


class TestDatabase(TestCaseDatabase):

    def add_docmatch_data(self):
        """
        Add docmatch data
        """
        self.add_eprint_bibstem_lookup_data()

        docmatch_data = [
                        ('2021arXiv210312030S', '2021CSF...15311505S', 0.9829099),
                        ('2017arXiv171111082H', '2018ConPh..59...16H', 0.9877064),
                        ('2018arXiv181105526S', '2022NuPhB.98015830S', 0.97300124),
        ]

        docmatch_records = []
        for record in docmatch_data:
            docmatch_record = {'source_bibcode': record[0],
                               'matched_bibcode': record[1],
                               'confidence': record[2]}
            docmatch_records.append(docmatch_record)

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        response = self.client.put('/add', data=json.dumps(docmatch_records), headers=headers)
        self.assertEqual(response._status_code, 200)
        self.assertEqual(response.json['status'], 'updated db with new data successfully')

    def delete_docmatch_data(self):
        """

        """
        self.delete_eprint_bibstem_lookup_data()

        with self.current_app.session_scope() as session:
            session.query(DocMatch).delete()
            session.commit()

    def add_confidence_lookup_data(self):
        """

        """
        confidence_lookup_table = [
            ConfidenceLookup(source='ADS', confidence=1.3),
            ConfidenceLookup(source='incorrect', confidence=-1),
            ConfidenceLookup(source='author', confidence=1.2),
            ConfidenceLookup(source='publisher', confidence=1.1),
            ConfidenceLookup(source='SPIRES', confidence=1.05),
        ]
        with self.current_app.session_scope() as session:
            session.bulk_save_objects(confidence_lookup_table)
            session.commit()

    def delete_confidence_lookup_data(self):
        """

        """
        with self.current_app.session_scope() as session:
            session.query(ConfidenceLookup).delete()
            session.commit()

    def add_eprint_bibstem_lookup_data(self):
        """

        """
        eprint_bibstem_lookup_table = [
            EPrintBibstemLookup(name='arXiv', pattern=r'^(\d\d\d\d(?:arXiv|acc\.phys|adap\.org|alg\.geom|ao\.sci|astro\.ph|atom\.ph|bayes\.an|chao\.dyn|chem\.ph|cmp\.lg|comp\.gas|cond\.mat|cs\.|dg\.ga|funct\.an|gr\.qc|hep\.ex|hep\.lat|hep\.ph|hep\.th|math\.|math\.ph|mtrl\.th|nlin\.|nucl\.ex|nucl\.th|patt\.sol|physics\.|plasm\.ph|q\.alg|q\.bio|quant\.ph|solv\.int|supr\.con))'),
            EPrintBibstemLookup(name='Earth Science', pattern=r'^(\d\d\d\d(?:EaArX|esoar))'),
        ]
        with self.current_app.session_scope() as session:
            session.bulk_save_objects(eprint_bibstem_lookup_table)
            session.commit()

    def delete_eprint_bibstem_lookup_data(self):
        """

        """
        with self.current_app.session_scope() as session:
            session.query(EPrintBibstemLookup).delete()
            session.commit()

    def test_get_a_record(self):
        """
        test querying db for a record
        """
        self.add_docmatch_data()

        # query for a record that exists
        record = get_a_record('2021arXiv210312030S', '2021CSF...15311505S')
        self.assertEqual(record['eprint_bibcode'], '2021arXiv210312030S')
        self.assertEqual(record['pub_bibcode'], '2021CSF...15311505S')
        self.assertEqual(record['confidence'], 0.9829099)

        # query for a record that does not exits
        record = get_a_record('2021arXiv210312030G', '2021CSF...15311505G')
        self.assertEqual(record, {})

        self.delete_docmatch_data()

    def test_del_records(self):
        """
        test querying db for a record
        """
        self.add_docmatch_data()

        docmatch_records = [
            {
                "source_bibcode": "2021arXiv210312030S",
                "matched_bibcode": "2021CSF...15311505S",
                "confidence": 0.9829099
            }, {
                "source_bibcode": "2017arXiv171111082H",
                "matched_bibcode": "2018ConPh..59...16H",
                "confidence": 0.9877064
            }, {
                "source_bibcode": "2018arXiv181105526S",
                "matched_bibcode": "2022NuPhB.98015830S",
                "confidence": 0.97300124
            }
        ]
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        response = self.client.delete('/delete', data=json.dumps(docmatch_records), headers=headers)
        self.assertEqual(response._status_code, 200)
        self.assertEqual(response.json['status'], 'removed 3 records of 3 requested')

        # attempt to delete for the second time the same data
        response = self.client.delete('/delete', data=json.dumps(docmatch_records), headers=headers)
        self.assertEqual(response._status_code, 200)
        self.assertEqual(response.json['status'], 'removed 0 records of 3 requested')

        self.delete_docmatch_data()

    def test_docmatch(self):
        """
        test matching a record and compute the score
        """
        source_bibcode = '2022arXiv220606316S'
        abstract = 'In the present paper, discussion of the canonical quantization of a weakly nonideal Bose gas at zero temperature along the lines of the famous Bogolyubov approach is continued. Contrary to the previous paper on this subject, here the two-body interaction potential is considered in the general form. It is shown that consideration of the first nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach, without any modification of the resulting effective Hamiltonian.'
        title = 'Nonlinear corrections in the quantization of a weakly nonideal Bose gas   at zero temperature. II. The general case'
        author = 'Smolyakov, Mikhail N.'
        year = 2022
        matched_docs = [{'bibcode': '2021CSF...15311505S',
                         'abstract': 'In the present paper, quantization of a weakly nonideal Bose gas at zero temperature along the lines of the well-known Bogolyubov approach is performed. The analysis presented in this paper is based, in addition to the steps of the original Bogolyubov approach, on the use of nonoscillation modes (which are also solutions of the linearized Heisenberg equation) for recovering the canonical commutation relations in the linear approximation, as well as on the calculation of the first nonlinear correction to the solution of the linearized Heisenberg equation which satisfies the canonical commutation relations at the next order. It is shown that, at least in the case of free quasi-particles, consideration of the nonlinear correction automatically solves the problem of nonconserved particle number, which is inherent to the original approach.',
                         'author_norm': ['Smolyakov, M'],
                         'doctype': 'article',
                         'identifier': ['10.1016/j.chaos.2021.111505', 'arXiv:2103.12030', '2021CSF...15311505S', '2021arXiv210312030S'],
                         'title': ['Nonlinear corrections in the quantization of a weakly nonideal Bose gas at zero temperature'],
                         'year': '2021'},
                        {'bibcode': '2020PhRvR...2c3276C',
                         'abstract': 'We develop a quantum many-body theory of the Bose-Hubbard model based on the canonical quantization of the action derived from a Gutzwiller mean-field ansatz. Our theory is a systematic generalization of the Bogoliubov theory of weakly interacting gases. The control parameter of the theory, defined as the zero point fluctuations on top of the Gutzwiller mean-field state, remains small in all regimes. The approach provides accurate results throughout the whole phase diagram, from the weakly to the strongly interacting superfluid and into the Mott insulating phase. As specific examples of application, we study the two-point correlation functions, the superfluid stiffness, and the density fluctuations, for which quantitative agreement with available quantum Monte Carlo data is found. In particular, the two different universality classes of the superfluid-insulator quantum phase transition at integer and noninteger filling are recovered.',
                         'author_norm': ['Caleffi, F', 'Capone, M', 'Menotti, C', 'Carusotto, I', 'Recati, A'],
                         'doctype': 'article',
                         'identifier': ['arXiv:1908.03470', '2019arXiv190803470C', '10.1103/PhysRevResearch.2.033276', '2020PhRvR...2c3276C'],
                         'title': ['Quantum fluctuations beyond the Gutzwiller approximation in the Bose-Hubbard model'],
                         'year': '2020'},
                        {'bibcode': '2011PhRvE..83e1132W',
                         'abstract': 'Based on counting statistics and Bogoliubov theory, we present a recurrence relation for the microcanonical partition function for a weakly interacting Bose gas with a finite number of particles in a cubic box. According to this microcanonical partition function, we calculate numerically the distribution function, condensate fraction, and condensate fluctuations for a finite and isolated Bose-Einstein condensate. For ideal and weakly interacting Bose gases, we compare the condensate fluctuations with those in the canonical ensemble. The present approach yields an accurate account of the condensate fluctuations for temperatures close to the critical region. We emphasize that the interactions between excited atoms turn out to be important for moderate temperatures.',
                         'author_norm': ['Wang, J', 'He, J', 'Ma, Y'],
                         'doctype': 'article',
                         'identifier': ['10.1103/PhysRevE.83.051132', '2011PhRvE..83e1132W'],
                         'title': ['Condensate fluctuations of interacting Bose gases within a microcanonical ensemble'],
                         'year': '2011'},
                        {'bibcode': '1999LNP...517..129K',
                         'abstract': 'Canonical quantization may be approached from several different starting points. The usual approaches involve promotion of c-numbers to q-numbers, or path integral constructs, each of which generally succeeds only in Cartesian coordinates. All quantization schemes that lead to Hilbert space vectors and Weyl operators—even those that eschew Cartesian coordinates—implicitly contain a metric on a flat phase space. This feature is demonstrated by studying the classical and quantum "aggregations", namely, the set of all facts and properties resident in all classical and quantum theories, respectively. Metrical quantization is an approach that elevates the flat phase space metric inherent in any canonical quantization to the level of a postulate. Far from being an unwanted structure, the flat phase space metric carries essential physical information. It is shown how the metric, when employed within a continuous-time regularization scheme, gives rise to an unambiguous quantization procedure that automatically leads to a canonical coherent state representation. Although attention in this paper is confined to canonical quantization we note that alternative, nonflat metrics may also be used, and they generally give rise to qualitatively different, noncanonical quantization schemes.',
                         'author_norm': ['Klauder, J'],
                         'doctype': 'inbook',
                         'identifier': ['10.1007/BFb0105343', '1999qffv.conf..129K', '1998quant.ph..4009K', 'arXiv:quant-ph/9804009', '1999LNP...517..129K'],
                         'title': ['Metrical Quantization'],
                         'year': '1999'},
                        {'bibcode': '2009JMP....50a3527G',
                         'abstract': 'We obtain a canonical form of a quadratic Hamiltonian for linear waves in a weakly inhomogeneous medium. This is achieved by using the Wentzel-Kramers-Brillouin representation of wave packets. The canonical form of the Hamiltonian is obtained via the series of canonical Bogolyubov-type and near-identical transformations. Various examples of the application illustrating the main features of our approach are presented. The knowledge of the Hamiltonian structure for linear wave systems provides a basis for developing a theory of weakly nonlinear random waves in inhomogeneous media generalizing the theory of homogeneous wave turbulence.',
                         'author_norm': ['Gershgorin, B', 'Lvov, Y', 'Nazarenko, S'],
                         'doctype': 'article',
                         'identifier': ['2008arXiv0807.1149G', '10.1063/1.3054275', 'arXiv:0807.1149', '2009JMP....50a3527G'],
                         'title': ['Canonical Hamiltonians for waves in inhomogeneous media'],
                         'year': '2009'},
                        {'bibcode': '2017NJPh...19k3002K',
                         'abstract': 'The low-temperature properties of certain quantum magnets can be described in terms of a Bose-Einstein condensation (BEC) of magnetic quasiparticles (triplons). Some mean-field approaches (MFA) to describe these systems, based on the standard grand canonical ensemble, do not take the anomalous density into account and leads to an internal inconsistency, as it has been shown by Hohenberg and Martin, and may therefore produce unphysical results. Moreover, an explicit breaking of the U(1) symmetry as observed, for example, in TlCuCl<SUB>3</SUB> makes the application of MFA more complicated. In the present work, we develop a self-consistent MFA approach, similar to the Hartree-Fock-Bogolyubov approximation in the notion of representative statistical ensembles, including the effect of a weakly broken U(1) symmetry. We apply our results on experimental data of the quantum magnet TlCuCl<SUB>3</SUB> and show that magnetization curves and the energy dispersion can be well described within this approximation assuming that the BEC scenario is still valid. We predict that the shift of the critical temperature T <SUB>c</SUB> due to a finite exchange anisotropy is rather substantial even when the anisotropy parameter γ is small, e.g., {{Δ }}{T}<SUB>{c</SUB>}≈ 10 % of T <SUB>c</SUB> in H = 6 T and for γ ≈ 4 μ {eV}.',
                         'author_norm': ['Khudoyberdiev, A', 'Rakhimov, A', 'Schilling, A'],
                         'doctype': 'article',
                         'identifier': ['2017NJPh...19k3002K', '2017arXiv170108009K', 'arXiv:1701.08009', '10.1088/1367-2630/aa8a2f'],
                         'title': ['Bose-Einstein condensation of triplons with a weakly broken U(1) symmetry'],
                         'year': '2017'},
                        {'bibcode': '1995TMP...105.1249T',
                         'abstract': "The nonideal degenerate Bose-system at a temperature close to zero is investigated by N. N. Bogolyubov and D. N. Zubarev's method of collective variables. Applicable to a wide range of frequencies and wave vectors, interpolated expressions for the Green functions of the densities of conserved quantities and for the superfluid velocity potential are derived from exact relations. The criteria defining the validity domain of the hydrodynamic approximation are obtained. The kinetic coefficients of two-liquid hydrodynamics at temperatures close to zero are calculated for a weakly nonideal Bose-gas. A comparison with the method employing the kinetic equation for quasi-particles is made.",
                         'author_norm': ['Tserkovnikov, Y'],
                         'doctype': 'article',
                         'identifier': ['1995TMP...105.1249T', '10.1007/BF02067493'],
                         'title': ['Molecular hydrodynamics of a weakly degenerate nonideal bose-gas II. Green functions and kinetic coefficients'],
                         'year': '1995'}]

        self.add_eprint_bibstem_lookup_data()

        # case when multiple arXiv can be matched against one publisher
        # best match for this second arXiv paper is the publisher's first paper, the publisher's second paper not yet published
        best_match = {'source_bibcode': '2022arXiv220606316S',
                      'matched_bibcode': '2021CSF...15311505S',
                      'confidence': 0.7142998,
                      'matched': 1,
                      'scores': {'abstract': 0.76, 'title': 0.98, 'author': 1, 'year': 1}}
        matches = get_matches(source_bibcode, abstract, title, author, year, None, matched_docs)
        self.assertEqual(len(matches), 1)
        self.assertDictEqual(matches[0], best_match)

        # it will get added again in stub_data
        self.delete_eprint_bibstem_lookup_data()

        # now insert the match of first arXiv paper and first publisher to the db
        self.add_docmatch_data()

        # now attempting to get a match returns the match with highest confidence
        # with either source bibcode or one of the matching bibcodes
        best_match = {'source_bibcode': '2021arXiv210312030S',
                      'matched_bibcode': '2021CSF...15311505S',
                      'confidence': 0.9829099,
                      'matched': 1,
                      'scores': {}}
        matches = get_matches(source_bibcode, abstract, title, author, year, None, matched_docs)
        self.assertEqual(len(matches), 1)
        self.assertDictEqual(matches[0], best_match)

        self.delete_docmatch_data()

    def test_docmatch_changed_bibcode(self):
        """
        test when the bibcode saved in db is different from the current match, but the record is the same and needs
        to be recognized as such
        """
        self.add_docmatch_data()

        # add prev match to database
        prev_match = {'source_bibcode': '2021arXiv210911714Q',
                      'matched_bibcode': '2022MNRAS.tmp.1429J',
                      'confidence': 0.982056}
        add_a_record(prev_match)

        # current source with new bibcode, having old bibcode in identifier
        source_doc = {'abstract': 'We numerically investigate non-Gaussianities in the late-time cosmological density field in Fourier space. We explore various statistics, including the two-point and three-point probability distribution function (PDF) of phase and modulus, and two three-point correlation function of of phase and modulus. We detect significant non-Gaussianity for certain configurations. We compare the simulation results with the theoretical expansion series of {2007ApJS..170....1M}. We find that the  order term alone is sufficiently accurate to describe all the measured non-Gaussianities in not only the PDFs, but also the correlations. We also numerically find that the phase-modulus cross-correlation contributes  to the bispectrum, further verifying the accuracy of the  order prediction. This work demonstrates that non-Gaussianity of the cosmic density field is simpler in Fourier space, and may facilitate the data analysis in the era of precision cosmology.',
                      'title': 'Numerical investigation of non-Gaussianities in the phase and modulus of   density Fourier modes',
                      'author': 'Qin, Jian; Pan, Jun; Yu, Yu; Zhang, Pengjie',
                      'year': '2021',
                      'doctype': 'eprint',
                      'bibcode': '2021arXiv210911714Q',
                      'doi': '10.1093/mnras/stac1454'}
        # current match with new bibcode
        matched_docs = [{'bibcode':'2022MNRAS.514.1548Q',
                         'abstract':'We numerically investigate the non-Gaussianities in the late-time cosmological density field in Fourier space. We explore various statistics, including the two- and three-point probability distribution function (PDF) of phase and modulus, and their two- and three-point correlation function. Significant non-Gaussianity is observed for certain configurations. Comparing the measurement from simulation with the theoretical expansion prediction, we find that for (600 Mpc h<SUP>-1</SUP>)<SUP>3</SUP> volume, the $\\mathcal {O}(V^{-1/2})$ order term alone is sufficiently accurate to describe all the measured non-Gaussianities in not only the PDFs, but also the correlations. We also numerically find that the phase-modulus cross-correlation contributes $\\sim 50{{\\ \\rm per\\ cent}}$ to the bispectrum, further verifying the accuracy of the $\\mathcal {O}(V^{-1/2})$ order prediction. This work demonstrates that the non-Gaussianity of cosmic density field is simpler in Fourier space, and may facilitate the data analysis in the era of precision cosmology.',
                         'author_norm':['Qin, J', 'Pan, J', 'Yu, Y', 'Zhang, P'],
                         'doctype':'article',
                         'doi': ['10.1093/mnras/stac1454'],
                         'identifier':['2022MNRAS.tmp.1429J', '2021arXiv210911714Q', '10.1093/mnras/stac1454', '2022MNRAS.514.1548Q', 'arXiv:2109.11714'],
                         'title':['Numerical investigation of non-Gaussianities in the phase and modulus of density Fourier modes'],
                         'year':'2022'}]
        # match it
        matches = get_doi_match(source_doc['bibcode'], source_doc['abstract'], source_doc['title'],
                              source_doc['author'], source_doc['year'], source_doc['doi'], matched_docs)
        # current match the same as prev with the new bibcode
        current_match = {'source_bibcode': '2021arXiv210911714Q',
                         'matched_bibcode': '2022MNRAS.514.1548Q',
                         'confidence': 0.982056,
                         'matched': 1,
                         'scores': {}}
        self.assertEqual(len(matches), 1)
        self.assertDictEqual(matches[0], current_match)

        self.delete_docmatch_data()

    def test_query(self):
        """

        """
        self.add_docmatch_data()

        # add records to db, including multiple matches
        matches = [
            {'source_bibcode': '2021arXiv210911714Q', 'matched_bibcode': '2022MNRAS.tmp.1429J', 'confidence': 0.982056},
            {'source_bibcode': '2021arXiv210312030S', 'matched_bibcode': '2021CSF...15311505S', 'confidence': 0.9829099},
            {'source_bibcode': '2017arXiv171111082H', 'matched_bibcode': '2018ConPh..59...16H', 'confidence': 0.9877064},
            {'source_bibcode': '2018arXiv181105526S', 'matched_bibcode': '2022NuPhB.98015830S', 'confidence': 0.97300124},
            {'source_bibcode': '2021arXiv210614498B', 'matched_bibcode': '2021JHEP...10..058B', 'confidence': 0.9938304},
            {'source_bibcode': '2022arXiv220806634R', 'matched_bibcode': '2022MNRAS.tmp.2065R', 'confidence': 0.994127},
            {'source_bibcode': '2022arXiv220700058R', 'matched_bibcode': '2022ApJ...935...54R', 'confidence': 0.9939186},
            {'source_bibcode': '2022arXiv220702921C', 'matched_bibcode': '2022ApJ...935...44C', 'confidence': 0.9927035},
        ]

        for match in matches:
            add_a_record(match)

        expected_results = [
            ('2017arXiv171111082H', '2018ConPh..59...16H', 0.9877064),
            ('2021arXiv210312030S', '2021CSF...15311505S', 0.9829099),
            ('2021arXiv210614498B', '2021JHEP...10..058B', 0.9938304),
            ('2022arXiv220702921C', '2022ApJ...935...44C', 0.9927035),
            ('2022arXiv220700058R', '2022ApJ...935...54R', 0.9939186),
            ('2021arXiv210911714Q', '2022MNRAS.tmp.1429J', 0.982056),
            ('2022arXiv220806634R', '2022MNRAS.tmp.2065R', 0.994127),
            ('2018arXiv181105526S', '2022NuPhB.98015830S', 0.97300124),
        ]

        # test all unique records are returned
        result, status_code = query_docmatch({'start': 0, 'rows':10, 'date_cutoff': get_date('1972/01/01 00:00:00')})
        self.assertEqual(status_code, 200)
        self.assertEqual(result, expected_results)

        # now test returning a page a time
        for i in range(0, len(matches), 2):
            result, status_code = query_docmatch({'start': i, 'rows': 2, 'date_cutoff': get_date('1972/01/01 00:00:00')})
            self.assertEqual(status_code, 200)
            self.assertEqual(result, expected_results[i:i+2])

        # do one iteration and see it returns 0 records
        result, status_code = query_docmatch({'start': len(matches), 'rows': 2, 'date_cutoff': get_date('1972/01/01 00:00:00')})
        self.assertEqual(status_code, 200)
        self.assertEqual(result, [])

        self.delete_docmatch_data()

    def test_query_source_score(self):
        """

        """
        self.add_confidence_lookup_data()
        expected_results = [
            {'source': 'ADS', 'confidence': 1.3},
            {'source': 'incorrect', 'confidence': -1.0},
            {'source': 'author', 'confidence': 1.2},
            {'source': 'publisher', 'confidence': 1.1},
            {'source': 'SPIRES', 'confidence': 1.05}
        ]
        results, _ = query_source_score()
        self.assertEqual(results, expected_results)
        self.delete_confidence_lookup_data()

    def test_lookup_confidence(self):
        """

        """
        self.add_confidence_lookup_data()
        self.assertEqual(lookup_confidence('ADS'), (1.3, 200))
        self.assertEqual(lookup_confidence('incorrect'), (-1.0, 200))
        self.delete_confidence_lookup_data()

    def test_source_score_endpoint(self):
        """
        Test the endpoint that lists all available source/score pairs
        """
        self.add_confidence_lookup_data()
        expected_results = [
            {'source': 'ADS', 'confidence': 1.3},
            {'source': 'incorrect', 'confidence': -1.0},
            {'source': 'author', 'confidence': 1.2},
            {'source': 'publisher', 'confidence': 1.1},
            {'source': 'SPIRES', 'confidence': 1.05}
        ]
        r = self.client.get(path='/source_score')
        result = json.loads(r.data)
        self.assertEqual(result['results'], expected_results)
        self.delete_confidence_lookup_data()

    def test_lookup_confidence_endpoint(self):
        """
        Test the endpoint that returns confidence for a source
        """
        self.add_confidence_lookup_data()
        r = self.client.get(path='/confidence/ADS')
        result = json.loads(r.data)
        self.assertEqual(result['confidence'], 1.3)
        r = self.client.get(path='/confidence/incorrect')
        result = json.loads(r.data)
        self.assertEqual(result['confidence'], -1.0)
        self.delete_confidence_lookup_data()

    def test_get_solr_data_exception(self):
        """
        Test when there is an SQLAlchemyError exception
        """
        with mock.patch.object(self.current_app, 'session_scope') as exception_mock:
            sql_alchemy_error = SQLAlchemyError('DB not initialized properly, check: SQLALCHEMY_URL')
            exception_mock.side_effect = sql_alchemy_error

            # exception within add_a_record
            status, message = add_a_record({})
            self.assertEqual(status, False)
            self.assertEqual(message, 'SQLAlchemy: DB not initialized properly, check: SQLALCHEMY_URL')

            # exception within del_records
            status, message = del_records(docmatches=None)
            self.assertEqual(status, False)
            self.assertEqual(message, 'SQLAlchemy: DB not initialized properly, check: SQLALCHEMY_URL')

            # exception within get_a_record
            results = get_a_record(source_bibcode='', matched_bibcode='')
            self.assertEqual(results, {})

            # exception within get_a_matched_record
            results = get_a_matched_record(source_bibcode='')
            self.assertEqual(results, {})

            # exception within query_docmatch
            result, status_code = query_docmatch({})
            self.assertEqual(result, [])
            self.assertEqual(status_code, 404)

            # exception within query_source_score
            result, status_code = query_source_score()
            self.assertEqual(result, [])
            self.assertEqual(status_code, 404)

            # exception within lookup_confidence
            confidence, status_code = lookup_confidence(source='')
            self.assertEqual(confidence, 0)
            self.assertEqual(status_code, 404)

            # exception within delete_tmp_matches
            status, message = delete_tmp_matches()
            self.assertEqual(status, False)
            self.assertEqual(message, 'SQLAlchemy: DB not initialized properly, check: SQLALCHEMY_URL')

            # exception within replace_tmp_with_canonical
            status, message = replace_tmp_with_canonical()
            self.assertEqual(status, False)
            self.assertEqual(message, 'SQLAlchemy: DB not initialized properly, check: SQLALCHEMY_URL')

            # exception within delete_multi_matches
            status, message = delete_multi_matches()
            self.assertEqual(status, False)
            self.assertEqual(message, 'SQLAlchemy: DB not initialized properly, check: SQLALCHEMY_URL')

            # exception within get_tmp_bibcodes
            results, message = get_tmp_bibcodes()
            self.assertEqual(results, None)
            self.assertEqual(message, 'SQLAlchemy: DB not initialized properly, check: SQLALCHEMY_URL')

            # exception within get_muti_matches
            results, message = get_muti_matches()
            self.assertEqual(results, None)
            self.assertEqual(message, 'SQLAlchemy: DB not initialized properly, check: SQLALCHEMY_URL')

    def test_delete_tmp_matches(self):
        """

        """
        # add stub data and verify that there are 3 records in db
        self.add_docmatch_data()
        result, status_code = query_docmatch({'start': 0, 'rows':10, 'date_cutoff': get_date('1972/01/01 00:00:00')})
        self.assertEqual(status_code, 200)
        self.assertEqual(len(result), 3)

        # add duplicate matches, one with tmp bibcode and one with canonical bibcode, to the database
        duplicate_matches = [
            {
                'source_bibcode': '2023arXiv230410160K',
                'matched_bibcode': '2023MNRAS.tmp.1147K',
                'confidence': 0.9957017
            },                 {
                'source_bibcode': '2023arXiv230410160K',
                'matched_bibcode': '2023MNRAS.522.3648K',
                'confidence': 0.9957017
            },
        ]
        for match in duplicate_matches:
            add_a_record(match)

        # verify that there are 5 matches in db
        result, status_code = query_docmatch({'start': 0, 'rows':10, 'date_cutoff': get_date('1972/01/01 00:00:00')})
        self.assertEqual(status_code, 200)
        self.assertEqual(len(result), 5)

        # call delete_tmp_matches to remove tmp bibcode that also have canonical bibcode match
        # verify that one record was deleted
        count, status = delete_tmp_matches()
        self.assertEqual(count, 1)
        self.assertEqual(status, '')

        # call again and verify that no record was deleted
        count, status = delete_tmp_matches()
        self.assertEqual(count, 0)
        self.assertEqual(status, '')

        # verify that now there are 4 records in the db
        result, status_code = query_docmatch({'start': 0, 'rows':10, 'date_cutoff': get_date('1972/01/01 00:00:00')})
        self.assertEqual(status_code, 200)
        self.assertEqual(len(result), 4)

        # verify that the tmp bibcode does not exists in db anymore, only the canonical
        result = get_a_record(source_bibcode='2023arXiv230410160K', matched_bibcode='2023MNRAS.tmp.1147K')
        self.assertNotEqual(result['pub_bibcode'], '2023MNRAS.tmp.1147K')
        self.assertEqual(result['pub_bibcode'], '2023MNRAS.522.3648K')

        self.delete_docmatch_data()

    def test_replace_tmp_with_canonical(self):
        """

        """
        self.add_docmatch_data()
        self.add_confidence_lookup_data()

        # test when there is no record to replace
        count, status = replace_tmp_with_canonical()
        self.assertEqual(count, 0)
        self.assertEqual(status, '')

        # add matches with tmp bibcodes
        tmp_matches = [
            {
                'source_bibcode': '2023arXiv230410160K',
                'matched_bibcode': '2023MNRAS.tmp.1147K',
                'confidence': 0.9957017
            },{
                'source_bibcode': '2023arXiv230602536C',
                'matched_bibcode': '2023MNRAS.tmpL..73C',
                'confidence': 0.9961402
            },{
                'source_bibcode': '2023arXiv230603140V',
                'matched_bibcode': '2023MNRAS.tmp.1672V',
                'confidence': 0.9942136
            },{
                'source_bibcode': '2023arXiv230603140V',
                'matched_bibcode': '2023MNRAS.523.4624V',
                'confidence': 0.9942136
            }
        ]
        for match in tmp_matches:
            add_a_record(match)

        # now test when there are records to replace
        docs = [
            {'bibcode': '2023MNRAS.522.3648K',
            'identifier': ['2023MNRAS.522.3648K', 'arXiv:2304.10160', '2023arXiv230410160K', '2023MNRAS.tmp.1147K',
                         '10.1093/mnras/stad1181', '10.48550/arXiv.2304.10160']},
            {'bibcode': '2023MNRAS.524L..61C',
            'identifier': ['arXiv:2306.02536', '10.1093/mnrasl/slad072', '2023arXiv230602536C',
                         '10.48550/arXiv.2306.02536', '2023MNRAS.524L..61C', '2023MNRAS.tmpL..73C']},
            {'bibcode': '2023MNRAS.523.4624V',
            'identifier': ['10.1093/mnras/stad1719', '2023arXiv230603140V', '10.48550/arXiv.2306.03140', '2023MNRAS.tmp.1672V',
                        '2023MNRAS.523.4624V', 'arXiv:2306.03140']},
        ]
        with mock.patch('oraclesrv.utils.get_solr_data_chunk', return_value=[docs, 200]):
            count, status = replace_tmp_with_canonical()
            self.assertEqual(count, 3)
            self.assertEqual(status, '')

        # verify the updates
        record = get_a_record('2023arXiv230410160K', '2023MNRAS.522.3648K')
        self.assertEqual(record['eprint_bibcode'], '2023arXiv230410160K')
        self.assertEqual(record['pub_bibcode'], '2023MNRAS.522.3648K')
        self.assertEqual(record['confidence'], 0.9957017)
        record = get_a_record('2023arXiv230602536C', '2023MNRAS.524L..61C')
        self.assertEqual(record['eprint_bibcode'], '2023arXiv230602536C')
        self.assertEqual(record['pub_bibcode'], '2023MNRAS.524L..61C')
        self.assertEqual(record['confidence'], 0.9961402)
        record = get_a_record('2023arXiv230603140V', '2023MNRAS.tmp.1672V')
        self.assertEqual(record['eprint_bibcode'], '2023arXiv230603140V')
        self.assertEqual(record['pub_bibcode'], '2023MNRAS.523.4624V')
        self.assertEqual(record['confidence'], 0.9942136)

        self.delete_confidence_lookup_data()
        self.delete_docmatch_data()

    def test_delete_multi_matches(self):
        """

        """
        self.add_docmatch_data()

        # add multiple matches
        # note that there can be multiple low values (ie, two or more matches with confidence -1)
        # also note that there could be multi matches for a specific eprint or multi matches for specific pub
        # both sides needs to be checked and extra matches deleted
        multi_matches = [
            {
                'source_bibcode': '2019arXiv190102008A',
                'matched_bibcode': '2018ADNDT.123..168A',
                'confidence': -1
            },{
                'source_bibcode': '2019arXiv190102008A',
                'matched_bibcode': '2019ADNDT.125..226A',
                'confidence': -1
            },{
                'source_bibcode': '2019arXiv190102008A',
                'matched_bibcode': '2019ADNDT.127...22A',
                'confidence': 0.9858069
            },{
                'source_bibcode': '2022arXiv220500682A',
                'matched_bibcode': '2023PhRvC.107e4904A',
                'confidence': 0.7222667
            },{
                'source_bibcode': '2022arXiv220500682A',
                'matched_bibcode': '2023PhRvC.107e4908A',
                'confidence': 0.9833502
            },{
                'source_bibcode': '2020arXiv201201581C',
                'matched_bibcode': '2019PhRvD..99c2011S',
                'confidence': 0.56
            },{
                'source_bibcode': '2020arXiv201201581C',
                'matched_bibcode': '2021PhRvD.104a2008C',
                'confidence': 0.78
            },{
                'source_bibcode': '2020arXiv201201581C',
                'matched_bibcode': '2021PhRvD.104a2015S',
                'confidence': 0.9681432
            },{
                'source_bibcode': '2021arXiv210205495L',
                'matched_bibcode': '2021EPJC...81..489L',
                'confidence': -1
            },{
                'source_bibcode': '2021arXiv210205551L',
                'matched_bibcode': '2021EPJC...81..489L',
                'confidence': 1.3
            },{
                'source_bibcode': '2021arXiv210912660B',
                'matched_bibcode': '2022JHEP...09..242B',
                'confidence': 1.3
            },{
                'source_bibcode': '2020arXiv201201581C',
                'matched_bibcode': '2022arXiv220306688',
                'confidence': -1
            }
        ]
        for match in multi_matches:
            add_a_record(match)

        count, status = delete_multi_matches()
        self.assertEqual(count, 7)
        self.assertEqual(status, '')

        self.delete_docmatch_data()

    def test_clean_db(self):
        """

        """
        self.add_docmatch_data()

        counts, status = clean_db()
        self.assertEqual(counts, {'count_deleted_tmp': 0, 'count_updated_canonical': 0, 'count_deleted_multi_matches': 0})
        self.assertEqual(status, '')

        self.delete_docmatch_data()

    def test_get_tmp_bibcodes(self):
        """

        """
        self.add_docmatch_data()

        # add matches with tmp bibcodes
        tmp_matches = [
            {
                'source_bibcode': '2023arXiv230410160K',
                'matched_bibcode': '2023MNRAS.tmp.1147K',
                'confidence': 0.9957017
            },{
                'source_bibcode': '2023arXiv230602536C',
                'matched_bibcode': '2023MNRAS.tmpL..73C',
                'confidence': 0.9961402
            },{
                'source_bibcode': '2023arXiv230603140V',
                'matched_bibcode': '2023MNRAS.tmp.1672V',
                'confidence': 0.9942136
            }
        ]
        for match in tmp_matches:
            add_a_record(match)

        results, status = get_tmp_bibcodes()
        self.assertEqual(results, [('2023arXiv230410160K', '2023MNRAS.tmp.1147K', 0.9957017),
                                   ('2023arXiv230602536C', '2023MNRAS.tmpL..73C', 0.9961402),
                                   ('2023arXiv230603140V', '2023MNRAS.tmp.1672V', 0.9942136)])
        self.assertEqual(status, 200)

        self.delete_docmatch_data()

    def test_get_muti_matches(self):
        """

        """
        self.add_docmatch_data()

        multi_matches = [
            {
                'source_bibcode': '2019arXiv190102008A',
                'matched_bibcode': '2018ADNDT.123..168A',
                'confidence': -1
            },{
                'source_bibcode': '2019arXiv190102008A',
                'matched_bibcode': '2019ADNDT.125..226A',
                'confidence': -1
            },{
                'source_bibcode': '2019arXiv190102008A',
                'matched_bibcode': '2019ADNDT.127...22A',
                'confidence': 0.9858069
            },{
                'source_bibcode': '2022arXiv220500682A',
                'matched_bibcode': '2023PhRvC.107e4904A',
                'confidence': 0.7222667
            },{
                'source_bibcode': '2022arXiv220500682A',
                'matched_bibcode': '2023PhRvC.107e4908A',
                'confidence': 0.9833502
            },{
                'source_bibcode': '2020arXiv201201581C',
                'matched_bibcode': '2019PhRvD..99c2011S',
                'confidence': 0.56
            },{
                'source_bibcode': '2020arXiv201201581C',
                'matched_bibcode': '2021PhRvD.104a2008C',
                'confidence': 0.78
            },{
                'source_bibcode': '2020arXiv201201581C',
                'matched_bibcode': '2021PhRvD.104a2015S',
                'confidence': 0.9681432
            },{
                'source_bibcode': '2021arXiv210205495L',
                'matched_bibcode': '2021EPJC...81..489L',
                'confidence': -1
            },{
                'source_bibcode': '2021arXiv210205551L',
                'matched_bibcode': '2021EPJC...81..489L',
                'confidence': 1.3
            },{
                'source_bibcode': '2021arXiv210912660B',
                'matched_bibcode': '2022JHEP...09..242B',
                'confidence': 1.3
            },{
                'source_bibcode': '2020arXiv201201581C',
                'matched_bibcode': '2022arXiv220306688',
                'confidence': -1
            }
        ]
        for match in multi_matches:
            add_a_record(match)

        results, status = get_muti_matches()
        self.assertEqual(results, [('2019arXiv190102008A', '2018ADNDT.123..168A', -1.0),
                                   ('2019arXiv190102008A', '2019ADNDT.125..226A', -1.0),
                                   ('2019arXiv190102008A', '2019ADNDT.127...22A', 0.9858069),
                                   ('2020arXiv201201581C', '2019PhRvD..99c2011S', 0.56),
                                   ('2020arXiv201201581C', '2021PhRvD.104a2008C', 0.78),
                                   ('2020arXiv201201581C', '2021PhRvD.104a2015S', 0.9681432),
                                   ('2020arXiv201201581C', '2022arXiv220306688', -1.0),
                                   ('2021arXiv210205495L', '2021EPJC...81..489L', -1.0),
                                   ('2021arXiv210205551L', '2021EPJC...81..489L', 1.3),
                                   ('2022arXiv220500682A', '2023PhRvC.107e4904A', 0.7222667),
                                   ('2022arXiv220500682A', '2023PhRvC.107e4908A', 0.9833502)])
        self.assertEqual(status, 200)

        self.delete_docmatch_data()

    def test_adding_earth_science_records(self):
        """

        """
        self.add_eprint_bibstem_lookup_data()

        docmatch_data = [
                        ('2017EaArX....2FDCTH', '2018Litho.314..360H', 1.3),
                        ('2017EaArX....2RGV5B', '2013ChGeo.347...82B', 1.3),
                        ('2016ESRv..155...49L', '2017EaArX....3T65DL', 1.3),
        ]

        docmatch_records = []
        for record in docmatch_data:
            docmatch_record = {'source_bibcode': record[0],
                               'matched_bibcode': record[1],
                               'confidence': record[2]}
            docmatch_records.append(docmatch_record)

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        response = self.client.put('/add', data=json.dumps(docmatch_records), headers=headers)
        self.assertEqual(response._status_code, 200)
        self.assertEqual(response.json['status'], 'updated db with new data successfully')

        self.delete_docmatch_data()

    def test_add_unrecognizable_match(self):
        """

        """
        self.add_eprint_bibstem_lookup_data()

        docmatch_data = [
                        ('2017EaarX....2FDCTH', '2018Litho.314..360H', 1.3),
        ]

        docmatch_records = []
        for record in docmatch_data:
            docmatch_record = {'source_bibcode': record[0],
                               'matched_bibcode': record[1],
                               'confidence': record[2]}
            docmatch_records.append(docmatch_record)

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        response = self.client.put('/add', data=json.dumps(docmatch_records), headers=headers)
        self.assertEqual(response._status_code, 400)
        self.assertEqual(response.json['error'], 'Error: Invalid EPrint Bibcode.')

        self.delete_docmatch_data()


if __name__ == "__main__":
    unittest.main()
