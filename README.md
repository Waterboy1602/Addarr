# TELEGRAM SONARR RADARR BOT

This is a bot made to add series to [Sonarr](https://github.com/Sonarr/Sonarr) or movies to [Radarr](https://github.com/Radarr/Radarr with a couple of commands.

For the moment I only mode a wikipage for installation on FreeBSD. If there is interest for other wikipages, just tell me and I will look into it.

# GUIDE


```
#!/bin/sh

#
# PROVIDE: telegramBot
# REQUIRE: networking
# KEYWORD:

. /etc/rc.subr

name="telegramBot"
rcvar="telegramBot_enable"
command="/usr/local/bin/python2.7 /usr/local/bazarr/bazarr.py"
telegramBot_user=root

start_cmd="telegramBot_start"

bazarr_start(){
        /usr/sbin/daemon -r -f -u $telegramBot_user $command
}

load_rc_config $name
: ${telegramBotbazarr_enable:=no}

run_rc_command "$1"
```

pkg update && pkg install python36
Install the required software pkg update && pkg install git python36
cd /usr/local
Clone the repository using git clone https://github.com/morpheus65535/bazarr.git (this will download the files to /usr/local/bazarr)
cd bazarr
Install Python requirements using pip install -r requirements.txt --upgrade
If you get this error message: pip: Command not found, you can refer to #642.
Check if it works python3.6 adderr.py. You should see TelegramBOT is started and waiting to receive messages