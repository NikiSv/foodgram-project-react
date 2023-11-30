import re

from djoser.serializers import UserCreateSerializer, UserSerializer
from drf_extra_fields.fields import Base64ImageField
from rest_framework.fields import CharField, IntegerField
from rest_framework.serializers import (ModelSerializer,
                                        PrimaryKeyRelatedField,
                                        SerializerMethodField, ValidationError)
from rest_framework.validators import UniqueTogetherValidator

from recipes.models import (Favorite, Ingredient, IngredientForRecipe, Recipe,
                            ShoppingCart, Tag)
from users.models import CustomUser, Subscription


class CustomUserSerializer(UserSerializer):
    is_subscribed = SerializerMethodField(read_only=True)

    class Meta:
        model = CustomUser
        fields = ('email', 'id', 'username',
                  'first_name', 'last_name', 'is_subscribed')

    def get_is_subscribed(self, data):
        user = self.context.get('request').user
        if user.is_authenticated:
            return Subscription.objects.filter(user=user, author=data).exists()
        return False


class CustomUserRegistrationSerializer(UserCreateSerializer):
    username = CharField(max_length=150)

    class Meta:
        model = CustomUser
        fields = ('id', 'email', 'username',
                  'first_name', 'last_name', 'password')

    def validate_username(self, data):
        pattern = r'^[\w.@+-]+$'
        if not re.match(pattern, data):
            raise ValidationError('Запрещенные символы')

        if CustomUser.objects.filter(username=data).exists():
            raise ValidationError('Пользователь с таким именем уже существует')
        return data


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
            recipes = recipes[:int(recipes_limit)]
        serializer = ShortCartRecipeSerializer(recipes, many=True)
        return serializer.data

    def get_recipes_count(self, user):
        return user.recipes.count()


class SubscriptionSerializer(ModelSerializer):
    user = PrimaryKeyRelatedField(read_only=True)
    author = PrimaryKeyRelatedField(queryset=CustomUser.objects.all())

    class Meta:
        model = Subscription
        fields = ('user', 'author')
        # validators = [UniqueTogetherValidator(
        #     queryset=Subscription.objects.all(),
        #     fields=('user', 'author'),
        #     message='Подписка уже существует')]

    def validate(self, attrs):
        user = self.context['request'].user
        author = attrs['author']
        if self.context['request'].method == 'POST':
            if user == author:
                raise ValidationError(
                    'Невозможно подписаться на самого себя'
                )
        elif self.context['request'].method == 'DELETE':
            try:
                Subscription.objects.get(user=user, author=author)
            except Subscription.DoesNotExist:
                raise ValidationError('Подписка не найдена')
        return attrs

    def create(self, validated_data):
        return Subscription.objects.create(**validated_data)

    # def validate(self, data):
    #     user = data['user']
    #     author = data['author']

    #     if user == author:
    #         raise ValidationError('Нельзя подписываться на себя')
    #     subscription = Subscription.objects.filter(
    #         user=user, author=author).first()
    #     if not subscription:
    #         raise ValidationError('Подписка не найдена')
    #     return data

    # def create(self, validated_data):
    #     return Subscription.objects.create(**validated_data)
    # def validate(self, data):
    #     user = data['user']
    #     author = data['author']

    #     if user == author:
    #         raise ValidationError('Нельзя подписываться на самого себя')

    #     subscription = Subscription.objects.filter(
    #         user=user, author=author).first()
    #     if subscription:
    #         raise ValidationError('Подписка уже существует')

    #     return data

    # def create(self, validated_data):
    #     user = validated_data['user']
    #     author = validated_data['author']

    #     subscription = Subscription.objects.create(user=user, author=author)
    #     return subscription


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

    def validate_amount(self, amount):
        if amount is None or amount <= 0 or amount >= 10000:
            raise ValidationError(
                'Количество не может быть 0 или больше 10000')
        return amount


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
        if self.context['request'].method == 'POST':
            ingredients = data.get('ingredients', [])
            if not ingredients:
                raise ValidationError('Добавьте ингредиенты')

            ingredient_ids = set()
            for ingredient_data in ingredients:
                ingredient = ingredient_data.get('ingredient')
                if not ingredient:
                    raise ValidationError('Ингредиент не может быть пустым')

                ingredient_id = ingredient.id
                if ingredient_id in ingredient_ids:
                    raise ValidationError('Ингредиенты не могут повторяться')
                ingredient_ids.add(ingredient_id)

            tags = data.get('tags')
            if not tags:
                raise ValidationError('Добавьте теги')

            if len(tags) != len(set(tags)):
                raise ValidationError('Теги не могут повторяться')

            if not data.get('image'):
                raise ValidationError('Добавьте изображение')

            return data

    @staticmethod
    def create_ingredients(ingredients, recipe):
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
        return super().update(recipe, validated_data)

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
        serializer = RecipeReadSerializer(
            instance, context={'request': request})
        return serializer.data


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
                and Favorite.objects.filter(user=request.user,
                                            recipe=data).exists())

    def get_is_in_shopping_cart(self, data):
        request = self.context.get('request')
        return (request and request.user.is_authenticated
                and ShoppingCart.objects.filter(user=request.user,
                                                recipe=data).exists())


class FavoriteOrShoppingCartSerializer(ModelSerializer):
    def to_representation(self, instance):
        request = self.context.get('request')
        return ShortCartRecipeSerializer(
            instance.recipe,
            context={'request': request}).data


class FavoriteSerializer(FavoriteOrShoppingCartSerializer):
    class Meta:
        model = Favorite
        fields = '__all__'
        validators = [UniqueTogetherValidator(
            queryset=Favorite.objects.all(),
            fields=('user', 'recipe'),
            message='Рецепт уже добавлен в избранное')]

    def validate(self, attrs):
        user = self.context['request'].user
        recipe = attrs['recipe']
        if self.context['request'].method == 'DELETE':
            if not Favorite.objects.filter(user=user, recipe=recipe).exists():
                raise ValidationError(
                    'Рецепт не был добавлен в избранное')
        return attrs

    def create(self, validated_data):
        return Favorite.objects.create(**validated_data)


class ShoppingCartSerializer(FavoriteOrShoppingCartSerializer):
    class Meta:
        model = ShoppingCart
        fields = '__all__'
        validators = [UniqueTogetherValidator(
            queryset=ShoppingCart.objects.all(),
            fields=('user', 'recipe'),
            message='Рецепт уже добавлен в список покупок')]


class ShortCartRecipeSerializer(ModelSerializer):
    class Meta:
        model = Recipe
        fields = ('id', 'name', 'image', 'cooking_time')
        # validators = [UniqueTogetherValidator(
        #     queryset=ShoppingCart.objects.all(),
        #     fields=('user', 'recipe'),
        #     message='Вы уже добавили этот рецепт в список покупок')]
