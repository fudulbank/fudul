from django.conf.urls import include, url
from django.contrib import admin

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^accounts/', include('accounts.urls')),
    url(r'^institutions/', include('blocks.urls', namespace="blocks")),
    url(r'', include('core.urls')),
]
