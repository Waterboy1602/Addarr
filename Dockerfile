FROM python:3.8-alpine

WORKDIR /app
# Install requirements
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev
# Copy files to container
COPY . /app
# Install ans build Addarr requirements, make symlink to redirect logs to stdout
RUN	pip install --no-cache-dir -r requirements.txt --upgrade

ENTRYPOINT ["python", "/app/addarr.py"]
