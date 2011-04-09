from django.conf import settings
from django.conf.urls.defaults import *

from core.views import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',    
    url(r'^json', search_json),
    url(r'^', search),
)

if settings.LOCAL_DEVELOPMENT:
    urlpatterns += patterns("django.views",
        url(r"^assets/(?P<path>.*)$", 'static.serve', {
            "document_root": settings.MEDIA_ROOT,})
    )
