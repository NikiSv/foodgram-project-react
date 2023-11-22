import json

from django.core.management.base import BaseCommand
from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка ингридиентов из json файла в БД'

    def handle(self, *args, **options):
        with open('recipes/data/ingredients.json',
                  'r', encoding='utf-8') as file:
            json_reader = json.load(file)
            for row in json_reader:
                ingredient = Ingredient(
                    name=row['name'],
                    measurement_unit=row['measurement_unit'])
                ingredient.save()
            self.stdout.write(self.style.SUCCESS(
                'Ингридиенты загружены в БД'))
