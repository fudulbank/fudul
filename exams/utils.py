def is_question_complete(question):
    return question.statuses.filter(code_name="COMPLETE").exists()
