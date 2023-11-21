from django_filters import (CharFilter, FilterSet,
                            ModelMultipleChoiceFilter,
                            NumberFilter)

from recipes.models import Ingredient, Recipe, Tag


class IngredientFilter(FilterSet):
    name = CharFilter(lookup_expr='istartswith')

    class Meta:
        model = Ingredient
        fields = ('name',)


class RecipeFilter(FilterSet):
    tags = ModelMultipleChoiceFilter(
        queryset=Tag.objects.all(),
        field_name='tags__slug',
        to_field_name='slug')
    author = NumberFilter(
        field_name='author')
    is_favorited = NumberFilter(
        method='filter_is_favorited')
    is_in_shopping_cart = NumberFilter(
        method='filter_is_in_shopping_cart')

    def filter_by_tags(self, queryset, name, value):
        tags = value.split('&')  # Разбиваем строку с тегами на список
        return queryset.filter(tags__slug__in=tags)

    def filter_is_favorited(self, queryset, name, value):
        if self.request.user.is_authenticated and value:
            return queryset.filter(favorites__user=self.request.user)
        return queryset

    def filter_is_in_shopping_cart(self, queryset, name, value):
        if self.request.user.is_authenticated and value:
            return queryset.filter(shopping_cart__user=self.request.user)
        return queryset

    class Meta:
        model = Recipe
        fields = ('author', 'tags', 'is_favorited', 'is_in_shopping_cart')
