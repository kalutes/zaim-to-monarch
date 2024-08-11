FROM python:3

RUN apt-get update
RUN apt-get install -y wget \
    unzip \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libc6 \
    libcairo2 \
    libcups2 \
    libdbus-1-3 \
    libexpat1 \
    libfontconfig1 \
    libgbm1 \
    libgcc1 \
    libglib2.0-0 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libstdc++6 \
    libx11-6 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxcursor1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxi6 \
    libxrandr2 \
    libxrender1 \
    libxss1 \
    libxtst6 \
    lsb-release \
    xdg-utils

WORKDIR /usr/src/zaim-to-monarch

RUN useradd -ms /bin/bash zaim-to-monarch
RUN chown zaim-to-monarch /usr/src/zaim-to-monarch

USER zaim-to-monarch

ENV VIRTUAL_ENV=/usr/src/zaim-to-monarch/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install dependencies:
COPY requirements.txt /usr/src/zaim-to-monarch/
RUN pip install -r /usr/src/zaim-to-monarch/requirements.txt

COPY . /usr/src/zaim-to-monarch/
ENTRYPOINT ["python3", "main.py"]
