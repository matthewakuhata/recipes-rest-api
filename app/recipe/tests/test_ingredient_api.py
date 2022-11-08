"""
Tests for the ingredients API
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase


from rest_framework import status
from rest_framework.test import APIClient


from core.models import Ingredient


from recipe.serializers import IngredientSerializer


INGREDIENTS_URL = reverse('recipe:ingredient-list')


def detail_url(tag_id):
    return reverse('recipe:ingredient-detail', args=[tag_id])


def create_user(email='example.com@example.com', password='test123'):
    return get_user_model().objects.create_user(email=email, password=password)


class PublicIngredientsAPITests(TestCase):
    """Test unauthenticated API Requests"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required"""
        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsAPITest(TestCase):
    """Test Authenticated API requests"""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_get_ingredients(self):
        Ingredient.objects.create(user=self.user, name='Kale')
        Ingredient.objects.create(user=self.user, name='Vanilla')

        res = self.client.get(INGREDIENTS_URL)

        ingredients = Ingredient.objects.all().order_by('-name')
        serializer = IngredientSerializer(ingredients, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_ingredients_limited_by_user(self):
        user2 = create_user(email='example2@example.com')
        expected = Ingredient.objects.create(user=self.user, name='Kale')

        Ingredient.objects.create(user=user2, name='Vanilla')

        res = self.client.get(INGREDIENTS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], expected.name)
        self.assertEqual(res.data[0]['id'], expected.id)

    def test_update_ingredient(self):
        """Test update ingredient"""
        ingredient = Ingredient.objects.create(user=self.user, name='Kale')

        payload = {'name': 'Lettuce'}
        url = detail_url(ingredient.id)
        res = self.client.patch(url, payload)

        ingredient.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(ingredient.name, payload['name'])

    def test_delete_ingredient(self):
        """Test delete ingredient"""
        ingredient = Ingredient.objects.create(user=self.user, name='Kale')

        url = detail_url(ingredient.id)
        res = self.client.delete(url)

        ingredients = Ingredient.objects.filter(user=self.user)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(ingredients.exists())
