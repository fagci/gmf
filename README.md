# Global Misconfig Finder

Searches webserver misconfigs over all internet.

```
usage: gmf.py [-h] [-w WORKERS] [-t TIMEOUT] [-l LIMIT] [--proxy PROXY] [-b]
              [-x EXCLUDE]
              path

positional arguments:
  path

optional arguments:
  -h, --help            show this help message and exit
  -w WORKERS, --workers WORKERS
  -t TIMEOUT, --timeout TIMEOUT
  -l LIMIT, --limit LIMIT
  --proxy PROXY
  -b, --show-body
  -x EXCLUDE, --exclude EXCLUDE
```

# Examples

```sh
xport PYTHONUNBUFFERED=1
./gmf.py /favicon.ico \
  | parallel -uj1 wget http://{}/favicon.ico \
    -O  ~/storage/pictures/fav/{}.ico
```

_Only for educational purposes_
