import sys
sys.path.append('/app')

try:
    from nomoklis_app import views
    print("✓ views.py imports successfully")
    
    # Check if stats_view exists
    if hasattr(views, 'stats_view'):
        print("✓ stats_view function exists")
    else:
        print("✗ stats_view function NOT found")
        
except SyntaxError as e:
    print(f"✗ SYNTAX ERROR in views.py: {e}")
    print(f"  Line {e.lineno}: {e.text}")
except ImportError as e:
    print(f"✗ IMPORT ERROR: {e}")
except Exception as e:
    print(f"✗ ERROR: {type(e).__name__}: {e}")
