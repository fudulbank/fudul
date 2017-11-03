from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
from exams.admin import editor_site

urlpatterns = [
    url(r'^admin/', include('loginas.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^mailer/', include('mailer.urls', namespace="mailer")),
    url(r'^exams/admin/', include(editor_site.urls)),
    url(r'^exams/', include('exams.urls', namespace="exams")),
    url(r'', include('core.urls')),
    url(r'^ckeditor/', include('ckeditor_uploader.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
