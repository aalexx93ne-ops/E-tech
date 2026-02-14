#!/usr/bin/env python
"""
Script to generate slugs for all brands that don't have one.
Run this script to fix the brand filtering issue.
"""
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'appx.settings')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
django.setup()

from index.models import Brand

def generate_slugs():
    brands_without_slug = Brand.objects.filter(slug__isnull=True) | Brand.objects.filter(slug='')
    count = brands_without_slug.count()
    
    if count == 0:
        print("All brands already have slugs!")
        return
    
    print(f"Found {count} brands without slugs. Generating...")
    
    for brand in brands_without_slug:
        brand.save()  # This will trigger the save() method which generates the slug
        print(f"  - Generated slug '{brand.slug}' for brand '{brand.name}'")
    
    print(f"\nDone! Generated slugs for {count} brands.")

if __name__ == '__main__':
    generate_slugs()
