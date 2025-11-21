import os
import sys
import django

# Setup Django environment
sys.path.append('/Users/justinaszamarys/Library/Mobile Documents/com~apple~CloudDocs/_Python_duomenys/docker_Nomoklis/Nomoklis')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Nomoklis.settings')
django.setup()

try:
    from nomoklis_app.services import generate_invoice
    print("Successfully imported generate_invoice")
except NameError as e:
    print(f"Import failed: {e}")
except Exception as e:
    print(f"An error occurred during import: {e}")
