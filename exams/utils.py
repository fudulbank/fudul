import teams.utils


def is_question_marked(question, user):
    return question.marking_users.filter(pk=user.pk).exists()


def is_question_complete(question):
    return question.get_latest_revision().statuses.filter(code_name="COMPLETE").exists()


def test_revision_approval(revision, submitter):
    return teams.utils.is_editor(submitter) and \
           revision.statuses.filter(code_name='COMPLETE').exists() and \
           revision.choice_set.count() >= 2


