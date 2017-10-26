# YaMSv2
Yet another MarketScanner v2

YaMS v2 is intended to pull data from exchanges (every 5m, 30m, 4h, 1d), adding indicators to the stream and saving it to an elastisearch instance where you can further investigate your strategies with Kibana.
 
![Architecture](docs/YaMSv2.jpg)

# Features
- Supported Exchanges:
  - Bittrex (via REST-Api)
- create your own strategy and indicator as a plugin

# Requirements
- docker

# Usage
```
$ cp sample.config.yml config.yml
$ bash startup.sh
```

# Contributing
Feel like there is a feature missing? I welcome your pull requests! Few pointers for contributions:

- Create your PR against the `master` branch
- If you are unsure, discuss the feature on the [btc-echo slack](https://btc-echo.slack.com/) in room `#tools` or in a [github issue](https://github.com/YaMSorg/yams/issues) before

# Donations
Feel like you wanna honor my work? That's awesome!
Just ask me in the Chat for a donation address :)

# Links
* https://stackoverflow.com/questions/45595750/use-django-orm-outside-of-django
* https://stackoverflow.com/questions/41825037/how-to-execute-external-script-in-the-django-environment/41826771#41826771
* https://stackoverflow.com/questions/33170016/how-to-use-django-1-8-5-orm-without-creating-a-django-project
