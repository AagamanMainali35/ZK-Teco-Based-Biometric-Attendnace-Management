run:
	uv run python manage.py runserver

migrate:
	uv run python manage.py migrate

make-migrations:
	uv run python manage.py makemigrations

help:
	uv run python manage.py help
