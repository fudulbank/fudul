from django.core.management.base import BaseCommand
from django.db.models import Count
from exams.models import Exam, Revision, Rule, SuggestedChange
from exams.forms import RevisionForm 
import datetime
import re


class Command(BaseCommand):
    help = "Clean-up tasks for the exam app"
    def add_arguments(self, parser):
        parser.add_argument('--verbose', action='store_true',
                            default=False)
        parser.add_argument('--dry', action='store_true',
                            default=False)

    def handle(self, *args, **options):
        rules = list(Rule.objects.filter(is_disabled=False))

        # Providing initial compiled regexes speeds things up.
        compiled_rules = {}
        for rule in rules:
            compiled_rules[rule.pk] = re.compile(rule.regex_pattern)

        # Clean up suggested edits that are no longer related to best revision
        obsolete_suggestions =  SuggestedChange.objects.exclude(revision__is_last=True,
                                                                revision__is_deleted=False)\
                                                       .filter(status="PENDING")\

        if options['verbose']:
            print("Found {} obsolute suggestions.  Deleting...".format(obsolete_suggestions.count()))
        obsolete_suggestions.delete()

        for exam in Exam.objects.order_by('pk'):
            if options['verbose']:
                print("Scanning {}...".format(exam.name))
            pool = list(Revision.objects.select_related('question')\
                                        .filter(question__exam=exam,
                                                is_last=True,
                                                is_deleted=False)\
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
                        print("We found {} rules for Q#{}".format(len(applied_rules), revision.question.pk))
