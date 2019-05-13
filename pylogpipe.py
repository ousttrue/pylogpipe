import pathlib
import asyncio
import sys
import signal
import subprocess
import logging
from typing import BinaryIO, Callable
'''
* __file__と同じパスの pywarp.conf に記述された exe を実行する
* 引数 sys.argv[1:] を exe にすべて渡す
* PIPEを経由して接続して内容を pywarp.log に loggingする
'''

VERSION = [0, 0, 1]


# if sys.platform == "win32":
#     import signal
#     signal.signal(signal.SIGINT, signal.SIG_DFL)


async def async_stream_connector(name: str, r: BinaryIO, w: BinaryIO,
                                 running: Callable):
    logger = logging.getLogger(name)

    loop = asyncio.get_running_loop()

    buf = bytearray()

    try:
        while running():
            b = await loop.run_in_executor(None, r.read, 1)
            if not b:
                logger.debug('%s break', name)
                break

            w.write(b)
            buf.append(b[0])
            if b == b'\n':
                logger.debug('%s', bytes(buf).decode('utf-8').rstrip())
                buf.clear()
    except RuntimeError as err:
        logger.error(err)


async def async_stream(p):
    def running() -> bool:
        return p.returncode is None

    # stdout to stdout
    asyncio.create_task(
        async_stream_connector('stdout', p.stdout, sys.stdout.buffer, running))
    # stderr to stderr
    asyncio.create_task(
        async_stream_connector('stderr', p.stderr, sys.stderr.buffer, running))

    # stdin to stdin
    await async_stream_connector('stdin', sys.stdin.buffer, p.stdin, running)

    p.terminate()


def setup_logger(logfile):
    # setup logger
    level = logging.DEBUG
    # clear output
    logging.lastResort = logging.NullHandler()
    handler = logging.FileHandler(logfile, encoding='utf-8')
    handler.setLevel(level)
    fmt = '%(asctime)s[%(name)s] %(message)s'
    f = logging.Formatter(fmt, '%H:%M:%S')
    handler.setFormatter(f)

    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(level)


def main():
    # launch process
    self = pathlib.Path(__file__).resolve()

    logfile = self.parent / (self.stem + '.log')
    setup_logger(logfile)

    conf = self.parent / (self.stem + '.conf')
    cmd = conf.read_text(encoding='utf-8').strip()
    p = subprocess.Popen([cmd] + sys.argv[1:],
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         stdin=subprocess.PIPE)

    # start stream
    asyncio.run(async_stream(p))


if __name__ == '__main__':
    main()
