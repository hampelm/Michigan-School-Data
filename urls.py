from django.conf import settings
from django.conf.urls.defaults import *

from core.views import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',

    url('^$', home),
    
    url(r'^building/(?P<building_code>[-\w]+)/$', building, name="building"),
    url(r'^district/(?P<district_code>[-\w]+)/$', district, name="district"),
    
    url(r'^search/json', search_json),
    url(r'^search', search),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)

if settings.LOCAL_DEVELOPMENT:
    urlpatterns += patterns("django.views",
        url(r"^assets/(?P<path>.*)$", 'static.serve', {
            "document_root": settings.MEDIA_ROOT,})
    )
