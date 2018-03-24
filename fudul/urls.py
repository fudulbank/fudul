from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from django.views.decorators.cache import cache_page
from django_js_reverse.views import urls_js
from rest_framework import routers

from exams.admin import editor_site
from exams.api import *


router = routers.DefaultRouter()
router.register(r'answers', AnswerViewSet, base_name="answer")
router.register(r'highlights', HighlightViewSet, base_name="highlight")
router.register(r'marked', MarkedQuestionViewSet, base_name="marked")
router.register(r'question_summary', QuestionSummaryViewSet, base_name="summary")
router.register(r'question_assignment', QuestionAssignmentViewSet, base_name="assigned")
router.register(r'suggestions', SuggestedChangeViewSet, base_name="suggestion")
router.register(r'duplicates', DuplicateContainerViewSet, base_name="duplicate")

urlpatterns = [
    url(r'^api/activities/$', ActivityList.as_view(), name="activity-list"),
    url(r'^api/corrections/$', CorrectionList.as_view(), name="correction-list"),
    url(r'^api/', include(router.urls)),
    url(r'^admin/', include('loginas.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^silk/', include('silk.urls', namespace='silk')),
    url(r'^api-auth/', include('rest_framework.urls')),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^mailer/', include('mailer.urls', namespace="mailer")),
    url(r'^exams/admin/', include(editor_site.urls)),
    url(r'^exams/', include('exams.urls', namespace="exams")),
    url(r'', include('core.urls')),
    url(r'^ckeditor/', include('ckeditor_uploader.urls')),
    url(r'^notifications/', include('notifications.urls', namespace='notifications')),
    url(r'^jsreverse/$', cache_page(60 * 60 * 24 * 7)(urls_js), name='js_reverse'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
