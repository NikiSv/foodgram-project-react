from io import BytesIO

from django.http import FileResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from reportlab.pdfgen import canvas
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from api.filters import IngredientFilter, RecipeFilter
from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from users.models import CustomUser, Subscription

from .pagination import CustomPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (CustomUserSerializer, FavoriteSerializer,
                          IngredientForRecipe, IngredientSerializer,
                          RecipeCreateSerializer, RecipeReadSerializer,
                          ShoppingCartSerializer, SubscribeSerializer,
                          TagSerializer)
from .utils import pdf_drawer


class CustomUserViewSet(UserViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    pagination_class = CustomPagination

    @action(detail=True, methods=['post'],
            url_path='subscribe', permission_classes=[IsAuthorOrReadOnly])
    def subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(CustomUser, id=id)
        subscription = Subscription.objects.filter(
            user=user, author=author).first()
        if subscription:
            return Response('Подписка уже существует',
                            status=status.HTTP_400_BAD_REQUEST)
        subscription = Subscription.objects.create(user=user, author=author)
        serializer = SubscribeSerializer(
            subscription, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @subscribe.mapping.delete
    def delete_subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(CustomUser, id=id)
        subscription = Subscription.objects.filter(
            user=user, author=author).first()
        if not subscription:
            return Response('Подписка не найдена',
                            status=status.HTTP_400_BAD_REQUEST)
        subscription.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=['get'],
            url_path='subscriptions',
            pagination_class=CustomPagination)
    def subscriptions(self, request):
        user = request.user
        subs = Subscription.objects.filter(user=user)
        authors = [sub.author for sub in subs]
        paginated_queryset = self.paginate_queryset(authors)
        serializer = SubscribeSerializer(paginated_queryset,
                                         many=True,
                                         context={'request': request})
        return self.get_paginated_response(serializer.data)


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthorOrReadOnly]
    pagination_class = None


class IngredientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [IsAuthorOrReadOnly]
    pagination_class = None
    filterset_class = IngredientFilter


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.all()
    permission_classes = [IsAuthorOrReadOnly]
    http_method_names = ['get', 'post', 'patch', 'delete']
    filterset_class = RecipeFilter

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def get_serializer_class(self):
        if self.request.method in SAFE_METHODS:
            return RecipeReadSerializer
        return RecipeCreateSerializer

    @action(detail=True, methods=['post'],
            permission_classes=[IsAuthorOrReadOnly])
    def favorite(self, request, pk):
        # try:
        #     recipe = Recipe.objects.get(id=pk)
        # except Recipe.DoesNotExist:
        #     return Response('Рецепт не существует',
        #                     status=status.HTTP_400_BAD_REQUEST)
        recipe = Recipe.objects.get(id=pk)
        serializer = FavoriteSerializer(
            data={'user': request.user.id, 'recipe': recipe.id},
            context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @favorite.mapping.delete
    def delete_favorite(self, request, pk):
        recipe = Recipe.objects.get(id=pk)
        favorite_item = Favorite.objects.get(user=request.user, recipe=recipe)
        favorite_item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
        # try:
        #     favorite_item = Favorite.objects.get(
        #         user=request.user, recipe=recipe)
        #     favorite_item.delete()
        #     return Response(status=status.HTTP_204_NO_CONTENT)
        # except Favorite.DoesNotExist:
        #     return Response('Рецепт не был добавлен в избранное',
        #                     status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'],
            permission_classes=[IsAuthorOrReadOnly])
    def shopping_cart(self, request, pk):
        try:
            recipe = Recipe.objects.get(id=pk)
        except Recipe.DoesNotExist:
            return Response('Рецепт не существует',
                            status=status.HTTP_400_BAD_REQUEST)
        serializer = ShoppingCartSerializer(
            data={'user': request.user.id, 'recipe': recipe.id},
            context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @shopping_cart.mapping.delete
    def delete_shopping_cart(self, request, pk):
        recipe = Recipe.objects.get(id=pk)
        try:
            shopping_cart = Favorite.objects.get(
                user=request.user, recipe=recipe)
            shopping_cart.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ShoppingCart.DoesNotExist:
            return Response('Рецепт не был добавлен в список покупок',
                            status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'],
            permission_classes=[IsAuthorOrReadOnly])
    def download_shopping_cart(self, request):
        shopping_cart_user = ShoppingCart.objects.filter(user=request.user)
        ingredient_data = IngredientForRecipe.objects.filter(
            recipe__in=shopping_cart_user.values_list('recipe', flat=True))

        ingredient_totals = {}
        for ingredient in ingredient_data:
            name = ingredient.ingredient.name
            amount = ingredient.amount
            unit = ingredient.ingredient.measurement_unit

            if name in ingredient_totals:
                ingredient_totals[name] += amount
            else:
                ingredient_totals[name] = amount

        buffer = BytesIO()
        pdf = canvas.Canvas(buffer)
        pdf_drawer(pdf, unit, ingredient_totals)
        pdf.save()
        buffer.seek(0)

        response = FileResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = \
            'attachment; filename="shopping_cart.pdf"'
        return response
