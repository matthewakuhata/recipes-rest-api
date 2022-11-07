"""
Tests for the user API
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APIClient
from rest_framework import status

CREATE_USER_URL = reverse('user:create')
TOKEN_URL = reverse('user:token')

def create_user(**params):
    """Create and return a user"""
    return get_user_model().objects.create_user(**params)


class PublicUserAPITests(TestCase):
    """Test the public feature of the user API"""

    def setUp(self):
        self.client = APIClient()

    def test_create_user_success(self):
        """Test creating a user is successful"""

        payload = {
            'email': 'test@example.com',
            'password': 'abdwc123VFe1$',
            'name': 'Test Name'
        }

        res = self.client.post(CREATE_USER_URL, payload)
        user = get_user_model().objects.get(email=payload['email'])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(user.check_password(payload['password']))
        self.assertNotIn('password', res.data)

    def test_user_with_email_exists_error(self):
        """Test error return if user with email exists."""

        payload = {
            'email': 'test@example.com',
            'password': 'abdwc123VFe1$',
            'name': 'Test Name'
        }
        create_user(**payload)
        res = self.client.post(CREATE_USER_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short(self):
        """Test an error is returned when password is too short"""

        payload = {
            'email': 'test@example.com',
            'password': 'ab',
            'name': 'Test Name'
        }
        res = self.client.post(CREATE_USER_URL, payload)
        user_exists = get_user_model()\
            .objects\
            .filter(email=payload['email'])\
            .exists()

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """Test generates token for valid credentials"""

        user_details = {
            'email': 'test@example.com',
            'password': 'asdf1234',
            'name': 'Test Name'
        }
        create_user(**user_details)

        payload = {
            'email': 'test@example.com',
            'password': 'asdf1234',
        }

        res = self.client.post(TOKEN_URL, payload)

        self.assertIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_create_token_bad_credentials(self):
        """Test returns error if credentials invalid"""

        user_details = {
            'email': 'test@example.com',
            'password': 'asdf1234',
            'name': 'Test Name'
        }
        create_user(**user_details)

        payload = {
            'email': 'test@example.com',
            'password': 'asdf1234ff',
        }

        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_blank_password(self):
        """Testing blank password returns error"""

        payload = {
            'email': 'test@example.com',
            'password': '',
        }

        res = self.client.post(TOKEN_URL, payload)

        self.assertNotIn('token', res.data)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

