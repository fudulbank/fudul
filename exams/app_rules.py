import rules


@rules.predicate
def can_access_session(user, session):
    return user.is_superuser or \
        session.submitter == user

@rules.predicate
def can_access_exam(user, exam):
    return user.is_superuser or \
        exam.can_user_access(user)

rules.add_perm('exams.access_session', can_access_session)
rules.add_perm('exams.access_exam', can_access_exam)
