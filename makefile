run:
	uv run python manage.py runserver "$(port)"

migrate:
	uv run python manage.py migrate

make-migrations:
	uv run python manage.py makemigrations

help:
	uv run python manage.py help

back-commit:
	GIT_AUTHOR_DATE="$(date)" GIT_COMMITTER_DATE="$(date)" git commit -m "$(message)" --date="$(date)"

connect-db:
	psql -h localhost -U postgres -p 5432

seed_attendance:
	uv run python manage.py seed_attendance

shell:
	uv run python manage.py shell
