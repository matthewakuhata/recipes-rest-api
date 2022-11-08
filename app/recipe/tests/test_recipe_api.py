"""
Tests for recipe APIs
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APIClient

from core.models import Recipe

from recipe.serializers import RecipeSerializer

RECIPES_URL = reverse('recipe:recipe-list')
def create_recipe(user, **params):
    """Create and Return a sample recipe"""
    default = {
        'title': 'Sample title',
        'time_minutes': 22,
        'price': Decimal('5.24'),
        'description': 'default description',
        'link': 'http://example.com/example',
    }
    default.update(params)

    recipe = recipe.objects.create(user=user, **default)
    return recipe

class PublicRecipeAPITests(TestCase):
    """Test unaithenticated API requests"""

    def setUp(self):
        """Test auth is required"""
        res = self.client(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeAPITests(TestCase):
    """Test authenticated API requests"""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().object.create_user(
            'user@example.com',
            'testpassword'
        )
        self.client.force_authenticate(self.user)

    def test_retrive_recipes(self):
        "Test retrieving a list of recipes"
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.object.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """Test list of recipes is limited to authenticated user"""
        new_user = get_user_model().object.create_user(
            'user2@example.com',
            'testpassword'
        )
        create_recipe(user=new_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.object.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)


