from django.conf.urls import include, url
from django.contrib import admin
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^institutions/', include('exams.urls', namespace="exams")),
    url(r'', include('core.urls')),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
