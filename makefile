run:
	uv run python manage.py runserver

migrate:
	uv run python manage.py migrate

make-migrations:
	uv run python manage.py makemigrations

help:
	uv run python manage.py help

back-commit:
	GIT_AUTHOR_DATE="$(DATE)" GIT_COMMITTER_DATE="$(DATE)" git commit -m "$(MESSAGE)" --date="$(DATE)"

connect-db:
	psql -h localhost -U postgres -p 5432

seed_attendance:
	uv run python manage.py seed_attendance
