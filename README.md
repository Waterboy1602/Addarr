# ADDARR
[![Docker Cloud Build Status](https://img.shields.io/docker/cloud/build/waterboy1602/addarr)](https://hub.docker.com/r/waterboy1602/addarr)

This is a TelegramBot made to add series to [Sonarr](https://github.com/Sonarr/Sonarr) or movies to [Radarr](https://github.com/Radarr/Radarr) with a couple of commands.

## HOW IT WORKS
You can start the bot with sending `/start` or just `start`. At any time you can stop with the bot by sending `/stop` or `stop`. The first time you use `start` you will be asked to enter your password you set in the config file. You will only need to do this one time. The chatId will be saved to a file and be checked there every time.
The next steps will be made clear by the bot.

## SCREENSHOTS
<div style="float: left">
<img src="https://i.imgur.com/gO4UGG6.png" height="350" style="padding-right: 50px">
<img src="https://i.imgur.com/6UAmcAk.png" height="350" style="padding-right: 50px">
<img src="https://i.imgur.com/1X3xUNA.png" height="350" style="padding-right: 50px">
</div>

## INSTALLATION
For the moment there is only an installation guide for [FreeBSD](https://github.com/Waterboy1602/Addarr/wiki/Installation-on-FreeBSD) and Docker. If there is any interest for other guides, just tell me and I will look for it.
### Docker
* `docker pull waterboy1602/addarr`
* Rename the provided `config_example.yaml` to `config.yaml` and set the values to your configuration.
* Then you can use the provided docker-compose file to run the bot using the command `docker-compose up -d`.

All the credits for the docker setup go to [@tedvdb](https://github.com/tedvdb) and [@schoentoon](https://github.com/schoentoon).
