import shutil
import tempfile

from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

from ..models import Group, Post

User = get_user_model()


class PostContextTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Временная папка для медиа-файлов;
        settings.MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create(username='author')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='test_slug',
            description='Тестовое описание группы',
        )
        cls.post = Post.objects.create(
            text='Тестовый пост',
            author=cls.user,
            group=cls.group,
            image=uploaded
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(settings.MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_post_index_show_correct_context(self):
        response = self.authorized_client.get(reverse('posts:index'))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, 'Тестовый пост')
        self.assertEqual(first_object.author.username, 'author')
        self.assertEqual(first_object.group.title, 'Тестовая группа')
        # добавил проверку image
        self.assertEqual(Post.objects.first().image, 'posts/small.gif')

    def test_group_list_correct_context(self):
        response = self.client.get(reverse('posts:group_list',
                                           kwargs={'slug': self.group.slug}))
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, 'Тестовый пост')
        self.assertEqual(first_object.author.username, 'author')
        self.assertEqual(first_object.group.title, 'Тестовая группа')
        self.assertEqual(Post.objects.first().image, 'posts/small.gif')

    def test_post_detail_correct_context(self):
        response = self.client.get(reverse('posts:post_detail',
                                           kwargs={'post_id': self.post.id}))
        first_object = response.context['post']
        self.assertEqual(first_object.text, 'Тестовый пост')
        self.assertEqual(first_object.author.username, 'author')
        self.assertEqual(first_object.group.title, 'Тестовая группа')
        self.assertEqual(Post.objects.first().image, 'posts/small.gif')

    def test_post_create_correct_context(self):
        response = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={"post_id": f'{self.post.id}'})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
            'image': forms.fields.ImageField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)

    def test_profile_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом"""
        response = self.authorized_client.get(
            reverse('posts:profile', kwargs={'username': 'author'}))
        first_object = response.context['page_obj'][0]
        posts_text = first_object.text
        posts_image = Post.objects.first().image
        self.assertEqual(posts_image, 'posts/small.gif')
        self.assertEqual(response.context['author'].username, 'author')
        self.assertEqual(posts_text, 'Тестовый пост')

    def test_posts_sorted_by_user(self):
        response = self.client.get(
            reverse('posts:profile',
                    kwargs={'username': self.post.author})
        )
        first_object = response.context['page_obj'][0]
        self.assertEqual(first_object.text, 'Тестовый пост')
        self.assertEqual(first_object.author.username, 'author')
        self.assertEqual(first_object.group.title, 'Тестовая группа')

    def test_post_edit_correct_context(self):
        """Шаблон post_edit сформирован с правильным контекстом."""
        response = self.authorized_client.get(
            reverse('posts:post_edit',
                    kwargs={"post_id": f'{self.post.id}'})
        )
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.models.ModelChoiceField,
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context['form'].fields[value]
                self.assertIsInstance(form_field, expected)
        self.assertTrue(response.context['is_edit'])

    def test_extended_post_checking(self):
        """Дополнительная проверка при создании поста."""
        response = self.authorized_client.get(
            reverse('posts:group_list',
                    kwargs={'slug': 'test_slug'})
        )
        first_object = response.context["page_obj"][0]
        post_1 = first_object.text
        self.assertTrue(post_1, 'Тестовая запись 2')

    def test_creation_post_with_image(self):
        """Создаётся пост с картинкой."""
        posts_count = Post.objects.count()
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        form_data = {
            'title': 'Тестовый заголовок',
            'text': 'Тестовый текст',
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        # загруженная картинка соотсветствует картинке в модели
        self.assertEqual(Post.objects.last().image, 'posts/small.gif')
        self.assertRedirects(response, reverse(
            'posts:profile',
            kwargs={'username': self.user.username})
        )

    def test_cache_is_working_20_sec(self):
        response_first = self.client.get(reverse("posts:index"))
        response_first_cont = response_first.content
        Post.objects.all().delete
        response_sec = self.client.get(reverse("posts:index"))
        response_sec_context = response_sec.content
        self.assertEqual(response_first_cont, response_sec_context)


class PostPaginatorTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='test_name')
        cls.group = Group.objects.create(
            title="Тестовая группа",
            slug='test_slug',
            description='Тестовое описание',
        )
        for i in range(1, 14):
            cls.post = Post.objects.create(
                text='Тестовый текст',
                author=cls.user,
                group=cls.group
            )

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_first_page_contains_ten_posts(self):
        paginator_list = {
            'posts:index': reverse('posts:index'),
            'posts:group_list': reverse(
                'posts:group_list',
                kwargs={'slug': PostPaginatorTests.group.slug}
            ),
            'posts:profile': reverse(
                'posts:profile',
                kwargs={'username': PostPaginatorTests.user.username}
            ),
        }
        for template, reverse_name in paginator_list.items():
            response = self.guest_client.get(reverse_name)
            self.assertEqual(len(response.context['page_obj']), 10)

    def test_second_page_contains_ten_posts(self):
        paginator_list = {
            'posts:index': reverse('posts:index') + '?page=2',
            'posts:group_list': reverse(
                'posts:group_list',
                kwargs={'slug': PostPaginatorTests.group.slug}) + '?page=2',
            'posts:profile': reverse(
                'posts:profile',
                kwargs={'username': PostPaginatorTests.user.username}
            ) + '?page=2',
        }
        for template, reverse_name in paginator_list.items():
            response = self.guest_client.get(reverse_name)
            self.assertEqual(len(response.context['page_obj']), 3)
