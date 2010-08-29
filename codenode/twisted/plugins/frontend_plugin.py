import os

os.environ['DJANGO_SETTINGS_MODULE'] = 'frontend.settings'
from codenode import service

frontend = service.FrontendServiceMaker()

