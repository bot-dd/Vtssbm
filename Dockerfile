FROM mysterysd/wzmlx:latest


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
