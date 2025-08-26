# IRC logger

IRC bot to log multiple servers. Controllable with raw IRC commands via private messages, password required. Able to find nicknames associated with a given nick, ident or IP.


## Installation commands

```
mkdir irc-logger
cd irc-logger
git clone https://github.com/neuralXray/irc-logger.git
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

### Dependencies

```
git clone https://github.com/neuralXray/irc-nicks-channels.git
```


## Configuration and Setup

1. Paths and passwords.
    * Inside `loggers.config.example` file:
        * Set the locations of the working directory, Python virtual environment, and log files.
        * Change the example passwords:
            * root: to control the bot with raw IRC commands.
            * access: for searching nicknames.
    * Rename the file to `loggers.config`.

2. Server, user and channels
    * Navigate to `logs.example` directory and edit the following files according to their template structure:
        * `loggers.txt`: Configure IRC servers, setting the bot's nick, ident and realname for each, along with the channels to log.
        * `ignore.txt`: Specify user masks to ignore. Write each one on a new line, preceded by the server address and a comma.
        * `ignore_msg.txt`: Add regular expressions to ignore matching private messages per server.

    * Rename the directory to `logs`. This directory can be moved anywhere, as long as its path is updated in `loggers.config`.

3. Start logging by executing:
    ```
    python3 loggers.py
    ```


## Support the developer

* Bitcoin: 1GDDJ7sLcBwFXg978qzCdsxrC8Ci9Dbgfa
* Monero: 4BGpHVqEWBtNwhwE2FECSt6vpuDMbLzrCFSUJHX5sPG44bZQYK1vN8MM97CbyC9ejSHpJANpJSLpxVrLQ2XT6xEXR8pzdCT
* Litecoin: LdaMXYuayfQmEQ4wsgR2Tp6om78caG3TEG
* Ethereum: 0x7862D03Dd9Dd5F1ebc020B2AaBd107d872ebA58E
* PayPal: paypal.me/neuralXray

