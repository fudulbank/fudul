from dal import autocomplete
from django import forms
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.forms.models import inlineformset_factory
import itertools
import random
import string

from . import models, utils
import teams.utils
import accounts.utils

class MetaChoiceField(forms.ModelMultipleChoiceField):
    def __init__(self, *args, **kwargs):
        self.exam = kwargs.pop('exam')
        self.form_type = kwargs.pop('form_type')
        super(MetaChoiceField, self).__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        approved_only = self.form_type == 'session'
        count = utils.get_exam_question_count_per_meta(self.exam,
                                                       meta=obj,
                                                       approved_only=approved_only)

        return "{} ({})".format(str(obj), count)

class StatusChoiceField(forms.ModelMultipleChoiceField):
    def label_from_instance(self, obj):
        if obj.is_blocker:
            blocker_str = "blocker"
            css_class = "text-danger"
        else:
            blocker_str = "nonblocker"
            css_class = "text-success"
        return "{} <strong class='{}'>({})</strong>".format(obj.name, css_class, blocker_str)

class UserChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return accounts.utils.get_user_credit(obj, full=True)
    
# shared widgets for exam_types, sources and subjects in QuestionForm and SessionForm
select2_widget = autocomplete.ModelSelect2Multiple(attrs={'data-width': '100%'})

class QuestionForm(forms.ModelForm):
    issues = StatusChoiceField(widget=autocomplete.ModelSelect2Multiple(attrs={'data-width': '100%', 'data-html': 'true'}),
                               queryset=models.Issue.objects.all(),
                               required=False)

    def __init__(self, *args, **kwargs):
        super(QuestionForm, self).__init__(*args, **kwargs)
        exam = self.instance.exam

        # Only include 'subjects' field if the exam has subjects
        subjects = models.Subject.objects.filter(exam=exam)
        if subjects.exists():
            self.fields['subjects'] = MetaChoiceField(required=True,
                                                      form_type='question',
                                                      exam=exam,
                                                      queryset=subjects,
                                                      widget=select2_widget)
        else:
            del self.fields['subjects']

        sources = exam.get_sources()
        if sources.exists():
            self.fields['sources'] = MetaChoiceField(required=True,
                                                     form_type='question',
                                                     exam=exam,
                                                     queryset=sources,
                                                     widget=select2_widget)
        else:
            del self.fields['sources']

        if exam.exam_types.exists():
            self.fields['exam_types'] = MetaChoiceField(required=True,
                                                        form_type='question',
                                                        exam=exam,
                                                        queryset=exam.exam_types.all(),
                                                        widget=select2_widget)
        else:
            del self.fields['exam_types']

    class Meta:
        model = models.Question
        fields = ['sources', 'subjects', 'exam_types',
                  'parent_question', 'issues']
        widgets = {
            'parent_question': autocomplete.ModelSelect2(url='exams:autocomplete_questions',
                                                         forward=['exam_pk'],
                                                         attrs={'data-html': True,
                                                                'data-width': '100%'}),
        }

class RevisionForm(forms.ModelForm):
    def clone(self, question, user):
        new_revision = self.save(commit=False)

        # Setting primary key to None creates a new object, rather
        # than modifying the pre-existing one
        new_revision.pk = None
        new_revision.submitter = user
        new_revision.is_first = False
        new_revision.is_last = True
        new_revision.is_contribution = not teams.utils.is_editor(user)
        new_revision.save()
        self.save_m2m()

        # Mark the last revision as such
        question.update_latest()
        question.update_best_revision()
        question.save()

        return new_revision

    class Meta:
        model = models.Revision
        fields = ['text', 'figure', 'change_summary']

class ChoiceForms(forms.ModelForm):
    class Meta:
        model = models.Choice
        fields = ['text','revision','is_right']

class CustomRevisionChoiceFormset(forms.BaseInlineFormSet):
    def clone(self, revision):
        # Let's clone choices!
        modified_choices = self.save(commit=False)
        unmodified_choices = []
        for choice in self.queryset:
            if not choice in self.deleted_objects and \
               not choice in modified_choices:
                unmodified_choices.append(choice)
        choices = modified_choices + unmodified_choices
        for choice in choices:
            choice.pk = None
            choice.revision = revision
            choice.save()

RevisionChoiceFormset = inlineformset_factory(models.Revision,
                                              models.Choice,
                                              formset=CustomRevisionChoiceFormset,
                                              extra=4,
                                              fields=['text','is_right'])


ContributedRevisionChoiceFormset = inlineformset_factory(models.Revision,
                                              models.Choice,
                                              formset=CustomRevisionChoiceFormset,
                                              extra=0,
                                              fields=['text','is_right'])

class SessionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.exam = kwargs.pop('exam')
        self.user = kwargs.pop('user')
        original_session = kwargs.pop('original_session', None)
        self.is_automatic = kwargs.pop('is_automatic', False)
        super(SessionForm, self).__init__(*args, **kwargs)

        self.fields['session_mode'].widget = forms.RadioSelect(choices=models.session_mode_choices[:-1])

        common_pool = self.exam.question_set.select_related('parent_question',
                                                            'child_question')

        # We can base the session on a previous session
        if original_session:
            session_question_pks = original_session.answer_set.values('question').distinct()
            incorrect_question_pks = session_question_pks.filter(choice__is_right=False)
            skipped_question_pks = session_question_pks.filter(choice__isnull=True)
            self.question_pools = {'ALL': original_session.get_questions(),
                                   'INCORRECT': models.Question.objects.filter(pk__in=incorrect_question_pks),
                                   'SKIPPED': models.Question.objects.filter(pk__in=skipped_question_pks),
            }
        else:
            self.question_pools = {'ALL': common_pool.approved(),
                                   'UNUSED': common_pool.approved().unused_by_user(self.user, exclude_skipped=False),
                                   'INCORRECT': common_pool.approved().incorrect_by_user(self.user),
                                   'SKIPPED': common_pool.approved().skipped_by_user(self.user),
                                   'MARKED': common_pool.approved().filter(marking_users=self.user),
                                   'INCOMPLETE': common_pool.incomplete()
            }

        # The following verbose calculations are only needed for
        # manually-created sessions.
        if not self.is_automatic:
            filter_choices = []
            for code_name, human_name in models.questions_choices:
                question_pool = self.question_pools[code_name]
                count = question_pool.count()
                choice = (code_name, "{} ({})".format(human_name, count))
                filter_choices.append(choice)
            self.fields['question_filter'].widget = forms.RadioSelect(choices=filter_choices)

            # Limit number of questions
            total_questions = self.exam.question_set.approved().count()
            self.fields['number_of_questions'].widget.attrs['max'] = total_questions

            self.fields['number_of_questions'].validators.append(MinValueValidator(1))
            self.fields['number_of_questions'].widget.attrs['min'] = 1
            # This widget should be big enough to contain 5 digits.
            self.fields['number_of_questions'].widget.attrs['style'] = 'width: 5em;'
            self.fields['number_of_questions'].widget.attrs['placeholder'] = ''

        # Limit subjects and exams per exam
        subjects = models.Subject.objects.filter(exam=self.exam)\
                                         .with_approved_questions()\
                                         .distinct()
        if subjects.exists():
            self.fields['subjects'] = MetaChoiceField(exam=self.exam,
                                                      required=False,
                                                      form_type='session',
                                                      queryset=subjects,
                                                      widget=select2_widget)
        else:
            del self.fields['subjects']

        sources = self.exam.get_sources().filter(parent_source__isnull=True)\
                                         .with_approved_questions(self.exam)\
                                         .distinct()
        if sources.exists():
            self.fields['sources'] = MetaChoiceField(exam=self.exam,
                                                     required=False,
                                                     form_type='session',
                                                     queryset=sources,
                                                     widget=select2_widget)
        else:
            del self.fields['sources']

        exam_types = self.exam.exam_types.with_approved_questions(self.exam)\
                                         .distinct()
        if exam_types.exists():
            self.fields['exam_types'] = MetaChoiceField(required=not self.is_automatic,
                                                        form_type='session',
                                                        exam=self.exam,
                                                        queryset=exam_types,
                                                        widget=select2_widget)
        else:
            del self.fields['exam_types']

        if self.is_automatic:
            self.fields['number_of_questions'].required = False
            
    def clean(self):
        cleaned_data = super(SessionForm, self).clean()

        # If the form is invalid to start with, skip question
        # checking.

        if not 'question_filter' in cleaned_data:
            return cleaned_data

        number_of_questions = cleaned_data.get('number_of_questions')
        question_filter = cleaned_data['question_filter']
        question_pool = self.question_pools[question_filter]

        subjects = cleaned_data.get('subjects')
        if subjects:
            question_pool = question_pool.filter(subjects__in=subjects)

        sources = cleaned_data.get('sources')
        if sources:
            question_pool = question_pool.filter(sources__in=sources)

        exam_types = cleaned_data.get('exam_types')
        if exam_types:
            question_pool = question_pool.filter(exam_types__in=exam_types)

        if not question_pool.exists():
            raise forms.ValidationError("No questions at all match your selection.  Please try other options.")

        # In automatic session creation, we sometimes do not need to
        # specify a given number of questions

        if number_of_questions:
            # Ideally, randomization should be a database thing, but
            # Django is buggy when it comes to slicing a randomzied query
            # with many filters.  For this reason, we apply the filers,
            # then get only the PKs of included quessions, shuffle them,
            # and then slice the number we need.  Finally, we get the
            # question objects per the shuffled PKs.
            pool_pks = list(question_pool.values_list('pk', flat=True))
            random.shuffle(pool_pks)
            sliced_pks = pool_pks[:number_of_questions]

            selected_pool = models.Question.objects.filter(pk__in=sliced_pks)
            questions_to_find_tree = selected_pool.filter(parent_question__isnull=False) | \
                                     selected_pool.filter(child_question__isnull=False)

            pks = []
            for question in questions_to_find_tree.distinct():
                tree = question.get_tree()
                new_pks = [q.pk for q in tree if not q.pk in pks]
                pks += new_pks
            self.questions_with_tree = models.Question.objects\
                                                      .filter(pk__in=pks)

            if question_filter != 'INCOMPLETE':
                self.questions_with_tree = self.questions_with_tree.approved()

            remaining_count = number_of_questions - self.questions_with_tree.count()
            orphan_questions = selected_pool.filter(parent_question__isnull=True,
                                                    child_question__isnull=True)
            self.orphan_pool = models.Question.objects.filter(pk__in=orphan_questions[:remaining_count])

            self.final_questions = itertools.chain(self.orphan_pool, self.questions_with_tree)
        else:
            self.final_questions = question_pool

        return cleaned_data

    def save(self, *args, **kwargs):
        session = super(SessionForm, self).save(*args, **kwargs)
        session.questions.add(*self.final_questions)

        if not session.parent_session:
            chars = string.ascii_lowercase + string.digits
            secret_key = "".join([random.choice(chars) for i in range(10)])
            session.secret_key = secret_key

        if self.is_automatic:
            session.is_automatic = True
            session.number_of_questions = len(self.final_questions)

        session.save()
        return session

    class Meta:
        model = models.Session
        fields = ['session_mode', 'number_of_questions','exam_types',
                  'sources', 'subjects', 'question_filter']


class ExplanationForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.is_optional = kwargs.pop('is_optional', False)        
        super(ExplanationForm, self).__init__(*args, **kwargs)
        if self.is_optional:
            self.fields['explanation_text'].required = False

    def save(self,  commit=True):
        if self.is_optional and \
           (not 'explanation_text' in self.cleaned_data or \
            'explanation_text' in self.cleaned_data and \
            not self.cleaned_data['explanation_text']):
            return
        return super(ExplanationForm, self).save(commit=commit)

    def clone(self, question, user):
        # If nothing has changed, don't create a new instance.
        if self.instance.pk and \
           not self.changed_data:
            return

        new_explanation = self.save(commit=False)
        if not new_explanation:
            return
        new_explanation.pk = None
        new_explanation.is_first = False
        new_explanation.is_last = True
        new_explanation.is_contribution = not teams.utils.is_editor(user)
        new_explanation.submitter = user
        new_explanation.question = question
        new_explanation.save()

        # Mark the last explanation as such
        question.update_latest()

        return new_explanation

    class Meta:
        model = models.ExplanationRevision
        fields = ['explanation_text', 'explanation_figure', 'reference']

class AnswerCorrectionForm(forms.ModelForm):
    class Meta:
        model = models.AnswerCorrection
        fields = ['justification']


class ContributeMnemonic(forms.ModelForm):
    class Meta:
        model = models.Mnemonic
        fields=['text','image']


class AssignQuestionForm(forms.Form):
    editor = UserChoiceField(widget=autocomplete.ModelSelect2(),
                             queryset=User.objects.none())

    def __init__(self, *args, **kwargs):
        exam = kwargs.pop('exam', None)        
        super(AssignQuestionForm, self).__init__(*args, **kwargs)
        self.fields['editor'].queryset = exam.get_editors()
