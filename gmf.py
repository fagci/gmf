#!/usr/bin/env python3
"""Global Misconfig Finder"""
from argparse import ArgumentParser
from functools import cached_property
from http.client import HTTPConnection
from ipaddress import IPV4LENGTH, IPv4Address
from queue import Queue
from random import randrange
import re
from socket import setdefaulttimeout
import sys
from threading import Event, Thread

MAX_IPV4 = 1 << IPV4LENGTH


class Checker(Thread):
    def __init__(self, q: Queue, r: Event, p: str, exclude: str):
        super().__init__(daemon=True)
        self._q = q
        self._r = r
        self._p = p
        self._ex = re.compile(exclude)

    def check(self, ip):
        try:
            c = HTTPConnection(ip)
            c.request('GET', self.rand_path)
            r = c.getresponse()
            r.read()
            if 100 <= r.status < 300:
                return False
            c.request('GET', self._p)
            r = c.getresponse()
            text = r.read().decode(errors='ignore').lower()
            c.close()
            return 100 <= r.status < 300 and not self._ex.match(text)
        except:
            return False

    def run(self):
        while self._r.is_set():
            ip = self._q.get()
            if not ip:
                break
            if self.check(ip):
                print(ip)
                if not sys.stdout.isatty():
                    sys.stderr.write(f'{ip}\n')

    @staticmethod
    def rand_char():
        return chr(randrange(ord('a'), ord('z') + 1))

    @cached_property
    def rand_path(self):
        p = ''.join(self.rand_char() for _ in range(8))
        return f'/{p}'


class Generator(Thread):
    def __init__(self, q: Queue, r: Event, c=1000000):
        super().__init__(daemon=True)
        self._q = q
        self._r = r
        self._c = c

    def run(self):
        while self._r.is_set() and self._c:
            ip_address = IPv4Address(randrange(0, MAX_IPV4))
            if ip_address.is_global and not ip_address.is_multicast:
                self._c -= 1
                self._q.put(str(ip_address))


def main(path, workers, timeout, limit, exclude):
    sys.stderr.write('--=[ G M F ]=--\n')
    threads = []
    queue = Queue(workers * 3)
    running = Event()

    setdefaulttimeout(timeout)

    try:
        running.set()
        for _ in range(workers):
            t = Checker(queue, running, path, exclude)
            threads.append(t)
            t.start()

        sys.stderr.write('....working....')
        sys.stderr.write('\n')

        gen = Generator(queue, running, limit)
        gen.start()
        gen.join()

        for t in threads:
            queue.put(None)

        for t in threads:
            t.join()
    except KeyboardInterrupt:
        sys.stderr.write('\rStopping...\n')
        running.clear()

    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        sys.stderr.write('\r-----forced-----\n')
    else:
        sys.stderr.write('----- end -----\n')


if __name__ == '__main__':
    ap = ArgumentParser()
    ap.add_argument('path', type=str)
    ap.add_argument('-w', '--workers', type=int, default=512)
    ap.add_argument('-t', '--timeout', type=float, default=0.75)
    ap.add_argument('-l', '--limit', type=int, default=1000000)
    ap.add_argument('-x',
                    '--exclude',
                    type=str,
                    default='<(!doctype|html|head|body|br)')
    main(**vars(ap.parse_args()))
