FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CONFIG_PATH=/config/config.yaml

WORKDIR /app

RUN apk add --no-cache gcc musl-dev libffi-dev

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/main.py .

RUN mkdir /config

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers"]