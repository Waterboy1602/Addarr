# ADDARR
[![Docker Cloud Build Status](https://img.shields.io/docker/cloud/build/waterboy1602/addarr)](https://hub.docker.com/r/waterboy1602/addarr)

This is a TelegramBot made to add series to [Sonarr](https://github.com/Sonarr/Sonarr) or movies to [Radarr](https://github.com/Radarr/Radarr) with a couple of commands. You can also communicate with your [Transmission](https://transmissionbt.com/) installation to change its download speed.

## HOW IT WORKS
Authenticating a chat can be achieved by `/auth` or `auth`. The chat will ask you to enter the password and will response when it is correct or false. You need to enter the correct password, before you can do anything else.

If you've entered a wrong password, there will be saved a log to `addarr.log` with the timestamp, username and entered password. Possible errors from executing the code will also be saved there.

You can start the Transmission command with `/transmission` or `transmission`. After that you will be asked what you want to do. Just press the action you want and it's done.

You can start adding series/movies with `/start` or just `start`. The next steps will be made clear by the bot. At any time you can stop the adding by sending `/stop` or `stop`.

You can also start adding a series or movie with `/movie` or `/series` when the bot is running in English or `/film` or `/serie` when the bot is running in Dutch. This will skip the step of asking if the title represents a series or a movie.

Different entrypoints for all these commands can be entered in the config file, except `/movie`/`/film`/`series`/`serie`, which are defined in `lang.yaml`.

To receive a list of all the series on Sonarr you can use the command `/allSeries` or `allSeries`. This will give you their title, year, status and if they are monitored or not.

## FUNCTIONS    
- Add series/movies to Sonarr/Radarr
- List of series on Sonarr
- Change speed of Transmission
- Secure bot with a password. New chats first need to authenticate
- Wrong login attempts are saved in `addarr.log`
- Possibility to enable Transmission command only for admins

## COMMANDS
These are the default commands:
- Auth: authenticate the chat to use your bot
- Start: start adding a series or movie to Sonarr/Radarr
- Movie (en)/Film (nl): starting adding a movie to Radarr
- Series (en)/Serie (nl): starting adding a series to Sonarr
- allSeries: receive list of series on Sonarr
- Transmission: change the down-/upload speed of Transmission from Temporary Speed Limit to normal or the other way around
- Stop: stop the command you were executing

## CONFIG
An example of the config file can be found in this git. Change it to your configuration. After you're done, rename it to `config.yaml`.

## ADMIN    
There is a functionality to only let admins use the `transmission` command. Before you can use this, you should enable it in the config file `config.yaml`. Then you need to add the admins to `admin.txt`. You can add `username` or `id` of the user. Every added user should be on a new line to prevent errors.

## INSTALLATION
You can find the installation guides on the [wikipage](https://github.com/Waterboy1602/Addarr/wiki).
- [FreeBSD](https://github.com/Waterboy1602/Addarr/wiki/Installation-on-FreeBSD)
- [Docker](https://github.com/Waterboy1602/Addarr/wiki/Installation-on-Docker)
- [Windows](https://github.com/Waterboy1602/Addarr/wiki/Installation-on-Windows)
- [Linux](https://github.com/Waterboy1602/Addarr/wiki/Installation-on-Linux)

## SCREENSHOTS
<div style="float: left">
<img src="https://i.imgur.com/gO4UGG6.png" height="350" style="padding-right: 50px">
<img src="https://i.imgur.com/6UAmcAk.png" height="350" style="padding-right: 50px">
<img src="https://i.imgur.com/1X3xUNA.png" height="350" style="padding-right: 50px">
</div>
