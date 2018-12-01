#!/usr/bin/python3

import subprocess, re, time, argparse, sys
import functools as ft
import itertools as it
from datetime import datetime
from maybe import *
from typing import Callable, Generic, List, Iterable

A = TypeVar('A')
DateTime = TypeVar('DateTime')
statefile = '/tmp/myusb-last.dat'

log_datetime_fmt = "^([A-Za-z]{3} +\d+ +\d+:\d+:\d+)"
log_usb_detect_fmt = log_datetime_fmt + \
                     ".+ kernel: \\[ *\d+\\.\d+\\]"\
                     " *sd[a-z]: (sd[a-z][0-9])"

def current_time() -> DateTime:
    return datetime.now()

def dmesg(pred: Callable[[str], bool] = lambda x: True) -> List[str]:
    return filter(pred,
                  str(subprocess.check_output(['tail',
                                               '-n',
                                               '10',
                                               '/var/log/kern.log']))\
                  .split('\\n'))

def parse_datetime(dmesg_line: str) -> Maybe[DateTime]:
    m = re.search(log_datetime_fmt, dmesg_line)
    this_year = str(datetime.now().year)
    return Just(datetime.strptime(m.group(1) + " " + this_year,
                                  "%b %d %H:%M:%S %Y")) if m \
                                  else Nothing()

# Is the given `time` within `range_s` from `reference`?
# Assumption: `time` < `reference`
def time_within(range_s: int,
                reference: DateTime,
                time: DateTime) -> bool:
    return abs((time - reference).total_seconds()) <= range_s

# Is the given `dmesg_line` within `range_s` of `time`?
def dmesg_time_within(range_s: int,
                      time: DateTime,
                      dmesg_line: str) -> bool:
    dmesg_time = parse_datetime(dmesg_line)
    return dmesg_time.map(lambda msg_time: \
                          time_within(range_s, time, msg_time))\
                     .getDefault(False)

def dmesg_within(range_s: int, from_time: DateTime) -> Callable[[str], bool]:
    return ft.partial(dmesg_time_within, range_s, from_time)

def detected_usb(msg: str) -> Maybe[str]:
    m = re.search(log_usb_detect_fmt, msg)
    return Just(m.group(2)) if m else Nothing()

def last(seq: Iterable[A]) -> Maybe[A]:
    l = list(seq)
    return Just(f'/dev/{l[-1]}') if l else Nothing()

def filtermap(f: Callable[[A], Maybe[B]], seq: Iterable[A]) -> Iterable[B]:
    for el in seq:
        res = f(el)
        if res.isNonEmpty():
            yield res.get()

def last_detected_usb(time_range_s: int = 30) -> Maybe[str]:
    uptime_now = current_time()
    recent_dmesgs = dmesg(dmesg_within(time_range_s, uptime_now))
    detected_usbs = filtermap(detected_usb, recent_dmesgs)
    return last(detected_usbs)

# returns mount path
def mount_usb(path: str, log_path: bool = True) -> Maybe[str]:
    try:
        res = subprocess.run(['udisksctl', 'mount',
                              '--no-user-interaction',
                              '-b', path],
                             stdout=subprocess.PIPE)
        mount_msg = res.stdout.decode('utf-8')
    except subprocess.CalledProcessError:
        mount_msg = ""

    m = re.search(f'^Mounted {path} at (.+)\\.$', mount_msg)
    if m:
        if log_path: log_mounted_path(path)
        return Just((path, m.group(1)))
    else:
        return Nothing()

def unmount_usb(path: str) -> int:
    a = subprocess.call (['sync'])
    b = subprocess.call(['udisksctl', 'unmount',
                         '--no-user-interaction',
                         '-b', path])
    c = subprocess.call(['udisksctl', 'power-off',
                         '--no-user-interaction',
                         '-b', path])
    return a or b or c

def automount_usb(timeout_remaining_s = 10, time_range_s = 10):
    if timeout_remaining_s < 1:
        return Nothing()
    else:
        usb = last_detected_usb(time_range_s)
        try_again = lambda: time.sleep(1) or \
                    automount_usb(timeout_remaining_s - 1)
        return usb.bind(mount_usb)\
                  .otherwise(try_again)

def log_mounted_path(path: str) -> None:
    with open(statefile, 'w') as f:
        f.write(path)

def read_last_mounted_path() -> Maybe[str]:
    try:
        with open(statefile, 'r') as f:
            contents = f.read()
            return Just(contents) if contents else Nothing()
    except FileNotFoundError:
        return Nothing()

def autounmount_usb() -> Maybe[int]:
    return read_last_mounted_path().map(unmount_usb)

# Pair[str, str] -> int
def print_pair(p):
    print(p[0])
    print(p[1])
    return 0

def print_error(msg: str) -> Callable[[], int]:
    return lambda: print(msg) or 1

def parseArgs():
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--mount", action="store_true",
                        help="Mount an auto-detected usb.")
    parser.add_argument("-e", "--autoeject", action="store_true",
                        help="Eject the last mounted usb.")
    parser.add_argument("-E", "--eject", type=str,
                        help="Eject the usb at the given path.")
    parser.add_argument("-T", "--timeout", type=int, default=10,
                        help="Specify how long (seconds, max) to search "
                        "for a usb.")
    parser.add_argument("-t", "--timerange", type=int, default=10,
                        help="Specify the time (seconds) backward to consider"
                        " from now when detecting usbs.")
    return parser.parse_args()

def main():
    args = parseArgs()
    if args.mount:
        return automount_usb(args.timeout, args.timerange)\
            .either(print_pair,
                    print_error("No usb found!"))
    elif args.autoeject:
        return autounmount_usb()\
            .bind(lambda x: Just(x) if x == 0 else Nothing())\
            .either(lambda x: print("Ejected.") or 0,
                    print_error('Failed to eject.'))
    elif args.eject:
        return unmount_usb(args.eject)

if __name__ == '__main__':
    sys.exit(main())
