# YaMSv2 - Yet another MarketScanner v2

YaMS v2 is intended to pull data from exchanges, populating indicators to the stream and saving it to several databases (Postrgres, InfluxDB). Afterwards you can use Grafana/Kapacitor/${WHATEVER} to create dashboard overviews and alerts.

![Architecture](docs/YaMSv2.jpg)

# Features
- Supported Exchanges:
  - Bittrex (via REST-Api)
- create your own strategy and indicator as a plugin

# Requirements
- docker

# Usage
* build and run
```
cp sample.config.yml config.yml
docker-compose down && docker-compose build && docker-compose up
```

* cleanup
```
docker run --rm -ti yamsv2_app_tracker /bin/bash
docker-compose down && rm -rf data/
for i in $(docker ps -a -q); do docker rm -f "${i}"; done
for i in $(docker images -a -q); do docker rmi "${i}"; done
```

* Forwarding rules:
```
ssh host -L 8080:0.0.0.0:80 -L 8083:0.0.0.0:8083 -L 8086:0.0.0.0:8086
```

# Contributing
Feel like there is a feature missing? I welcome your pull requests! Few pointers for contributions:

- Create your PR against the `master` branch
- If you are unsure, discuss the feature on the [btc-echo slack](https://btc-echo.slack.com/) in room `#tools` or in a [github issue](https://github.com/YaMSorg/yams/issues) before

# Donations
Feel like you wanna honor my work? That's awesome! Just ask me in the Chat for a donation address :)

# TODO
- redis to own image:
```
redis_1          | 1:C 05 Nov 19:27:45.425 # oO0OoO0OoO0Oo Redis is starting oO0OoO0OoO0Oo
redis_1          | 1:C 05 Nov 19:27:45.426 # Redis version=4.0.2, bits=64, commit=00000000, modified=0, pid=1, just started
redis_1          | 1:C 05 Nov 19:27:45.426 # Warning: no config file specified, using the default config. In order to specify a config file use redis-server /path/to/redis.conf
redis_1          | 1:M 05 Nov 19:27:45.426 * Running mode=standalone, port=6379.
redis_1          | 1:M 05 Nov 19:27:45.427 # WARNING: The TCP backlog setting of 511 cannot be enforced because /proc/sys/net/core/somaxconn is set to the lower value of 128.
redis_1          | 1:M 05 Nov 19:27:45.427 # Server initialized
redis_1          | 1:M 05 Nov 19:27:45.428 # WARNING you have Transparent Huge Pages (THP) support enabled in your kernel. This will create latency and memory usage issues with Redis. To fix this issue run the command 'echo never > /sys/kernel/mm/transparent_hugepage/enabled' as root, and add it to your /etc/rc.local in order to retain the setting after a reboot. Redis must be restarted after THP is disabled.
redis_1          | 1:M 05 Nov 19:27:45.429 * DB loaded from disk: 0.001 seconds
redis_1          | 1:M 05 Nov 19:27:45.429 * Ready to accept connections
```
- db image: send message to redis, when db is finally loaded
- monitoring!
- keep-alive thread which sends out a str+nonce to controller and back 
  - use different strigns for db ready and keepalive(ping-pong) of controller or getter
- use extra redis channel for "which data should be received next"-queue, for the getter as well as when controller detects len(data)==0  


# Queries
```
SHOW MEASUREMENTS
SHOW FIELD KEYS FROM "all"

SELECT "close" FROM "btrx-BTC-1ST-5m" WHERE "tval" > now() - 30m
SELECT DIFFERENCE("close") FROM "btrx-BTC-1ST-5m" WHERE "tval" > now() - 30m

SELECT "pair", "close" FROM "btrx" WHERE time = '2017-11-14T18:00:00Z'
SHOW TAG VALUES FROM "btrx" WITH KEY = "pair"
```
