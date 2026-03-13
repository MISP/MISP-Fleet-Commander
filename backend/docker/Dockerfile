# syntax=docker/dockerfile:1

FROM node:18-alpine as build

WORKDIR /app

COPY web/package*.json ./

RUN npm install

COPY web/ .

RUN npm run build

FROM python:3.12-slim


WORKDIR /app
COPY backend/ /app
RUN bash docker/install.sh

COPY --from=build /app/dist /app/application/dist

# CMD ["flask", "run", "--port=5001", "--host=0.0.0.0"]
