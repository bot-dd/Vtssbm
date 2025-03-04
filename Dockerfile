FROM mysterysd/wzmlx:latest

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

COPY ac.zip .

RUN unzip -o ac.zip

COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

COPY ac.zip .

RUN unzip -o ac.zip


COPY . .

COPY ac.zip .

RUN unzip -o ac.zip


CMD ["bash", "start.sh"]
