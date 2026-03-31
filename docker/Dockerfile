FROM python:3.12-alpine

ARG CONTAINER_PORT=8080

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CONFIG_PATH=/config/config.yaml
ENV RUN_PORT=${CONTAINER_PORT}

WORKDIR /app

RUN apk add --no-cache gcc musl-dev libffi-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/main.py .

RUN mkdir /config

EXPOSE ${RUN_PORT}

CMD uvicorn main:app --host 0.0.0.0 --port ${RUN_PORT} --proxy-headers