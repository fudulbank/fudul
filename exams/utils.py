import teams.utils

# FIXME: The field should be `marked_questions`
def is_question_marked(question, session):
    return session.is_marked.filter(pk=question.pk).exists()

def is_question_complete(question):
    return question.get_latest_revision().statuses.filter(code_name="COMPLETE").exists()

def test_revision_approval(revision, submitter):
    return teams.utils.is_editor(submitter) and \
           revision.statuses.filter(code_name='COMPLETE').exists() and \
           revision.choice_set.count() >= 2
