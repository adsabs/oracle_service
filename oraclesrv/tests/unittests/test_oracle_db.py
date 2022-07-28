import sys, os
project_home = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../'))
if project_home not in sys.path:
    sys.path.insert(0, project_home)

import unittest
import json

import oraclesrv.app as app
from oraclesrv.tests.unittests.base import TestCaseDatabase
from oraclesrv.utils import get_a_record, del_records
from oraclesrv.score import get_matches
# , add_records, get_records_new, add_records_new, del_records_new, get_ids
# from oraclesrv.views import LinkRequest, PopulateRequest
#
# from adsmsg import DocumentRecords

class TestDatabase(TestCaseDatabase):

    def create_app(self):
        '''Start the wsgi application'''
        a = app.create_app(**{
            'SQLALCHEMY_DATABASE_URI': self.postgresql_url,
        })
        return a

    def add_stub_data(self):
        """
        Add stub data
        :return:
        """
        stub_data = [
                        ('2021arXiv210312030S', '2021CSF...15311505S', 0.9829099),
                        ('2018ConPh..59...16H', '2018ConPh..59...16H', 0.9877064),
                        ('2022NuPhB.98015830S', '2022NuPhB.98015830S', 1.97300124),
        ]

        docmatch_records = []
        for record in stub_data:
            docmatch_record = {'source_bibcode': record[0],
                               'matched_bibcode': record[1],
                               'confidence': record[2]}
            docmatch_records.append(docmatch_record)

        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
        response = self.client.put('/update', data=json.dumps(docmatch_records), headers=headers)
        self.assertEqual(response._status_code, 200)
        self.assertEqual(response.json['status'], 'updated db with new data successfully')


    def test_get_a_record(self):
        """
        test querying db for a record
        :return:
        """
        self.add_stub_data()

        # query for a record that exists
        record = get_a_record('2021arXiv210312030S', '2021CSF...15311505S')
        self.assertEqual(record['source_bibcode'], '2021arXiv210312030S')
        self.assertEqual(record['matched_bibcode'], '2021CSF...15311505S')
        self.assertEqual(record['confidence'], 0.9829099)

        # query for a record that does not exits
        record = get_a_record('2021arXiv210312030G', '2021CSF...15311505G')
        self.assertEqual(record, None)

    def test_del_records(self):
        """
        test querying db for a record
        :return:
        """
        self.add_stub_data()

        docmatch_records = [
            {
                "source_bibcode": "2021arXiv210312030S",
                "matched_bibcode": "2021CSF...15311505S",
                "confidence": 0.9829099
            }, {
                "source_bibcode": "2018ConPh..59...16H",
                "matched_bibcode": "2018ConPh..59...16H",
                "confidence": 0.9877064
            }, {
                "source_bibcode": "2022NuPhB.98015830S",
                "matched_bibcode": "2022NuPhB.98015830S",
                "confidence": 1.97300124
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

    def test_docmatch(self):
        """
        test matching a record and compute the score
        :return:
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

        # case when multiple arXiv can be matched against one one publisher
        # best match for this second arXiv paper is the publisher's first paper, the publisher's second paper not yet published
        best_match = {'source_bibcode': '2022arXiv220606316S',
                      'matched_bibcode': '2021CSF...15311505S',
                      'confidence': '0.7259934',
                      'matched': 1,
                      'scores': {'abstract': 0.76, 'title': 0.98, 'author': 1, 'year': 1}}
        matches = get_matches(source_bibcode, abstract, title, author, year, matched_docs)
        self.assertEqual(len(matches), 1)
        self.assertDictEqual(matches[0], best_match)

        # now insert the match of first arXiv paper and first publisher to the db
        self.add_stub_data()

        # now attempting to get a match returns nothing
        matches = get_matches(source_bibcode, abstract, title, author, year, matched_docs)
        print(matches)
        self.assertEqual(len(matches), 0)
        self.assertEqual(matches, [])
