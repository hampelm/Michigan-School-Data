from django.conf import settings
from django.conf.urls.defaults import *

from core.views import *

urlpatterns = patterns('',   
    url(r'^json', search_json),
    url(r'^search/json', search_json),
    url(r'^$', search),
    url(r'^search', search),
    
)

if settings.LOCAL_DEVELOPMENT:
    urlpatterns += patterns("django.views",
        url(r"^assets/(?P<path>.*)$", 'static.serve', {
            "document_root": settings.MEDIA_ROOT,})
    )
