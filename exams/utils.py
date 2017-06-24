def is_question_complete(question):
    return question.get_latest_revision().statuses.filter(code_name="COMPLETE").exists()
