FROM python:alpine

WORKDIR /app

# Install requirements
RUN apk add --no-cache \
            transmission-cli

# Copy files to container
COPY . /app

# Install ans build Addarr requirements, make symlink to redirect logs to stdout
RUN	pip install --no-cache-dir -r requirements.txt --upgrade

ENTRYPOINT ["python", "/app/src/addarr.py"]
