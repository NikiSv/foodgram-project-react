# Foodgram - Ваш продуктовый помощник

**О проекте**

«Фудграм» — это веб-платформа, где пользователи могут делиться своими рецептами, добавлять чужие рецепты в избранное и подписываться на публикации других авторов. Кроме того, доступен сервис «Список покупок», который помогает создавать список необходимых продуктов для выбранных блюд.

## Локальная установка

1. Склонируйте репозиторий с GitHub:
   ```bash
   git clone git@github.com:NikiSv/foodgram-project-react.git
   ```

2. Установите Docker:
   [Инструкции по установке Docker](https://docs.docker.com/engine/install/ubuntu/)

3. Установите Docker Compose:
   [Инструкции по установке Docker Compose](https://docs.docker.com/compose/install/)

4. Запустите проект с помощью команды:
   ```bash
   docker-compose up --build
   ```
   После этого, в новом терминальном окне выполните следующие действия:
   ```bash
   docker exec backend python manage.py migrate # выполните миграции
   docker exec backend python manage.py load_data # загрузите ингредиенты в БД
   docker exec backend python manage.py collectstatic # соберите статику 
   docker exec backend cp -r /app/collected_static/. /app/static/ # скопируйте статику в контейнер backend'а
   docker exec backend python manage.py createsuperuser # создайте суперпользователя
   ```

5. Перейдите в административную панель и создайте несколько тегов (без них рецепты не будут сохраняться).

6. Для просмотра результатов работы откройте новую вкладку браузера и перейдите по адресу [http://localhost/](http://localhost/), зарегистрируйтесь и создайте свои любимые рецепты.

**Примечание:** Спецификацию API можно ознакомиться по адресу [http://localhost/api/docs/](http://localhost/api/docs/)

## Подготовьте удаленный сервер:

1. Удалите из джобсов воркфлоу пункты `build_and_push_to_docker_hub` и `send_message`.

2. Cкопируйте файл `docker-compose.production.yml` на сервер и измените конфигурацию Nginx в соответствии с вашим проектом.
3. Запишите в Secrets на GitHub следующие ключи:
     ```
     DB_ENGINE=django.db.backends.postgresql
     DB_NAME=postgres
     POSTGRES_USER=postgres
     POSTGRES_PASSWORD=postgres
     DB_HOST=db 
     DB_PORT=5432
     HOST
     USER
     SSH_KEY
     SSH_PASSPHRASE
     ```

## Запуск на ВМ
 Запустите проект на сервере, выполнив следующие команды в корневой папке backend'а:
   ```bash
   git add .
   git commit -m "Ваш комментарий"
   git push
   docker exec backend python manage.py createsuperuser # создайте суперпользователя и выполните пункты 5 и 6 из "Локальная установка"
   ```

**Технологии:**
- Python
- Django Rest Framework
- Docker
- Nginx
- Postgres

---

*Создано с ❤️ .*