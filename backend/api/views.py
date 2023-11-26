from io import BytesIO

from api.filters import IngredientFilter, RecipeFilter
from django.http import FileResponse
from django.shortcuts import get_object_or_404
from djoser.views import UserViewSet
from recipes.models import Favorite, Ingredient, Recipe, ShoppingCart, Tag
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import SAFE_METHODS, AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet
from users.models import CustomUser, Subscription

from .pagination import CustomPagination
from .permissions import IsAuthorOrReadOnly
from .serializers import (CustomUserSerializer, FavoriteSerializer,
                          IngredientForRecipe, IngredientSerializer,
                          RecipeCreateSerializer, RecipeReadSerializer,
                          ShoppingCartSerializer, SubscribeSerializer,
                          TagSerializer)


class CustomUserViewSet(UserViewSet):
    queryset = CustomUser.objects.all()
    serializer_class = CustomUserSerializer
    pagination_class = CustomPagination
    permission_classes = [AllowAny]

    # def get_permissions(self):
    #     if self.action == 'retrieve':
    #         self.permission_classes = [AllowAny]
    #     return super().get_permissions()

    @action(detail=False, methods=['get'], url_path='me',
            permission_classes=(IsAuthenticated,),
            serializer_class=CustomUserSerializer)
    def get_me(self, request):
        serializer = CustomUserSerializer(
            instance=request.user,
            context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post', 'delete'],
            url_path='subscribe', permission_classes=[IsAuthorOrReadOnly])
    def subscribe(self, request, id):
        user = request.user
        author = get_object_or_404(CustomUser, id=id)
        if request.method == 'POST':
            if user == author:
                return Response('Нельзя подписаться на самого себя',
                                status=status.HTTP_400_BAD_REQUEST)
            try:
                # Попытка получить существующую подписку
                Subscription.objects.get(user=user, author=author)
                return Response('Подписка уже существует',
                                status=status.HTTP_400_BAD_REQUEST)
            except Subscription.DoesNotExist:
                # Если подписка не существует, создать новую
                Subscription.objects.create(user=user, author=author)
                serializer = SubscribeSerializer(
                    author, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        elif request.method == 'DELETE':
            try:
                subscription = Subscription.objects.get(
                    user=user, author=author)
                subscription.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except Subscription.DoesNotExist:
                return Response('Подписка не найдена',
                                status=status.HTTP_400_BAD_REQUEST)
            except CustomUser.DoesNotExist:
                return Response('Автор не найден',
                                status=status.HTTP_400_BAD_REQUEST)

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

    # def get_recipe(self, pk):
    #     try:
    #         recipe = Recipe.objects.get(id=pk)
    #     except Recipe.DoesNotExist:
    #         return Response('Рецепт не существует',
    #                         status=status.HTTP_400_BAD_REQUEST)
    #     return recipe

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthorOrReadOnly]
    )
    def favorite(self, request, pk):
        # recipe = self.get_recipe(pk) попытка избавиться от
        # повтора кода, но не обрабатывает ошибку

        if request.method == 'POST':
            try:
                recipe = Recipe.objects.get(id=pk)
            except Recipe.DoesNotExist:
                return Response('Рецепт не существует',
                                status=status.HTTP_400_BAD_REQUEST)

            serializer = FavoriteSerializer(
                data={'user': request.user.id, 'recipe': recipe.id},
                context={'request': request})
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            try:
                recipe = Recipe.objects.get(id=pk)
            except Recipe.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
            try:
                favorite_item = Favorite.objects.get(
                    user=request.user, recipe=recipe)
                favorite_item.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except Favorite.DoesNotExist:
                return Response('Рецепт не был добавлен в избранное',
                                status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=True,
        methods=['post', 'delete'],
        permission_classes=[IsAuthorOrReadOnly]
    )
    def shopping_cart(self, request, pk):
        # recipe = self.get_recipe(pk)

        if request.method == 'POST':
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
        else:
            try:
                recipe = Recipe.objects.get(id=pk)
            except Recipe.DoesNotExist:
                return Response(status=status.HTTP_404_NOT_FOUND)
            try:
                shopping_cart = ShoppingCart.objects.get(
                    user=request.user,
                    recipe=recipe)
                shopping_cart.delete()
                return Response(status=status.HTTP_204_NO_CONTENT)
            except ShoppingCart.DoesNotExist:
                return Response('Рецепт не был добавлен в список покупок',
                                status=status.HTTP_400_BAD_REQUEST)

    @action(
        detail=False,
        methods=['get'],
        permission_classes=[IsAuthorOrReadOnly]
    )
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
        pdfmetrics.registerFont(TTFont('DejaVuSerif-Bold',
                                       'DejaVuSerif-Bold.ttf'))
        pdf.setFont('DejaVuSerif-Bold', 14)
        pdf.drawString(100, 50, ' ')
        y = 670
        page_height = 800
        for name, total_amount in ingredient_totals.items():
            pdf.drawString(100, y, f'{name} ({unit}) - {total_amount} ')
            y -= 20
            if y < 50:
                pdf.showPage()
                y = page_height - 50

        pdf.save()
        buffer.seek(0)

        response = FileResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = \
            'attachment; filename="shopping_cart.pdf"'
        return response
