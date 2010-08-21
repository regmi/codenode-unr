#########################################################################
# Copyright (C) 2007, 2008, 2009
# Alex Clemesha <alex@clemesha.org> & Dorian Raymer <deldotdr@gmail.com>
#
# This module is part of codenode, and is distributed under the terms
# of the BSD License:  http://www.opensource.org/licenses/bsd-license.php
#########################################################################

from django.conf.urls.defaults import *
from django.conf import settings

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns("",
    (r'^$', 'django.views.generic.simple.redirect_to', {'url': 'femhub'}),
    (r'^femhub/', include('codenode.frontend.femhub.urls')),
    (r'^admin/(.*)', admin.site.root),
    # XXX: 'notebook is a part of the old API, will be removed soon
    (r'^notebook/', include('codenode.frontend.notebook.urls')),
)

if settings.DEBUG:
    def get_static_path():
        import os
        return os.path.join(settings.PROJECT_PATH, 'static')

    urlpatterns += patterns('',
        (r'^static/(.*)', 'django.views.static.serve', {'document_root': get_static_path()}),
)

