import re

from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from recipes.models import (Favorite, Ingredient, IngredientForRecipe, Recipe,
                            ShoppingCart, Tag)
from rest_framework.fields import CharField, IntegerField
from rest_framework.serializers import (ModelSerializer,
                                        PrimaryKeyRelatedField,
                                        SerializerMethodField, ValidationError)
from rest_framework.validators import UniqueTogetherValidator
from users.models import CustomUser, Subscription


class CustomUserSerializer(UserSerializer):
    is_subscribed = SerializerMethodField(read_only=True)

    class Meta:
        model = CustomUser
        fields = ('email', 'id', 'username',
                  'first_name', 'last_name', 'is_subscribed')

    def get_is_subscribed(self, data):
        user = self.context.get('request').user
        if user.is_anonymous:
            return False
        return Subscription.objects.filter(user=user, author=data).exists()


class CustomUserRegistrationSerializer(UserCreateSerializer):
    username = CharField(max_length=150)

    def validate_username(self, value):
        pattern = r'^[\w.@+-]+$'
        if not re.match(pattern, value):
            raise ValidationError('Запрещенные символы')

        if CustomUser.objects.filter(username=value).exists():
            raise ValidationError('Пользователь с таким именем уже существует')
        return value

    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'username',
                  'first_name', 'last_name', 'password')


class SubscribeSerializer(CustomUserSerializer):
    is_subscribed = SerializerMethodField()
    recipes = SerializerMethodField()
    recipes_count = SerializerMethodField()

    class Meta:
        model = CustomUser
        fields = ('email', 'id', 'username', 'first_name',
                  'last_name', 'is_subscribed', 'recipes', 'recipes_count')
        read_only_fields = ('email', 'username', 'first_name', 'last_name',
                            'is_subscribed', 'recipes', 'recipes_count')

    def get_recipes(self, user):
        recipes = Recipe.objects.filter(author=user)
        recipes_limit = self.context.get('request').query_params.get(
            'recipes_limit')
        if recipes_limit:
            recipes_limit = int(recipes_limit)
            recipes = recipes[:recipes_limit]
        serializer = ShortCartRecipeSerializer(recipes, many=True)
        return serializer.data

    def get_recipes_count(self, user):
        return user.recipes.count()


class TagSerializer(ModelSerializer):
    class Meta:
        model = Tag
        fields = '__all__'


class IngredientSerializer(ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'


class IngredientPostSerializer(ModelSerializer):
    id = PrimaryKeyRelatedField(
        source='ingredient',
        queryset=Ingredient.objects.all())
    amount = IntegerField()

    class Meta:
        model = IngredientForRecipe
        fields = ('id', 'amount')


class RecipeCreateSerializer(ModelSerializer):
    ingredients = IngredientPostSerializer(
        many=True)
    tags = PrimaryKeyRelatedField(
        queryset=Tag.objects.all(),
        many=True)
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        exclude = ('id', 'author')

    def validate(self, data):
        # Проверка обязательности добавления ингредиентов
        ingredients = data.get('ingredients', [])
        if not ingredients:
            raise ValidationError('Добавьте ингредиенты')

        # Проверка уникальности ингредиентов
        ingredient_ids = set()
        for ingredient_data in ingredients:
            ingredient = ingredient_data.get('ingredient')
            if not ingredient:
                raise ValidationError('Ингредиент не может быть пустым')

            ingredient_id = ingredient.id
            if ingredient_id in ingredient_ids:
                raise ValidationError('Ингредиенты не могут повторяться')
            ingredient_ids.add(ingredient_id)

            # Проверка количества ингредиента
            amount = ingredient_data.get('amount')
            if amount is None or amount <= 0:
                raise ValidationError('Добавьте количество ингредиента')

        # Проверка обязательности добавления тегов
        tags = data.get('tags')
        if not tags:
            raise ValidationError('Добавьте теги')

        # Проверка уникальности тегов
        if len(tags) != len(set(tags)):
            raise ValidationError('Теги не могут повторяться')

        # Проверка обязательности добавления изображения
        if not data.get('image'):
            raise ValidationError('Добавьте изображение')

        return data

    def create_ingredients(self, ingredients, recipe):
        ingredient_for_recipe_list = []
        for recipe_ingredient in ingredients:
            ingredient_id = recipe_ingredient['ingredient'].id
            amount = recipe_ingredient.get('amount')
            ingredient_for_recipe_list.append(IngredientForRecipe(
                recipe=recipe,
                ingredient_id=ingredient_id,
                amount=amount))
        IngredientForRecipe.objects.bulk_create(ingredient_for_recipe_list)

    def create(self, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags)
        self.create_ingredients(ingredients, recipe)
        return recipe

    def update(self, recipe, validated_data):
        tags = validated_data.pop('tags')
        ingredients = validated_data.pop('ingredients')
        recipe.tags.clear()
        recipe.ingredients.clear()
        recipe.tags.set(tags)
        self.create_ingredients(ingredients, recipe)
        return super(RecipeCreateSerializer, self).update(
            recipe, validated_data)

    def get_is_favorited(self, data):
        if self.context.get('request').user.is_authenticated:
            return Recipe.objects.filter(
                id=data.id,
                favorites__user=self.context.get('request').user
            ).exists()
        return False

    def get_is_in_shopping_cart(self, data):
        if self.context.get('request').user.is_authenticated:
            return Recipe.objects.filter(
                id=data.id,
                shopping_cart__user=self.context.get('request').user
            ).exists()
        return False

    def to_representation(self, instance):
        request = self.context.get('request')
        return RecipeReadSerializer(
            instance, context={'request': request}).data


class RecipeReadSerializer(ModelSerializer):
    tags = TagSerializer(many=True, read_only=True)
    author = CustomUserSerializer(read_only=True)
    ingredients = SerializerMethodField()
    is_favorited = SerializerMethodField(read_only=True)
    is_in_shopping_cart = SerializerMethodField(read_only=True)
    image = Base64ImageField(required=True)

    class Meta:
        model = Recipe
        fields = ('id', 'tags', 'author', 'ingredients',
                  'is_favorited', 'is_in_shopping_cart', 'name',
                  'image', 'text', 'cooking_time')

    def get_ingredients(self, data):
        recipe = data
        ingredient_for_recipe_objects = IngredientForRecipe.objects.filter(
            recipe=recipe)

        ingredients = []
        for ingredient_for_recipe in ingredient_for_recipe_objects:
            ingredient_info = {
                'id': ingredient_for_recipe.ingredient.id,
                'name': ingredient_for_recipe.ingredient.name,
                'measurement_unit':
                ingredient_for_recipe.ingredient.measurement_unit,
                'amount': ingredient_for_recipe.amount
            }
            ingredients.append(ingredient_info)

        return ingredients

    def get_is_favorited(self, data):
        request = self.context.get('request')
        return (request and request.user.is_authenticated
                and Favorite.objects.filter(
                    user=request.user, recipe=data).exists())

    def get_is_in_shopping_cart(self, data):
        request = self.context.get('request')
        return (request and request.user.is_authenticated
                and ShoppingCart.objects.filter(
                    user=request.user, recipe=data).exists())


class FavoriteSerializer(ModelSerializer):
    class Meta:
        model = Favorite
        fields = '__all__'
        validators = [UniqueTogetherValidator(
            queryset=Favorite.objects.all(),
            fields=('user', 'recipe'),
            message='Вы уже добавили этот рецепт в избранное')]

    def to_representation(self, instance):
        request = self.context.get('request')
        return ShortCartRecipeSerializer(
            instance.recipe,
            context={'request': request}).data


class ShortCartRecipeSerializer(ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        validators = [UniqueTogetherValidator(
            queryset=ShoppingCart.objects.all(),
            fields=('user', 'recipe'),
            message='Вы уже добавили этот рецепт в список покупок')]


class ShoppingCartSerializer(ModelSerializer):
    class Meta:
        model = ShoppingCart
        fields = '__all__'
        validators = [UniqueTogetherValidator(
            queryset=ShoppingCart.objects.all(),
            fields=('user', 'recipe'),
            message='Рецепт уже добавлен в список покупок')]

    def to_representation(self, instance):
        request = self.context.get('request')
        return ShortCartRecipeSerializer(
            instance.recipe,
            context={'request': request}).data
