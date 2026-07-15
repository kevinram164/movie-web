FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -u 1001 -r -g 0 -m -d /home/app -s /sbin/nologin app \
    && mkdir -p /tmp/cinehome-work \
    && chown -R 1001:0 /tmp/cinehome-work

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY worker ./worker

USER 1001

CMD ["python", "-m", "worker.main"]
