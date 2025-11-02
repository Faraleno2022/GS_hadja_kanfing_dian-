from django.db import models
from django.contrib.auth.models import User
from eleves.models import Ecole
from decimal import Decimal

class ClasseNote(models.Model):
    """Classe pour la gestion des notes"""
    NIVEAUX_CHOICES = [
        ('GARDERIE', 'Garderie'),
        ('MATERNELLE', 'Maternelle'),
        ('PRIMAIRE_1', 'Primaire 1ère'),
        ('PRIMAIRE_2', 'Primaire 2ème'),
        ('PRIMAIRE_3', 'Primaire 3ème'),
        ('PRIMAIRE_4', 'Primaire 4ème'),
        ('PRIMAIRE_5', 'Primaire 5ème'),
        ('PRIMAIRE_6', 'Primaire 6ème'),
        ('COLLEGE_7', 'Collège 7ème'),
        ('COLLEGE_8', 'Collège 8ème'),
        ('COLLEGE_9', 'Collège 9ème'),
        ('COLLEGE_10', 'Collège 10ème'),
        ('LYCEE_11', 'Lycée 11ème'),
        ('LYCEE_12', 'Lycée 12ème'),
        ('TERMINALE', 'Terminale'),
    ]
    
    NIVEAU_ENSEIGNEMENT_CHOICES = [
        ('MATERNELLE', 'Maternelle'),
        ('PRIMAIRE', 'Primaire'),
        ('SECONDAIRE', 'Secondaire'),
    ]
    
    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, related_name='classes_notes')
    nom = models.CharField(max_length=100, verbose_name="Nom de la classe")
    niveau = models.CharField(max_length=20, choices=NIVEAUX_CHOICES, verbose_name="Niveau")
    niveau_enseignement = models.CharField(max_length=20, choices=NIVEAU_ENSEIGNEMENT_CHOICES, default='SECONDAIRE', verbose_name="Niveau d'enseignement")
    annee_scolaire = models.CharField(max_length=9, verbose_name="Année scolaire", help_text="Format: 2024-2025")
    effectif = models.PositiveIntegerField(default=0, verbose_name="Effectif")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    actif = models.BooleanField(default=True, verbose_name="Active")
    
    cree_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='classes_notes_creees')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Classe (Notes)"
        verbose_name_plural = "Classes (Notes)"
        ordering = ['niveau', 'nom']
        unique_together = ['ecole', 'nom', 'annee_scolaire']
    
    def __str__(self):
        return f"{self.nom} - {self.get_niveau_display()} ({self.annee_scolaire})"

class MatiereNote(models.Model):
    """Matière avec coefficient pour une classe"""
    classe = models.ForeignKey(ClasseNote, on_delete=models.CASCADE, related_name='matieres')
    nom = models.CharField(max_length=100, verbose_name="Nom de la matière")
    code = models.CharField(max_length=20, verbose_name="Code", help_text="Ex: MATH, FR, ANG")
    coefficient = models.DecimalField(max_digits=4, decimal_places=2, default=1.0, verbose_name="Coefficient")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    actif = models.BooleanField(default=True, verbose_name="Active")
    
    cree_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='matieres_notes_creees')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Matière (Notes)"
        verbose_name_plural = "Matières (Notes)"
        ordering = ['nom']
        unique_together = ['classe', 'code']
    
    def __str__(self):
        return f"{self.nom} ({self.code}) - Coef: {self.coefficient}"

class Evaluation(models.Model):
    """Évaluation pour une matière"""
    TYPE_CHOICES = [
        ('DEVOIR', 'Devoir'),
        ('COMPOSITION', 'Composition'),
        ('EXAMEN', 'Examen'),
        ('CONTROLE', 'Contrôle'),
        ('INTERROGATION', 'Interrogation'),
    ]
    
    PERIODE_CHOICES = [
        # Périodes mensuelles (système guinéen)
        ('OCTOBRE', 'Octobre'),
        ('NOVEMBRE', 'Novembre'),
        ('DECEMBRE', 'Décembre'),
        ('JANVIER', 'Janvier'),
        ('FEVRIER', 'Février'),
        ('MARS', 'Mars'),
        ('AVRIL', 'Avril'),
        ('MAI', 'Mai'),
        ('JUIN', 'Juin'),
        # Périodes trimestrielles
        ('TRIMESTRE_1', 'Trimestre 1'),
        ('TRIMESTRE_2', 'Trimestre 2'),
        ('TRIMESTRE_3', 'Trimestre 3'),
        # Périodes semestrielles
        ('SEMESTRE_1', 'Semestre 1'),
        ('SEMESTRE_2', 'Semestre 2'),
    ]
    
    matiere = models.ForeignKey(MatiereNote, on_delete=models.CASCADE, related_name='evaluations')
    titre = models.CharField(max_length=200, verbose_name="Titre de l'évaluation")
    type_evaluation = models.CharField(max_length=20, choices=TYPE_CHOICES, verbose_name="Type")
    periode = models.CharField(max_length=20, choices=PERIODE_CHOICES, verbose_name="Période")
    date_evaluation = models.DateField(verbose_name="Date de l'évaluation")
    note_sur = models.DecimalField(max_digits=5, decimal_places=2, default=20.0, verbose_name="Note sur")
    coefficient = models.DecimalField(max_digits=4, decimal_places=2, default=1.0, verbose_name="Coefficient")
    description = models.TextField(blank=True, null=True, verbose_name="Description")
    
    cree_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='evaluations_creees')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Évaluation"
        verbose_name_plural = "Évaluations"
        ordering = ['-date_evaluation']
    
    def __str__(self):
        return f"{self.titre} - {self.matiere.nom} ({self.get_periode_display()})"

class NoteEleve(models.Model):
    """Note d'un élève pour une évaluation"""
    from eleves.models import Eleve
    
    evaluation = models.ForeignKey(Evaluation, on_delete=models.CASCADE, related_name='notes')
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='notes_evaluations')
    note = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, verbose_name="Note obtenue")
    absent = models.BooleanField(default=False, verbose_name="Absent")
    commentaire = models.TextField(blank=True, null=True, verbose_name="Commentaire")
    
    cree_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='notes_saisies')
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Note élève"
        verbose_name_plural = "Notes élèves"
        ordering = ['eleve__nom', 'eleve__prenom']
        unique_together = ['evaluation', 'eleve']
    
    def __str__(self):
        if self.absent:
            return f"{self.eleve} - Absent"
        return f"{self.eleve} - {self.note}/{self.evaluation.note_sur}"
    
    @property
    def note_sur_20(self):
        """Convertir la note sur 20"""
        if self.absent:
            return 0
        return (self.note / self.evaluation.note_sur) * 20


class NoteMensuelle(models.Model):
    """Notes mensuelles pour le système guinéen (Octobre à Mai)"""
    from eleves.models import Eleve
    
    MOIS_CHOICES = [
        ('OCTOBRE', 'Octobre'),
        ('NOVEMBRE', 'Novembre'),
        ('DECEMBRE', 'Décembre'),
        ('JANVIER', 'Janvier'),
        ('FEVRIER', 'Février'),
        ('MARS', 'Mars'),
        ('AVRIL', 'Avril'),
        ('MAI', 'Mai'),
    ]
    
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='notes_mensuelles')
    matiere = models.ForeignKey(MatiereNote, on_delete=models.CASCADE, related_name='notes_mensuelles')
    mois = models.CharField(max_length=20, choices=MOIS_CHOICES, verbose_name="Mois")
    annee_scolaire = models.CharField(max_length=9, verbose_name="Année scolaire")
    note = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Note sur 20")
    absent = models.BooleanField(default=False, verbose_name="Absent")
    
    cree_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Note mensuelle"
        verbose_name_plural = "Notes mensuelles"
        ordering = ['eleve', 'matiere', 'mois']
        unique_together = ['eleve', 'matiere', 'mois', 'annee_scolaire']
    
    def __str__(self):
        if self.absent:
            return f"{self.eleve} - {self.matiere.nom} - {self.get_mois_display()} - Absent"
        return f"{self.eleve} - {self.matiere.nom} - {self.get_mois_display()} - {self.note}/20"


class CompositionNote(models.Model):
    """Notes de composition pour le système guinéen"""
    from eleves.models import Eleve
    
    PERIODE_CHOICES = [
        ('SEMESTRE_1', 'Semestre 1'),
        ('SEMESTRE_2', 'Semestre 2'),
        ('TRIMESTRE_1', 'Trimestre 1'),
        ('TRIMESTRE_2', 'Trimestre 2'),
        ('TRIMESTRE_3', 'Trimestre 3'),
    ]
    
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='compositions')
    matiere = models.ForeignKey(MatiereNote, on_delete=models.CASCADE, related_name='compositions')
    periode = models.CharField(max_length=20, choices=PERIODE_CHOICES, verbose_name="Période")
    annee_scolaire = models.CharField(max_length=9, verbose_name="Année scolaire")
    note = models.DecimalField(max_digits=5, decimal_places=2, verbose_name="Note sur 20")
    absent = models.BooleanField(default=False, verbose_name="Absent")
    
    cree_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Note de composition"
        verbose_name_plural = "Notes de composition"
        ordering = ['eleve', 'matiere', 'periode']
        unique_together = ['eleve', 'matiere', 'periode', 'annee_scolaire']
    
    def __str__(self):
        if self.absent:
            return f"{self.eleve} - {self.matiere.nom} - {self.get_periode_display()} - Absent"
        return f"{self.eleve} - {self.matiere.nom} - {self.get_periode_display()} - {self.note}/20"


class AppreciationMaternelle(models.Model):
    """Appréciations qualitatives pour la maternelle"""
    from eleves.models import Eleve
    
    APPRECIATION_CHOICES = [
        ('TRES_BIEN_ACQUIS', 'Très Bien Acquis'),
        ('BIEN_ACQUIS', 'Bien Acquis'),
        ('EN_COURS', 'En Cours d\'Acquisition'),
        ('NON_ACQUIS', 'Non Acquis'),
    ]
    
    TRIMESTRE_CHOICES = [
        ('TRIMESTRE_1', 'Trimestre 1'),
        ('TRIMESTRE_2', 'Trimestre 2'),
        ('TRIMESTRE_3', 'Trimestre 3'),
    ]
    
    eleve = models.ForeignKey(Eleve, on_delete=models.CASCADE, related_name='appreciations_maternelle')
    matiere = models.ForeignKey(MatiereNote, on_delete=models.CASCADE, related_name='appreciations_maternelle')
    trimestre = models.CharField(max_length=20, choices=TRIMESTRE_CHOICES, verbose_name="Trimestre")
    annee_scolaire = models.CharField(max_length=9, verbose_name="Année scolaire")
    appreciation = models.CharField(max_length=20, choices=APPRECIATION_CHOICES, verbose_name="Appréciation")
    commentaire = models.TextField(blank=True, null=True, verbose_name="Commentaire")
    absent = models.BooleanField(default=False, verbose_name="Absent")
    
    cree_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Appréciation maternelle"
        verbose_name_plural = "Appréciations maternelle"
        ordering = ['eleve', 'matiere', 'trimestre']
        unique_together = ['eleve', 'matiere', 'trimestre', 'annee_scolaire']
    
    def __str__(self):
        if self.absent:
            return f"{self.eleve} - {self.matiere.nom} - {self.get_trimestre_display()} - Absent"
        return f"{self.eleve} - {self.matiere.nom} - {self.get_trimestre_display()} - {self.get_appreciation_display()}"


class ThemeBulletin(models.Model):
    """Personnalisation des couleurs du bulletin"""
    
    nom = models.CharField(max_length=100, verbose_name="Nom du thème")
    ecole = models.ForeignKey(Ecole, on_delete=models.CASCADE, related_name='themes_bulletin', null=True, blank=True)
    
    # Couleurs principales
    couleur_primaire = models.CharField(max_length=7, default='#2c3e50', verbose_name="Couleur primaire", help_text="Ex: #2c3e50")
    couleur_secondaire = models.CharField(max_length=7, default='#3498db', verbose_name="Couleur secondaire", help_text="Ex: #3498db")
    couleur_accent = models.CharField(max_length=7, default='#e74c3c', verbose_name="Couleur accent", help_text="Ex: #e74c3c")
    
    # Couleurs de texte
    couleur_texte_principal = models.CharField(max_length=7, default='#2c3e50', verbose_name="Texte principal")
    couleur_texte_secondaire = models.CharField(max_length=7, default='#7f8c8d', verbose_name="Texte secondaire")
    
    # Couleurs de fond
    couleur_fond_header = models.CharField(max_length=7, default='#2c3e50', verbose_name="Fond en-tête")
    couleur_fond_tableau = models.CharField(max_length=7, default='#ecf0f1', verbose_name="Fond tableau")
    couleur_fond_carte = models.CharField(max_length=7, default='#ffffff', verbose_name="Fond cartes")
    
    # Couleurs des bordures
    couleur_bordure = models.CharField(max_length=7, default='#bdc3c7', verbose_name="Bordures")
    
    # Couleurs des mentions
    couleur_mention_tb = models.CharField(max_length=7, default='#27ae60', verbose_name="Mention Très Bien")
    couleur_mention_bien = models.CharField(max_length=7, default='#3498db', verbose_name="Mention Bien")
    couleur_mention_ab = models.CharField(max_length=7, default='#f39c12', verbose_name="Mention Assez Bien")
    couleur_mention_passable = models.CharField(max_length=7, default='#e67e22', verbose_name="Mention Passable")
    couleur_mention_insuffisant = models.CharField(max_length=7, default='#e74c3c', verbose_name="Mention Insuffisant")
    
    # Paramètres
    actif = models.BooleanField(default=False, verbose_name="Thème actif")
    par_defaut = models.BooleanField(default=False, verbose_name="Thème par défaut")
    
    cree_par = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Thème de bulletin"
        verbose_name_plural = "Thèmes de bulletin"
        ordering = ['-par_defaut', '-actif', 'nom']
    
    def __str__(self):
        return f"{self.nom}" + (" (Actif)" if self.actif else "") + (" (Par défaut)" if self.par_defaut else "")
    
    def save(self, *args, **kwargs):
        # Si ce thème est marqué comme par défaut, désactiver les autres
        if self.par_defaut:
            ThemeBulletin.objects.filter(ecole=self.ecole, par_defaut=True).exclude(id=self.id).update(par_defaut=False)
        super().save(*args, **kwargs)
