#!/usr/bin/env python3
"""Global Misconfig Finder"""
from argparse import ArgumentParser
from functools import cached_property
from http.client import HTTPConnection, HTTPException, HTTPSConnection
from ipaddress import IPV4LENGTH, IPv4Address
from random import randrange
import re
from socket import setdefaulttimeout, timeout as STimeout
import sys
from threading import Event, Thread

MAX_IPV4 = 1 << IPV4LENGTH


class Checker(Thread):
    __slots__ = ('_q', '_r', '_p', '_port', '_proxy', '_sb', '_ex', '__c')

    def __init__(self, r: Event, generator, path, port, exclude, proxy,
                 show_body):
        super().__init__()
        self._r = r
        self._p = path
        self._port = port
        self._proxy = proxy
        self._sb = show_body
        self._ex = re.compile(exclude, re.I) if exclude else None
        self._gen = generator

    def connect(self, ip):
        if self._port == 443:
            from ssl import _create_unverified_context as cuc
            self.__c = HTTPSConnection(ip, context=cuc())
        else:
            self.__c = HTTPConnection(ip, port=self._port)

        if self._proxy:
            ph, pp = self._proxy.split(':')
            self.__c.set_tunnel(ph, int(pp))

    def disconnect(self):
        self.__c.close()

    def pre_check(self):
        self.__c.request('GET', self.rand_path)
        r = self.__c.getresponse()
        r.close()

        return not 100 <= r.status < 300

    def check(self):
        self.__c.request('GET', self._p)
        r = self.__c.getresponse()
        data = r.read()
        text = data.decode(errors='ignore')
        body = '<binary file>' if self.is_binary(data) else text

        if self._ex and self._ex.findall(text):
            return False, body

        return 100 <= r.status < 300, body

    def run(self):
        while self._r.is_set():
            try:
                ip = next(self._gen)
            except:
                return

            if not ip:
                break

            try:
                self.connect(ip)
                if not self.pre_check():
                    continue
                result, body = self.check()
                if result:
                    self.print_result(ip, body)
                self.disconnect()
            except OSError as e:
                if str(e).startswith('Tunnel'):
                    print(e)
                    self._r.clear()
            except (STimeout, HTTPException) as e:
                pass
            except Exception as e:
                sys.stderr.write(repr(e))
                sys.stderr.write('\n')

    def print_result(self, ip, body):
        print(ip)
        if self._sb:
            print(body, end='\n_______________\n')
        if not sys.stdout.isatty():
            sys.stderr.write(f'{ip}\n')

    @staticmethod
    def is_binary(body: bytes):
        textchars = bytearray({7, 8, 9, 10, 12, 13, 27}
                              | set(range(0x20, 0x100)) - {0x7f})
        return bool(body.translate(None, textchars))

    @staticmethod
    def rand_char():
        return chr(randrange(ord('a'), ord('z') + 1))

    @cached_property
    def rand_path(self):
        p = ''.join(self.rand_char() for _ in range(8))
        return f'/{p}'


def ip_generator(count):
    while count:
        ip_address = IPv4Address(randrange(0, MAX_IPV4))
        if ip_address.is_global and not ip_address.is_multicast:
            count -= 1
            yield str(ip_address)


def main(path, workers, timeout, limit, exclude, proxy, show_body, port):
    sys.stderr.write('--=[ G M F ]=--\n')
    threads = []
    running = Event()
    running.set()

    setdefaulttimeout(timeout)

    generator = ip_generator(limit)

    for _ in range(workers):
        t = Checker(running, generator, path, port, exclude, proxy, show_body)
        threads.append(t)

    sys.stderr.write('....working....')
    sys.stderr.write('\n')

    try:
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        print('threads end?')
    except KeyboardInterrupt:
        running.clear()
        sys.stderr.write('\rStopping...\n')

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        sys.stderr.write('\r-----force-----\n')
    else:
        sys.stderr.write('----- end -----\n')


if __name__ == '__main__':
    ap = ArgumentParser()
    ap.add_argument('path', type=str)
    ap.add_argument('-p', '--port', type=int, default=80)
    ap.add_argument('-w', '--workers', type=int, default=512)
    ap.add_argument('-t', '--timeout', type=float, default=0.75)
    ap.add_argument('-l', '--limit', type=int, default=1000000)
    ap.add_argument('--proxy', type=str, default='')
    ap.add_argument('-b', '--show-body', default=False, action='store_true')
    ap.add_argument('-x',
                    '--exclude',
                    type=str,
                    default='<(!doctype|html|head|body|br)')
    main(**vars(ap.parse_args()))
