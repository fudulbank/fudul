from dal import autocomplete
from django import forms
from django.contrib.auth.models import User
from django.core.validators import MaxValueValidator, MinValueValidator
from django.forms.models import modelformset_factory, inlineformset_factory
from django.utils.safestring import mark_safe
import random
import string

from . import models, utils
import teams.utils
import accounts.utils

class MetaChoiceField(forms.ModelMultipleChoiceField):
    def __init__(self, *args, **kwargs):
        self.exam = kwargs.pop('exam')
        self.form_type = kwargs.pop('form_type')
        super().__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        approved_only = self.form_type == 'session'
        count = utils.get_exam_question_count_per_meta(self.exam,
                                                       meta=obj,
                                                       approved_only=approved_only)
        if type(obj) is models.Difficulty:
            return mark_safe(f"<abbr title='{obj.tooltip}'>{str(obj)} ({count})</abbr>")
        else:
            return f"{str(obj)} ({count})"

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
        super().__init__(*args, **kwargs)
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

class GenericRevisionForm(forms.ModelForm):
    def clone(self, question, user, figure_formset=None, choice_formset=None):
        # We induce save at this stage to pop up the new_objects,
        # changed_objects and deleted_objects attributed.  The actual
        # saving is done in figure_formset.clone().
        if figure_formset:
            figure_formset.save(commit=False)
            formset_changed = figure_formset.new_objects or \
                              figure_formset.changed_objects or \
                              figure_formset.deleted_objects
        else:
            formset_changed = False

        # In case of handling Revisions, we will also choice the
        # formset for choices for any potential changes.
        if not formset_changed and \
           type(self.instance) is models.Revision and \
           choice_formset:
            choice_formset.save(commit=False)
            formset_changed = choice_formset.new_objects or \
                              choice_formset.changed_objects or \
                              choice_formset.deleted_objects

        # If nothing has changed, don't create a new instance.
        if self.instance.pk and \
           not self.changed_data and \
           not formset_changed:
            return

        new_object = self.save(commit=False)
        if not new_object:
            return
        new_object.pk = None
        if not self.instance.pk:
            new_object.is_first = True
        else:
            new_object.is_first = False
        new_object.is_last = True
        new_object.is_contribution = not teams.utils.is_editor(user)
        new_object.submitter = user
        # We pass question as this 'clone' method might also be used
        # to create new explanation.
        new_object.question = question
        new_object.save()

        if figure_formset:
            figure_formset.clone(new_object)

        if type(new_object) is models.Revision:
            if choice_formset:
                choice_formset.clone(new_object)
            new_object.is_approved = utils.test_revision_approval(new_object)
            new_object.save()

        return new_object

class RevisionForm(GenericRevisionForm):
    def clean_text(self):
        """Remove illegal characters that are not allowed in the database."""
        text = self.cleaned_data['text']
        if text:
            text = text.replace('\u0000', '')
        return text

    class Meta:
        model = models.Revision
        fields = ['text', 'figure', 'change_summary']

class ChoiceForm(forms.ModelForm):
    def clean_text(self):
        """Remove illegal characters that are not allowed in the database."""
        text = self.cleaned_data['text']
        if text:
            text = text.replace('\u0000', '')
        return text

    class Meta:
        model = models.Choice
        fields = ['text', 'is_right']

class FigureForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['caption'].widget.attrs = {'rows': '1'}

    class Meta:
        model = models.Figure
        fields = '__all__'

class FigureFormSet(forms.BaseModelFormSet):
    def clone(self, revision):
        # How we handle figures?
        # 1) Clear all previous figures
        # 2) Remove all changed figures (to be cloned in #4)
        # 3) Add all new figures
        # 4) Clone all changed figures

        self.save(commit=False)
        # 1) Clear all previous figures
        revision.figures.clear()

        # 2) Remove all changed and deleted figures (to be cloned in #4)
        figures = list(self.queryset)
        for figure in [figure for figure, changed_fields in self.changed_objects] + self.deleted_objects:
            figures.remove(figure)

        # 3) Add all new figures
        for figure in self.new_objects:
            figure.save()
            figures.append(figure)

        # 4) Clone all changed figures
        for figure, changed_fields in self.changed_objects:
            figure.pk = None
            figure.save()
            figures.append(figure)

        revision.figures.add(*figures)

class ChoiceFormset(forms.BaseModelFormSet):
    def clone(self, revision):
        # How we handle choices?
        # 1) Clear all previous choices
        # 2) Remove all changed choices (to be cloned in #4)
        # 3) Add all new choices
        # 4) Clone all changed choices

        self.save(commit=False)
        # 1) Clear all previous choices
        revision.choices.clear()

        # 2) Remove all changed and deleted choices (to be cloned in #4)
        choices = list(self.queryset)
        for choice in [choice for choice, changed_fields in self.changed_objects] + self.deleted_objects:
            choices.remove(choice)

        # 3) Add all new choices
        for choice in self.new_objects:
            choice.question = revision.question
            choice.save()
            choices.append(choice)

        # 4) Clone all changed choices
        for choice, changed_fields in self.changed_objects:
            choice.pk = None
            choice.save()
            choices.append(choice)

        revision.choices.add(*choices)

RevisionChoiceFormset = modelformset_factory(models.Choice,
                                             formset=ChoiceFormset,
                                             form=ChoiceForm,
                                             extra=4, can_delete=True,
                                             fields=['text','is_right'])
ContributedRevisionChoiceFormset = modelformset_factory(models.Choice,
                                                        formset=ChoiceFormset,
                                                        form=ChoiceForm,
                                                        can_delete=True,
                                                        extra=0,
                                                        fields=['text','is_right'])
RevisionFigureFormset = modelformset_factory(models.Figure, extra=1,
                                             can_delete=True,
                                             formset=FigureFormSet,
                                             form=FigureForm)
ExplanationFigureFormset = modelformset_factory(models.Figure,
                                                can_delete=True,
                                                extra=1,
                                                formset=FigureFormSet,
                                                form=FigureForm)

class SessionForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.exam = kwargs.pop('exam')
        self.user = kwargs.pop('user')
        self.original_session = kwargs.pop('original_session', None)
        self.is_automatic = kwargs.pop('is_automatic', False)
        super().__init__(*args, **kwargs)

        self.fields['session_mode'].widget = forms.RadioSelect(choices=models.session_mode_choices[:-1])

        common_pool = self.exam.question_set.select_related('parent_question',
                                                            'child_question')

        # We can base the session on a previous session
        if self.original_session:
            session_question_pks = self.original_session.answer_set.values('question').distinct()
            incorrect_question_pks = session_question_pks.filter(choice__is_right=False)
            skipped_question_pks = session_question_pks.filter(choice__isnull=True)
            self.question_pools = {'ALL': self.original_session.get_questions(),
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
                                         .distinct()\
                                         .order_by('name')
        if subjects.exists():
            self.fields['all_subjects'] = forms.BooleanField(label="All", required=False)
            self.fields['subjects'] = MetaChoiceField(exam=self.exam,
                                                      required=False,
                                                      form_type='session',
                                                      queryset=subjects,
                                                      widget=forms.CheckboxSelectMultiple)
        else:
            del self.fields['subjects']

        sources = self.exam.get_sources().filter(parent_source__isnull=True)\
                                         .with_approved_questions(self.exam)\
                                         .distinct()\
                                         .order_by('name')
        if sources.exists():
            self.fields['all_sources'] = forms.BooleanField(label="All", required=False)
            self.fields['sources'] = MetaChoiceField(exam=self.exam,
                                                     required=False,
                                                     form_type='session',
                                                     queryset=sources,
                                                     widget=forms.CheckboxSelectMultiple)
        else:
            del self.fields['sources']

        exam_types = self.exam.exam_types.with_approved_questions(self.exam)\
                                         .distinct()
        if exam_types.exists():
            self.fields['all_exam_types'] = forms.BooleanField(label="All", required=False)
            self.fields['exam_types'] = MetaChoiceField(required=not self.is_automatic,
                                                        form_type='session',
                                                        exam=self.exam,
                                                        queryset=exam_types,
                                                        widget=forms.CheckboxSelectMultiple)
        else:
            del self.fields['exam_types']

        difficulties = models.Difficulty.objects.with_approved_questions()\
                                                .distinct()\
                                                .order_by('-upper_limit')
        if difficulties.exists():
            self.fields['all_difficulties'] = forms.BooleanField(label="All", required=False)
            self.fields['difficulties'] = MetaChoiceField(required=not self.is_automatic,
                                                          form_type='session',
                                                          exam=self.exam,
                                                          queryset=difficulties,
                                                          widget=forms.CheckboxSelectMultiple)
        else:
            del self.fields['difficulties']

        if self.is_automatic:
            self.fields['number_of_questions'].required = False

    def get_question_pool(self, cleaned_data=None):
        cleaned_data = cleaned_data or self.cleaned_data

        question_filter = cleaned_data.get('question_filter', 'ALL')
        question_pool = self.question_pools[question_filter]

        # If 'all_*' is selected, no need to save the m2m relationships.

        subjects = cleaned_data.get('subjects')
        if cleaned_data.get('all_subjects') and subjects:
            del cleaned_data['subjects']
        elif subjects:
            question_pool = question_pool.filter(subjects__in=subjects)

        sources = cleaned_data.get('sources')
        if cleaned_data.get('all_sources') and sources:
            del cleaned_data['sources']
        elif sources:
            question_pool = question_pool.filter(sources__in=sources)

        exam_types = cleaned_data.get('exam_types')
        if cleaned_data.get('all_exam_types') and exam_types:
            del cleaned_data['exam_types']
        elif exam_types:
            question_pool = question_pool.filter(exam_types__in=exam_types)

        difficulties = cleaned_data.get('difficulties')
        if cleaned_data.get('all_difficulties') and difficulties:
            del cleaned_data['difficulties']
        elif difficulties:
            question_pool = question_pool.filter(difficulty__in=difficulties)

        return question_pool

    def clean(self):
        cleaned_data = super().clean()

        # If the form is invalid to start with, skip question
        # checking.

        if not 'question_filter' in cleaned_data:
            return cleaned_data

        number_of_questions = cleaned_data.get('number_of_questions')
        question_filter = cleaned_data['question_filter']
        question_pool = self.get_question_pool(cleaned_data)

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

            self.final_questions = list(self.questions_with_tree)
            remaining_count = number_of_questions - self.questions_with_tree.count()
            if remaining_count > 0:
                orphan_questions = selected_pool.filter(parent_question__isnull=True,
                                                        child_question__isnull=True)
                self.orphan_pool = models.Question.objects.filter(pk__in=orphan_questions[:remaining_count])
                self.final_questions += list(self.orphan_pool)
        else:
            self.final_questions = question_pool

        return cleaned_data

    def save(self, *args, **kwargs):
        session = super().save(*args, **kwargs)
        session.questions.add(*self.final_questions)

        if not session.parent_session:
            chars = string.ascii_lowercase + string.digits
            secret_key = "".join([random.choice(chars) for i in range(10)])
            session.secret_key = secret_key

        # Here we try to account for cases when the requested number
        # of questions is not completely available.
        actual_question_count = len(self.final_questions)

        if self.is_automatic:
            session.is_automatic = True
            session.number_of_questions = actual_question_count

        # Initially, the value of unused_question_count equals the
        # number of questions in the sessions.
        session.unused_question_count = actual_question_count

        if self.original_session:
            session.examinee_name = self.original_session.examinee_name
            session.description = self.original_session.description

        session.save()
        return session

    class Meta:
        model = models.Session
        fields = ['session_mode', 'number_of_questions', 'exam_types',
                  'sources', 'subjects', 'question_filter',
                  'difficulties']


class ExplanationForm(GenericRevisionForm):
    def __init__(self, *args, **kwargs):
        self.is_optional = kwargs.pop('is_optional', False)
        super().__init__(*args, **kwargs)
        if self.is_optional:
            self.fields['explanation_text'].required = False

    def clean_explanation_text(self):
        """Remove illegal characters that are not allowed in the database."""
        text = self.cleaned_data['explanation_text']
        if text:
            text = text.replace('\u0000', '')
        return text

    def save(self,  commit=True):
        if self.is_optional and \
           (not 'explanation_text' in self.cleaned_data or \
            'explanation_text' in self.cleaned_data and \
            not self.cleaned_data['explanation_text']):
            return
        return super().save(commit=commit)

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
        super().__init__(*args, **kwargs)
        self.fields['editor'].queryset = exam.get_editors()
