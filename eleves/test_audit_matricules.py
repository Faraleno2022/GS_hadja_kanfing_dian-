from types import SimpleNamespace
from django.test import SimpleTestCase
from .models import _code_classe_from_nom_ou_niveau, _normalize_code_prefixe


class CodesMatriculesAuditTests(SimpleTestCase):
    def test_code_classe_nom_niveau_et_code_personnalise(self):
        cases = [
            ('1ère année', '', '', 'PN1'),
            ('  2ÈME   ANNÉE ', '', '', 'PN2'),
            ('Petite section A', 'PETITE_SECTION', '', 'MPS'),
            ('Moyenne section B', 'MOYENNE_SECTION', '', 'MMS'),
            ('Grande section C', 'GRANDE_SECTION', '', 'MGS'),
            ('7ème année A', 'COLLEGE_7', '', 'CN7'),
            ('11ème série littéraire', 'LYCEE_11', '', 'L11SL'),
            ('Classe A', '', ' PERSO ', 'PERSO'),
            ('Inconnue', '', '', ''),
        ]
        for nom, niveau, code_matricule, attendu in cases:
            with self.subTest(nom=nom):
                self.assertEqual(_code_classe_from_nom_ou_niveau(SimpleNamespace(nom=nom, niveau=niveau, code_matricule=code_matricule)), attendu)

    def test_prefixe_ecole_ne_se_repete_pas(self):
        self.assertEqual(_normalize_code_prefixe(' ECOLE/ECOLE/ '), 'ECOLE/')
        self.assertEqual(_normalize_code_prefixe(None), '')
