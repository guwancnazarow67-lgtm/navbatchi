FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DATA_DIR=/app/data
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN useradd -m navbatchi && mkdir -p /app/data && chown -R navbatchi /app/data
USER navbatchi

EXPOSE 8000
# Bitta worker: eslatmalar rejalashtiruvchisi bitta bo'lishi uchun
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--timeout", "60", "wsgi:app"]
