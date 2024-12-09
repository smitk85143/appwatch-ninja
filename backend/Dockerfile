# Use the official Python image as base
FROM python:3.11-slim

COPY entrypoint.sh /entrypoint.sh

ENV APP_HOME=/app
RUN mkdir $APP_HOME
RUN mkdir $APP_HOME/staticfiles
WORKDIR $APP_HOME

ENV PYTHONDONTWRITEBYTECODE=1

ENV PYTHONUNBUFFERED=1  

RUN pip3 install --upgrade pip 

COPY requirements.txt $APP_HOME/requirements.txt 

COPY . $APP_HOME/
RUN pip install uv
RUN uv venv
RUN uv pip sync $APP_HOME/requirements.txt

RUN apt-get update && apt-get install -y git curl
RUN uv pip install "aso @ git+https://github.com/smit-kukadiya/aso.git"

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ARG service=web
ENV SERVICE=$service

ENTRYPOINT ["/entrypoint.sh"]

# CMD ["gunicorn", "playstore_frontend.wsgi:application"]
CMD ["uv", "run", "uvicorn", "backend.asgi:application", "--reload", "--host", "0.0.0.0"]