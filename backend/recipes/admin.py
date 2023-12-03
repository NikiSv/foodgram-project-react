from django.contrib import admin
from django.contrib.admin import display

from .models import (Favorite, Ingredient, IngredientForRecipe, Recipe,
                     ShoppingCart, Tag)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    model = Tag
    list_display = ('id', 'name', 'color', 'slug')
    ordering = ('id',)
    search_fields = ('name',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    model = Ingredient
    list_display = ('name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('name',)


class IngredientForRecipeAdmin(admin.TabularInline):
    model = IngredientForRecipe
    list_display = ('recipe', 'ingredient', 'amount',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    model = Recipe
    list_display = ('name', 'author', 'count_in_favorites')
    list_filter = ('name', 'author', 'tags',)
    inlines = [IngredientForRecipeAdmin]

    @display(description='Сколько раз добавили в избранное')
    def count_in_favorites(self, obj):
        return obj.favorites.count()


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'recipe')
    search_fields = ('user', 'recipe')


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('pk', 'user', 'recipe')
    search_fields = ('user', 'recipe')
