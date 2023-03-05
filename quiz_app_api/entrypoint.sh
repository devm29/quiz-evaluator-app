#!/bin/sh
# Bring the database up to date and make sure the stack is never empty on a
# first boot, then hand off to whatever command the image was given.
set -eu

echo "==> Applying migrations"
python manage.py migrate --noinput

echo "==> Seeding questions and sample submissions"
python manage.py seed_quiz

echo "==> Collecting static files (the admin's CSS)"
python manage.py collectstatic --noinput

echo "==> Starting: $*"
exec "$@"
