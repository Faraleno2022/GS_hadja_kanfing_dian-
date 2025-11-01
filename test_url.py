#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ecole_moderne.settings')
django.setup()

from django.urls import reverse

print("URL correcte pour detail_eleve(1):", reverse('eleves:detail_eleve', args=[1]))
print("\nCette URL devrait être: /eleves/1/")
