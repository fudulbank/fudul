import rules


@rules.predicate
def can_access_session(user, session):
    return user.is_superuser or \
        session.submitter == user

rules.add_rule('can_access_session', can_access_session)
