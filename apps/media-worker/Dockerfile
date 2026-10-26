FROM python:3.12-slim-trixie
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
         ffmpeg \
         libexpat1=2.9.0-1~deb13u1 \
    && dpkg -l libexpat1 | grep -F '2.9.0-1~deb13u1' \
    && rm -rf /var/lib/apt/lists/* \
    && useradd -u 1001 -r -g 0 -m -d /home/app -s /sbin/nologin app \
    && mkdir -p /tmp/cinehome-work \
    && chown -R 1001:0 /tmp/cinehome-work

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir --force-reinstall "setuptools==75.8.2"

COPY worker ./worker

USER 1001

CMD ["python", "-m", "worker.main"]
