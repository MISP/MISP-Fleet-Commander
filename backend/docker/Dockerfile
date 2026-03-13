# syntax=docker/dockerfile:1

FROM python:3.12-slim

# Define build arguments with default values
ARG FLASK_APP=wsgi.py
ARG FLASK_ENV=production

# Set environment variables for the build
ENV FLASK_APP=$FLASK_APP
ENV FLASK_ENV=$FLASK_ENV

WORKDIR /app
COPY . /app
RUN bash docker/install.sh

# CMD ["flask", "run", "--port=5001", "--host=0.0.0.0"]
