import sys


def main():
    from .ui.window import App
    return App().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
