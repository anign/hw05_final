import shutil
import tempfile
from http import HTTPStatus

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Follow, Group, Post, User

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.auth_user = User.objects.create_user(username='auth')
        cls.user2 = User.objects.create_user(username='user2')
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='slug',
            description='Тестовое описание',
        )
        cls.post = Post.objects.create(
            author=cls.auth_user,
            text='Тестовый пост',
            group=cls.group,
        )
        cls.post2 = Post.objects.create(
            text='new post 2 new post 2',
            author=cls.user2,
            group=cls.group
        )

    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='Anonymous')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        self.authorized_client2 = Client()
        self.authorized_client2.force_login(self.user2)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        """Валидная форма создает пост."""
        posts_count = Post.objects.count()
        form_data = {
            'text': 'Текст нового поста',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertRedirects(
            response,
            reverse('posts:profile',
                    kwargs={'username': self.user.username}
                    )
        )
        self.assertEqual(Post.objects.count(), posts_count + 1)
        post = Post.objects.first()
        self.assertEqual(post.text, 'Текст нового поста')
        self.assertEqual(post.group, self.group)

    def test_guest_client_cant_create_post(self):
        initial_count = Post.objects.count()
        form_data = {
            'text': 'Текст нового поста',
            'group': self.group.id,
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), initial_count)

    def test_authorized_user_cant_edit_post(self):
        """Тест на невозможность редактирования существующей
        записи авторизованным пользователем не автором."""
        form_data = {
            'text': 'Измененный текст поста',
            'group': self.group.id,
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit',
                args=(self.post2.id,)
            ),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                args=(self.post2.id,),
            ),
        )
        post = Post.objects.get(id=self.post2.id)
        self.assertEqual(
            post.text,
            self.post2.text
        )

    def test_author_can_edit_post(self):
        """Тест на возможность редактирования существующей
        записи автором."""
        form_data = {
            'text': 'Измененный текст поста',
            'group': self.group.id,
        }
        response = self.authorized_client2.post(
            reverse(
                'posts:post_edit',
                args=(self.post2.id,)
            ),
            data=form_data,
            follow=True,
        )
        self.assertRedirects(
            response,
            reverse(
                'posts:post_detail',
                args=(self.post2.id,),
            ),
        )
        post = Post.objects.get(id=self.post2.id)
        self.assertEqual(
            post.text,
            form_data['text']
        )

    def test_post_with_image_create_record(self):
        "Форма создает запись поста с картинкой"
        count_posts = Post.objects.count()
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
            'text': 'Тестовый пост с картинкой',
            'group': self.group.id,
            'image': uploaded
        }
        response = self.authorized_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Post.objects.count(), count_posts + 1)


class FollowAndCommentsTests(TestCase):
    def setUp(self):

        self.guest_client = Client()
        self.client_auth_follower = Client()
        self.new_authorized_user = Client()
        self.new_user = User.objects.create_user(username='user3')
        self.user_follower = User.objects.create_user(username='follower')
        self.user_following = User.objects.create_user(username='following')
        self.post = Post.objects.create(
            author=self.user_following,
            text='Тестовая новая запись в ленте'
        )
        self.client_auth_follower.force_login(self.user_follower)
        self.new_authorized_user.force_login(self.new_user)

    def test_authorized_user_can_follow(self):
        "Зарегистрированный юзер может подписаться."
        self.client_auth_follower.get(
            reverse(
                'posts:profile_follow',
                kwargs={
                    'username': self.user_following.username
                }
            )
        )
        self.assertEqual(Follow.objects.all().count(), 1)

    def test_unauthorized_user_cant_follow(self):
        "Незарегистрированный юзер не может подписаться."
        self.guest_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={
                    'username': self.user_following.username
                }
            )
        )
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_authorized_user_can_unfollow(self):
        "Отписка от надоевшего графомана."
        self.client_auth_follower.get(
            reverse(
                'posts:profile_follow',
                kwargs={
                    'username': self.user_following.username
                }
            )
        )
        self.client_auth_follower.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={
                    'username': self.user_following.username
                }
            )
        )
        self.assertEqual(Follow.objects.all().count(), 0)

    def test_subscription_feed(self):
        "Новая запись пользователя появляется в ленте подписчиков"
        Follow.objects.create(user=self.user_follower,
                              author=self.user_following)
        response = self.client_auth_follower.get('/follow/')
        first_object = response.context['page_obj'][0]
        self.assertEqual(
            first_object.text,
            'Тестовая новая запись в ленте'
        )

    def test_subscription_not_feed(self):
        "Новая запись пользователя не появляется в ленте у неподписанных"
        Follow.objects.create(user=self.user_follower,
                              author=self.user_following)
        response = self.new_authorized_user.get('/follow/')
        self.assertNotContains(
            response,
            'Тестовая новая запись в ленте'
        )
