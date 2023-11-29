from colorfield.fields import ColorField
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import UniqueConstraint

from users.models import CustomUser

MAX_LENGTH = 200


class Tag(models.Model):
    name = models.CharField(
        'Название',
        max_length=MAX_LENGTH,
        unique=True)
    color = ColorField(
        'Цвет',
        null=True, blank=True,
        unique=True)
    slug = models.SlugField(
        'Уникальный слаг',
        max_length=MAX_LENGTH,
        unique=True,
        null=True, blank=True)

    class Meta:
        verbose_name = 'Тег'
        verbose_name_plural = 'Тэги'
        ordering = ['id']

    def __str__(self):
        return self.name


class Ingredient(models.Model):
    name = models.CharField(
        'Название',
        max_length=MAX_LENGTH,
        blank=False)
    measurement_unit = models.CharField(
        'Единицы измерения',
        max_length=MAX_LENGTH,
        blank=False)

    class Meta:
        verbose_name = 'Ингредиент'
        verbose_name_plural = 'Ингредиенты'
        ordering = ['name']

    def __str__(self):
        return self.name


class Recipe(models.Model):
    author = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        verbose_name='Автор',
        related_name='recipes')
    tags = models.ManyToManyField(
        Tag,
        verbose_name='Теги',
        blank=False)
    ingredients = models.ManyToManyField(
        Ingredient,
        through='IngredientForRecipe',
        blank=False,
        verbose_name='Ингредиенты',
        related_name='recipes')
    name = models.CharField(
        'Название',
        max_length=MAX_LENGTH,
        blank=False)
    image = models.ImageField(
        'Изображение',
        upload_to='recipes/',
        blank=False)
    text = models.CharField(
        'Описание',
        max_length=MAX_LENGTH,
        blank=False)
    cooking_time = models.PositiveSmallIntegerField(
        'Время приготовления',
        validators=[MinValueValidator(1), MaxValueValidator(100000)],
        blank=False)

    class Meta:
        verbose_name = 'Рецепт'
        verbose_name_plural = 'Рецепты'
        ordering = ['name']

    def __str__(self):
        return self.name


class IngredientForRecipe(models.Model):
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        verbose_name='Рецепт')
    ingredient = models.ForeignKey(
        Ingredient, on_delete=models.CASCADE,
        verbose_name='Ингридиент')
    amount = models.PositiveSmallIntegerField(
        'Количество',
        validators=[MinValueValidator(1)])

    class Meta:
        verbose_name = 'Количество ингридиентов в рецепте'
        verbose_name_plural = 'Количество ингридиентов в рецептах'
        ordering = ['-recipe']

    def __str__(self):
        return (f'{self.amount} {self.ingredient.measurement_unit}')


class Favorite(models.Model):
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Пользователь')
    recipe = models.ForeignKey(
        Recipe, on_delete=models.CASCADE,
        related_name='favorites',
        verbose_name='Рецепт')

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        ordering = ['-recipe']
        constraints = [UniqueConstraint(
            fields=['user', 'recipe'],
            name='unique_favourite')]

    def __str__(self):
        return f'Вы добавили "{self.recipe}" в Избранное'


class ShoppingCart(models.Model):
    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Пользователь')
    recipe = models.ForeignKey(
        Recipe,
        on_delete=models.CASCADE,
        related_name='shopping_cart',
        verbose_name='Рецепт')

    class Meta:
        verbose_name = 'Список покупок'
        verbose_name_plural = 'Список покупок'
        ordering = ['-id']

    def __str__(self):
        return f'Вы добавили "{self.recipe}" в список покупок'
