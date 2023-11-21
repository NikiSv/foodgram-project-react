from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    email = models.EmailField(
        'Адрес электронной почты',
        max_length=254,
        blank=False,
        null=False,
        unique=True)
    username = models.CharField(
        'Логин',
        max_length=150,
        blank=False,
        null=False,)
    first_name = models.CharField(
        'Имя',
        max_length=150,
        blank=False,
        null=False,)
    last_name = models.CharField(
        'Фамилия',
        max_length=150,
        blank=False,
        null=False,)
    password = models.CharField(
        'Пароль',
        max_length=150,
        blank=False,
        null=False,)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'username', 'password']

    class Meta:
        verbose_name = 'пользователь'
        verbose_name_plural = 'Пользователи'
        unique_together = ('email', 'username')

    def __str__(self):
        return self.username


class Subscription(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Подписчик')
    author = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='subscribers',
        verbose_name='Автор')

    def __str__(self):
        return self.author.username

    class Meta:
        verbose_name = 'подписка'
        verbose_name_plural = 'Подписки'
        unique_together = ('user', 'author')
