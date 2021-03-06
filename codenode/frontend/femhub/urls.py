
from django.conf.urls.defaults import *

from codenode.external.jsonrpc import jsonrpc_site
from codenode.frontend.femhub.views import femhub

urlpatterns = patterns('',
    url(r'^$', femhub, name='femhub'),
    url(r'^json/$', jsonrpc_site.dispatch, name='jsonrpc_mountpoint'),
    url(r'^json/browse/$', 'codenode.external.jsonrpc.views.browse', name='jsonrpc_browser'),
)

