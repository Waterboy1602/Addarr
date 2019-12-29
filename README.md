# ADDARR

This is a TelegramBot made to add series to [Sonarr](https://github.com/Sonarr/Sonarr) or movies to [Radarr](https://github.com/Radarr/Radarr) with a couple of commands.

## HOW IT WORKS
You can start the bot with sending a message or command `/start`. 
The rest will be made clear by the bot.

## SCREENSHOTS
<div style="float: left">
<img src="https://i.imgur.com/gO4UGG6.png" height="350" style="padding-right: 50px">
<img src="https://i.imgur.com/6UAmcAk.png" height="350" style="padding-right: 50px">
<img src="https://i.imgur.com/1X3xUNA.png" height="350" style="padding-right: 50px">
</div>

## INSTALLATION
### FreeBSD
For the moment I only made a wikipage for [installation on FreeBSD](https://github.com/Waterboy1602/Addarr/wiki/Installation-on-FreeBSD). If there is interest for other wikipages, just tell me and I will look for it.
### Docker
* To build a docker image use the command `docker-compose build`.
* After that copy the provided `config_example.yaml` to `config.yaml` and set the values to your configuration.
* Then you can use the provided docker-compose file to run the bot using the command `docker-compose up -d`.
