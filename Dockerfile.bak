FROM mysterysd/wzmlx:latest

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

RUN apt-get update && apt-get install -y apt-utils unzip zip #Install apt-utils, and zip/unzip together.

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
