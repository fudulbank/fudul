from django.core.management.base import BaseCommand
from django.db.models import Count
from exams.forms import RevisionForm 
from exams.models import *
import datetime
import re
import time

class Command(BaseCommand):
    help = "Clean-up tasks for the exam app"
    def add_arguments(self, parser):
        parser.add_argument('--verbose', action='store_true',
                            default=False)
        parser.add_argument('--dry', action='store_true',
                            default=False)
        parser.add_argument('--fast', action='store_true',
                            default=False)
        parser.add_argument('--exam-pk', default=None, type=int)

    def handle(self, *args, **options):
        if not options['fast']:
            question_count = Question.objects.undeleted().count()
            # Run over 10 hours
            total_seconds = 60 * 60 * 10
            sleep_time = question_count / total_seconds
        rules = list(Rule.objects.filter(is_disabled=False))

        # Providing initial compiled regexes speeds things up.
        compiled_rules = {}
        for rule in rules:
            compiled_rules[rule.pk] = re.compile(rule.regex_pattern)

        # Clean up suggested edits that are no longer related to best revision
        without_rules = SuggestedChange.objects.annotate(rule_count=Count('rules'))\
                                               .filter(status="PENDING", rule_count=0)
        with_deleted_questions = SuggestedChange.objects.exclude(revision__is_last=True,
                                                                 revision__is_deleted=False)\
                                                        .filter(status="PENDING")

        if options['verbose']:
            print("Found {} suggestions without rules and {} suggests with deleted questions.  Deleting...".format(without_rules.count(),
                                                                                                                   with_deleted_questions.count()))
        without_rules.delete()
        with_deleted_questions.delete()

        if options['exam_pk']:
            exams = Exam.objects.filter(pk=options['exam_pk'])
        else:
            exams = Exam.objects.order_by('pk')

        for exam in exams:
            if options['verbose']:
                print("Scanning {}...".format(exam.name))
            pool = list(Revision.objects.select_related('question')\
                                        .filter(question__exam=exam,
                                                is_last=True)\
                                        .undeleted()\
                                        .order_by('question__pk'))

            for revision in pool:
                applied_rules = []
                for rule in rules:
                    compiled_regex = compiled_rules[rule.pk]
                    if rule.scope in ['ALL', 'REVISIONS']:
                        match = re.search(compiled_regex,
                                          revision.text)
                        if match:
                            applied_rules.append(rule)
                    if rule.scope in ['ALL', 'CHOICES']:
                        for choice in revision.choice_set.all():
                            match = re.search(compiled_regex,
                                              choice.text)
                            if match:
                                applied_rules.append(rule)
                if applied_rules:
                    if not options['dry']:
                        declined_suggestions = SuggestedChange.objects.filter(revision=revision,
                                                                              status="DECLINED")
                        for rule in applied_rules:
                            declined_suggestions = declined_suggestions.filter(rules__pk=rule.pk)
                        if declined_suggestions.exists():
                            if options['verbose']:
                                print("Revision #{}: An identical previous container was declined. Skip this one.".format(revision.pk))
                            continue
                        suggestion, was_created = SuggestedChange.objects.get_or_create(status="PENDING", revision=revision)
                        suggestion.rules.add(*applied_rules)
                    if options['verbose']:
                        print("We found {} rules for Q#{} in {}".format(len(applied_rules), revision.question.pk, exam.name))
                if not options['fast']:
                    if options['verbose']:
                        print("Sleeping for {}...".format(sleep_time))
                    time.sleep(sleep_time)
