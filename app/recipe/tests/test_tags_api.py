"""
Tests for the tags API
"""
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.test import TestCase
from decimal import Decimal


from rest_framework import status
from rest_framework.test import APIClient


from core.models import (Tag, Recipe)


from recipe.serializers import TagSerializer


TAGS_URL = reverse('recipe:tag-list')


def detail_url(tag_id):
    return reverse('recipe:tag-detail', args=[tag_id])


def create_user(email='example.com@example.com', password='test123'):
    return get_user_model().objects.create_user(email=email, password=password)


class PublicTagsAPITests(TestCase):
    """Test unauthenticated API Requests"""

    def setUp(self):
        self.client = APIClient()

    def test_auth_required(self):
        """Test auth is required"""
        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsAPITest(TestCase):
    """Test Authenticated API requests"""

    def setUp(self):
        self.user = create_user()
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_get_tags(self):
        Tag.objects.create(user=self.user, name='Vegan')
        Tag.objects.create(user=self.user, name='Dessert')

        res = self.client.get(TAGS_URL)

        tags = Tag.objects.all().order_by('-name')
        serializer = TagSerializer(tags, many=True)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data, serializer.data)

    def test_tags_limited_by_user(self):
        user2 = create_user(email='example2@example.com')
        expected = Tag.objects.create(user=self.user, name='Vegan')

        Tag.objects.create(user=user2, name='Dessert')

        res = self.client.get(TAGS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data), 1)
        self.assertEqual(res.data[0]['name'], expected.name)
        self.assertEqual(res.data[0]['id'], expected.id)

    def test_update_tag(self):
        """Test update tag"""
        tag = Tag.objects.create(user=self.user, name='After Dinner')

        payload = {'name': 'Dessert'}
        url = detail_url(tag.id)
        res = self.client.patch(url, payload)

        tag.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(tag.name, payload['name'])

    def test_delete_tag(self):
        """Test delete tag"""
        tag = Tag.objects.create(user=self.user, name='After Dinner')

        url = detail_url(tag.id)
        res = self.client.delete(url)

        tags = Tag.objects.filter(user=self.user)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(tags.exists())

    def test_get_assigned_tags(self):
        recipe = Recipe.objects.create(
            user=self.user,
            title='Thai Curry',
            time_minutes=22,
            price=Decimal('5.25'),
        )
        tag = Tag.objects.create(user=self.user, name='Lunch')
        tag2 = Tag.objects.create(user=self.user, name='Dinner')
        recipe.tags.add(tag)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        s1 = TagSerializer(tag)
        s2 = TagSerializer(tag2)
        self.assertIn(s1.data, res.data)
        self.assertNotIn(s2.data, res.data)

    def test_filtered_tags_unique(self):
        recipe1 = Recipe.objects.create(
            user=self.user,
            title='Thai Curry',
            time_minutes=22,
            price=Decimal('5.25'),
        )
        recipe2 = Recipe.objects.create(
            user=self.user,
            title='Poached Eggs',
            time_minutes=22,
            price=Decimal('5.25'),
        )
        tag = Tag.objects.create(user=self.user, name='Lunch')
        Tag.objects.create(user=self.user, name='Dinner')

        recipe1.tags.add(tag)
        recipe2.tags.add(tag)

        res = self.client.get(TAGS_URL, {'assigned_only': 1})

        self.assertEqual(len(res.data), 1)
