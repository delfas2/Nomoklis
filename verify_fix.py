import os
import django
from django.conf import settings
from django.template.loader import render_to_string
from django.test import TestCase
from django.contrib.auth.models import User
from nomoklis_app.models import Property, PropertyImage, Profile

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Nomoklis.settings')
django.setup()

class PropertyDetailPopupTest(TestCase):
    def setUp(self):
        # Create a user for the property owner
        self.owner_user = User.objects.create_user(username='owner', password='password')
        self.owner_profile = Profile.objects.create(user=self.owner_user, user_type='nuomotojas')

        # Create a property
        self.property = Property.objects.create(
            owner=self.owner_user,
            street='Test Street',
            house_number='1',
            city='Test City',
            rent_price=500,
        )
        # Create a property image
        self.image = PropertyImage.objects.create(property=self.property, image='test_image.jpg')

    def test_property_detail_popup_with_image(self):
        # Prepare context for the template
        context = {'property': self.property}
        
        # Render the template
        html = render_to_string('nomoklis_app/_property_detail_popup.html', context)

        # Check if the main image is correctly set
        expected_image_url = self.image.image.url
        self.assertIn(f'mainImage: \'{expected_image_url}\'', html)

    def test_property_detail_popup_no_image(self):
        # Create a property with no images
        property_no_image = Property.objects.create(
            owner=self.owner_user,
            street='No Image Street',
            rent_price=600,
        )
        context = {'property': property_no_image}

        # Render the template
        html = render_to_string('nomoklis_app/_property_detail_popup.html', context)
        
        # Check if the placeholder is used
        self.assertIn('mainImage: \'https://placehold.co/600x400/e2e8f0/64748b?text=Nėra+nuotraukos\'', html)

if __name__ == '__main__':
    import unittest
    unittest.main()