FROM python:3.12-slim

WORKDIR /app

COPY req.txt .


RUN pip install --no-cache-dir -r req.txt

COPY . .


EXPOSE 5000

ENV FLASK_ENV=production \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

CMD [ "uvicorn", "app:app", "--port=5000"]