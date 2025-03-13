FROM mysterysd/wzmlx:latest

WORKDIR /usr/src/app
RUN chmod 777 /usr/src/app

# Git install

# Upgrade pip, setuptools এবং setuptools-scm সমস্যার সমাধান
RUN pip3 install --upgrade pip setuptools
RUN pip3 install --no-cache-dir --upgrade setuptools-scm

COPY requirements.txt .

# নির্দিষ্ট setuptools সংস্করণ সহ requirements ইনস্টল
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .

CMD ["bash", "start.sh"]
