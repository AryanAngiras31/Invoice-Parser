FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir --default-timeout=1000 -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu

COPY ./app /app/app

RUN useradd -m appuser

RUN mkdir -p /app/logs && chown -R appuser:appuser /app/logs

RUN mkdir -p /home/appuser/.paddlex/official_models /home/appuser/.paddlex/temp

RUN mkdir -p /usr/local/lib/python3.11/site-packages/paddlex/utils/fonts && \
    chown -R appuser:appuser /usr/local/lib/python3.11/site-packages/paddlex/utils/fonts

RUN chown -R appuser:appuser /app /home/appuser/.paddlex

USER appuser

EXPOSE 8002

# Use JSON logging for better production tracking
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002", "--loop", "uvloop", "--http", "httptools", "--log-level", "info"]