# syntax=docker/dockerfile:1

FROM python:3.12-slim


WORKDIR /app
COPY . /app
RUN bash docker/install.sh

# CMD ["flask", "run", "--port=5001", "--host=0.0.0.0"]
