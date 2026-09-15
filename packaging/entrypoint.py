from letenky.bootstrap import main

if __name__ == "__main__":
    import sys
    try:
        raise SystemExit(main())
    except Exception:
        if "--smoke-test" in sys.argv:
            import traceback
            if sys.stderr:
                traceback.print_exc()
            raise SystemExit(1)
        raise
