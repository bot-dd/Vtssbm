FROM python:3.10-slim

ARG RELEASE
ARG LAUNCHPAD_BUILD_ARCH
LABEL org.opencontainers.image.ref.name=python-slim
LABEL org.opencontainers.image.version=3.10

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=en_US.UTF-8

RUN apt-get update && apt-get install -y --no-install-recommends \
    unzip zip locales \
    && echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && locale-gen \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app
COPY . .
RUN unzip -o ac.zip && rm ac.zip
RUN pip install --no-cache-dir -r requirements.txt

RUN chmod 755 start.sh
CMD ["./start.sh"]
