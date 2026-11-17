from pathlib import Path

from premier_demo.startup import failure_hint

if __name__ == '__main__':
    try:
        from premier_demo.launcher import main
        result = main(Path(__file__).resolve().parent)
    except Exception as error:
        print(failure_hint(error))
        result = 1
    raise SystemExit(result)
