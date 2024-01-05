# syntax=docker/dockerfile:1

FROM python:3.8-slim


WORKDIR /app
COPY . /app
RUN pip install -r requirements.txt
# RUN rm app.db app.db.bak

CMD ["flask", "run", "--port=5001", "--host=0.0.0.0"]
