#!/bin/bash
set -e

# echo "Waiting for Elasticsearch..."
# until curl -s http://elasticsearch:9200/_cat/health > /dev/null; do
#   echo "Elasticsearch is unavailable - sleeping"
#   sleep 5
# done
# echo "Elasticsearch is up - continuing"

run_migrations() {
  echo "Running migrations..."
  
  # Check if the migrations table exists
  if ! uv run python3 $APP_HOME/manage.py showmigrations | grep -q '\[ \]'; then
    echo "Migrations already applied."
  else
    # Run migrations if they haven't been applied
    uv run python3 $APP_HOME/manage.py migrate
  fi
}

# Ensure migrations are done before running anything else
if [ "$1" != "celery" ]; then
  run_migrations
fi

if [ "$1" = "celery" ]; then
  # Run Celery without other tasks
  shift
  exec uv run celery "$@"
else

  uv run python3 $APP_HOME/manage.py collectstatic --noinput

  # Start Gunicorn
  # exec gunicorn --config gunicorn_config.py playstore_frontend.wsgi:application
  exec uv run uvicorn backend.asgi:application --reload --host 0.0.0.0
fi