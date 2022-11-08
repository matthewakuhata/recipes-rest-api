"""
Tests for recipe APIs.
"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


from rest_framework import status
from rest_framework.test import APIClient


from core.models import (Recipe, Tag, Ingredient)


from recipe.serializers import (RecipeSerializer, RecipeDetailSerializer)


RECIPES_URL = reverse('recipe:recipe-list')


def detail_url(recipe_id):
    """Create recipe detail URL"""
    return reverse('recipe:recipe-detail', args=[recipe_id])


def create_recipe(user, **params):
    """Create and return a sample recipe."""
    defaults = {
        'title': 'Sample recipe title',
        'time_minutes': 22,
        'price': Decimal('5.25'),
        'description': 'Sample description',
        'link': 'http://example.com/recipe.pdf',
    }
    defaults.update(params)

    recipe = Recipe.objects.create(user=user, **defaults)
    return recipe


def create_user(**params):
    """Create and return a user"""
    return get_user_model().objects.create_user(**params)


class PublicRecipeAPITests(TestCase):
    """Test unauthenticated API requests."""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required to call API."""
        res = self.client.get(RECIPES_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateRecipeApiTests(TestCase):
    """Test authenticated API requests."""

    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            'user@example.com',
            'testpass123',
        )
        self.client.force_authenticate(self.user)

    def test_retrieve_recipes(self):
        """Test retrieving a list of recipes."""
        create_recipe(user=self.user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.all().order_by('-id')
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_recipe_list_limited_to_user(self):
        """Test list of recipes is limited to authenticated user."""
        other_user = create_user(
            email='other@example.com',
            password='password123',
        )
        create_recipe(user=other_user)
        create_recipe(user=self.user)

        res = self.client.get(RECIPES_URL)

        recipes = Recipe.objects.filter(user=self.user)
        serializer = RecipeSerializer(recipes, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_get_recipe_detail(self):
        """Test get recipe detail."""
        recipe = create_recipe(user=self.user)

        url = detail_url(recipe.id)
        res = self.client.get(url)

        serializer = RecipeDetailSerializer(recipe)
        self.assertEqual(res.data, serializer.data)

    def test_create_recipe(self):
        """Test creating a recipe"""
        payload = {
            'title': 'Sample recipe title',
            'time_minutes': 12,
            'price': Decimal('5.65'),
            'description': 'abc description',
            'link': 'http://examplezz.com/recipe.pdf',
        }

        res = self.client.post(RECIPES_URL, payload)
        recipe = Recipe.objects.get(id=res.data['id'])

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for k, v in payload.items():
            self.assertEqual(getattr(recipe, k), v)
        self.assertEqual(recipe.user, self.user)

    def test_partial_update(self):
        original_link = 'https://example.com'
        recipe = create_recipe(
            user=self.user,
            link=original_link
        )

        payload = {'title': 'new title'}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload)

        recipe.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.title, payload['title'])
        self.assertEqual(recipe.link, original_link)
        self.assertEqual(recipe.user, self.user)

    def test_full_update(self):
        recipe_params = {
            'title': 'Sample recipe title',
            'time_minutes': 22,
            'price': Decimal('5.25'),
            'description': 'Sample description',
            'link': 'http://example.com/recipe.pdf',
        }

        recipe = create_recipe(self.user, **recipe_params)

        update_payload = {
            'title': 'Sample recipe title2',
            'time_minutes': 222,
            'price': Decimal('25.25'),
            'description': 'Sample2 description',
            'link': 'http://example2.com/recipe.pdf',
        }
        url = detail_url(recipe.id)
        res = self.client.put(url, update_payload)

        recipe.refresh_from_db()

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(self.user, recipe.user)
        for key, value in update_payload.items():
            self.assertEqual(getattr(recipe, key), value)

    def test_update_user_returns_error(self):
        new_user = create_user(
            email='example.example@example.com',
            password='abc123',
        )
        recipe = create_recipe(user=self.user)

        payload = {'user': new_user.id}
        url = detail_url(recipe.id)
        self.client.patch(url, payload)

        recipe.refresh_from_db()
        self.assertEqual(recipe.user, self.user)

    def test_delete_recipe(self):
        recipe = create_recipe(self.user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(Recipe.objects.filter(id=recipe.id).exists())

    def test_other_users_recipe_error(self):
        new_user = create_user(
            email="example@example.com",
            password='asdfasdf',
        )
        recipe = create_recipe(new_user)

        url = detail_url(recipe.id)
        res = self.client.delete(url)

        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)
        self.assertTrue(Recipe.objects.filter(id=recipe.id).exists())

    def test_create_recipe_with_new_tags(self):
        payload = {
            'title': 'Sample recipe title2',
            'time_minutes': 222,
            'price': Decimal('25.25'),
            'description': 'Sample2 description',
            'link': 'http://example2.com/recipe.pdf',
            'tags': [{'name': 'Thai'}, {'name': 'Dinner'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        recipes = Recipe.objects.filter(user=self.user)
        recipe = recipes[0]
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipe.tags.count(), 2)
        for tag in payload['tags']:
            exists = recipe.tags\
                .filter(name=tag['name'], user=self.user)\
                .exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_tags(self):
        tag = Tag.objects.create(user=self.user, name='Indian')
        payload = {
            'title': 'Sample recipe title2',
            'time_minutes': 222,
            'price': Decimal('25.25'),
            'description': 'Sample2 description',
            'link': 'http://example2.com/recipe.pdf',
            'tags': [{'name': 'Indian'}, {'name': 'Dinner'}]
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        recipes = Recipe.objects.filter(user=self.user)
        recipe = recipes[0]
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(recipes.count(), 1)
        self.assertEqual(recipe.tags.count(), 2)
        self.assertIn(tag, recipe.tags.all())
        for tag in payload['tags']:
            exists = recipe.tags\
                .filter(name=tag['name'], user=self.user)\
                .exists()
            self.assertTrue(exists)

    def test_create_tag_on_update(self):
        recipe = create_recipe(user=self.user)

        payload = {'tags': [{'name': 'Lunch'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        new_tag = Tag.objects.get(user=self.user, name='Lunch')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(new_tag, recipe.tags.all())

    def test_update_recipe_assign_tag(self):
        recipe = create_recipe(user=self.user)
        tag = Tag.objects.create(user=self.user, name='Lunch')
        recipe.tags.add(tag)

        new_tag = Tag.objects.create(user=self.user, name='Dinner')
        payload = {'tags': [{'name': 'Dinner'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(new_tag, recipe.tags.all())
        self.assertNotIn(tag, recipe.tags.all())

    def test_clear_recipe_tags(self):
        recipe = create_recipe(user=self.user)
        tag = Tag.objects.create(user=self.user, name='Lunch')
        recipe.tags.add(tag)

        payload = {'tags': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.tags.count(), 0)

    def test_create_recipe_with_new_ingredients(self):
        """Test creating a recipe with new ingredients."""
        payload = {
            'title': 'Cauliflower Tacos',
            'time_minutes': 60,
            'price': Decimal('4.30'),
            'ingredients': [{'name': 'Cauliflower'}, {'name': 'Salt'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)

        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_recipe_with_existing_ingredient(self):
        """Test creating a new recipe with existing ingredient."""
        ingredient = Ingredient.objects.create(user=self.user, name='Lemon')
        payload = {
            'title': 'Vietnamese Soup',
            'time_minutes': 25,
            'price': '2.55',
            'ingredients': [{'name': 'Lemon'}, {'name': 'Fish Sauce'}],
        }
        res = self.client.post(RECIPES_URL, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        recipes = Recipe.objects.filter(user=self.user)
        self.assertEqual(recipes.count(), 1)

        recipe = recipes[0]
        self.assertEqual(recipe.ingredients.count(), 2)
        self.assertIn(ingredient, recipe.ingredients.all())

        for ingredient in payload['ingredients']:
            exists = recipe.ingredients.filter(
                name=ingredient['name'],
                user=self.user,
            ).exists()
            self.assertTrue(exists)

    def test_create_ingredient_on_update(self):
        recipe = create_recipe(user=self.user)

        payload = {'ingredients': [{'name': 'Salt'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        new_ingredient = Ingredient.objects.get(user=self.user, name='Salt')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(new_ingredient, recipe.ingredients.all())

    def test_update_recipe_assign_ingredient(self):
        recipe = create_recipe(user=self.user)
        ingredient = Ingredient.objects.create(user=self.user, name='Salt')
        recipe.ingredients.add(ingredient)

        new_ingredient = Ingredient.objects.create(
            user=self.user,
            name='Kale'
        )
        payload = {'ingredients': [{'name': 'Kale'}]}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(new_ingredient, recipe.ingredients.all())
        self.assertNotIn(ingredient, recipe.ingredients.all())

    def test_clear_recipe_ingredients(self):
        recipe = create_recipe(user=self.user)
        ingredient = Ingredient.objects.create(user=self.user, name='Salt')
        recipe.ingredients.add(ingredient)

        payload = {'ingredients': []}
        url = detail_url(recipe.id)
        res = self.client.patch(url, payload, format='json')

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(recipe.ingredients.count(), 0)