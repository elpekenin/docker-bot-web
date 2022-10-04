FROM python:3.10.6
SHELL ["/bin/bash", "-c"]

MAINTAINER Pablo (elpekenin) Martinez Bernal "martinezbernalpablo@gmail.com"

# Download all files
WORKDIR /app
RUN git clone https://github.com/elpekenin/docker-bot-web && shopt -s dotglob && mv -v docker-bot-web/* .

# Install dependencies
RUN pip3 install -r requirements.txt

# Save build time
RUN date +%d/%m/%Y > build-timestamp

ENTRYPOINT ["python3", "main.py"]
