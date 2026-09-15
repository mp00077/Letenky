from letenky.domain.price import utc_now


def run_due(repository, checker):
    repository.expire(utc_now())
    for watch in repository.due(utc_now()):
        checker.check(watch.id)
