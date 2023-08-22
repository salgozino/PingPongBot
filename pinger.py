import argparse

from PingPong import PingPongBot


def add_args():
    parser = argparse.ArgumentParser("Ping Creator")
    parser.add_argument(
        "n_pings", help="An integer with the amount of pings to perform.",
        type=int,
        default=1
    )
    return parser.parse_args()


if __name__ == '__main__':
    args = add_args()
    bot = PingPongBot(
        address='0xC09A0F03708D8772e472C1B8B321e871df2145f9'
    )
    bot.do_ping(args.n_pings)
