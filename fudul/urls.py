from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from exams.admin import editor_site
from exams.api import HighlightViewSet, AnswerViewSet
from rest_framework import routers

router = routers.DefaultRouter()
router.register(r'answers', AnswerViewSet, base_name="answer")
router.register(r'highlights', HighlightViewSet, base_name="highlight")

urlpatterns = [
    url(r'^api/', include(router.urls)),
    url(r'^admin/', include('loginas.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^api-auth/', include('rest_framework.urls')),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^mailer/', include('mailer.urls', namespace="mailer")),
    url(r'^exams/admin/', include(editor_site.urls)),
    url(r'^exams/', include('exams.urls', namespace="exams")),
    url(r'', include('core.urls')),
    url(r'^ckeditor/', include('ckeditor_uploader.urls')),
    url(r'^notifications/', include('notifications.urls', namespace='notifications')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
