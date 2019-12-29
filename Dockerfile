FROM python:3.6-alpine

WORKDIR /usr/src
# Install requirements
RUN apk add --no-cache gcc musl-dev libffi-dev openssl-dev
# Copy files to container
COPY . /usr/src/addarr
# Install ans build Addarr requirements, make symlink to redirect logs to stdout
RUN	cd addarr && \
	pip install --no-cache-dir -r requirements.txt --upgrade && \
	ln -s /dev/stdout /usr/src/telegramBot.log 

ENTRYPOINT ["python"]
CMD ["/usr/src/addarr/addarr.py"]
