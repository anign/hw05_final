from django.test import Client, TestCase
from django.urls import reverse

from ..models import Follow, Group, Post, User


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
        self.assertEqual(post.group.title, 'Тестовый заголовок')

    def test_guest_client_cant_create_post(self):
        Post.objects.all().delete()
        form_data = {
            'text': 'Текст нового поста',
            'group': self.group.id,
        }
        response = self.guest_client.post(
            reverse('posts:post_create'),
            data=form_data,
            follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Post.objects.count(), 0)

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
        self.assertNotEqual(
            post.text,
            form_data['text']
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


class FollowAndCommentsTests(TestCase):
    def setUp(self):
        self.guest_client = Client()
        self.client_auth_follower = Client()
        self.user_follower = User.objects.create_user(username='follower')
        self.user_following = User.objects.create_user(username='following')
        self.post = Post.objects.create(
            author=self.user_follower,
            text='Тестовый коммент'
        )
        self.client_auth_follower.force_login(self.user_follower)

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
