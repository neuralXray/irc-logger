# IRC logger

IRC bot to log multiple servers. Controllable with irc raw command in private messages, password required. Able to find nicks that have been connected with a given ident or ip.


## Installation Instructions

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


## Start logging

Edit paths configuring location of working directory (script `loggers.py` and its dependencies), python virtual environment and logging text files at `loggers.config.example`. Finally, rename to `loggers.config`.

Edit configuration files inside `logs.example`, setting irc servers, nick, ident, realname and channels to log. Finally, rename the directory to `logs`.

Start logging executing:

```
python3 loggers.py
```


## Support the developer

* Bitcoin: 1GDDJ7sLcBwFXg978qzCdsxrC8Ci9Dbgfa
* Monero: 4BGpHVqEWBtNwhwE2FECSt6vpuDMbLzrCFSUJHX5sPG44bZQYK1vN8MM97CbyC9ejSHpJANpJSLpxVrLQ2XT6xEXR8pzdCT
* Litecoin: LdaMXYuayfQmEQ4wsgR2Tp6om78caG3TEG
* Ethereum: 0x7862D03Dd9Dd5F1ebc020B2AaBd107d872ebA58E
* PayPal: paypal.me/neuralXray

