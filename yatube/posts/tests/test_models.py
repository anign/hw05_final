from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import Group, Post

User = get_user_model()


class PostModelTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='auth')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='Тестовый слаг',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост для теста тестов блааа',
        )

    def test_models_have_correct_object_names(self):
        """Проверяем метод __str__"""
        post = PostModelTest.post
        group = PostModelTest.group
        self.assertEqual(str(post), post.text[:15])
        self.assertEqual(str(group), group.title)

    def test_verbose_name(self):
        """Проверка verbose name."""
        task = PostModelTest.post
        field_verboses = {
            'text': 'Текст',

        }
        for field, expected_value in field_verboses.items():
            with self.subTest(field=field):
                self.assertEqual(
                    task._meta.get_field(field).verbose_name, expected_value)
