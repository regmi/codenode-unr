
from django.shortcuts import render_to_response
from django.contrib.auth.decorators import login_required

from codenode.external.jsonrpc import jsonrpc_method

import codenode.frontend.bookshelf.models as _bookshelf
import codenode.frontend.notebook.models as _notebook
import codenode.frontend.backend.models as _backend

from codenode.frontend.backend.rpc import allocateEngine

def jsonrpc_auth_method(method, safe=False, validate=False):
    """Convenience function for authenticated Json RPC requests. """
    return jsonrpc_method(method, authenticated=True, safe=safe, validate=validate)

@login_required
def femhub(request):
    return render_to_response('femhub/femhub.html')

@jsonrpc_auth_method('RPC.hello')
def rpc_hello(request):
    return "Hello, %s!" % request.user.username

@jsonrpc_auth_method('RPC.getEngines')
def rpc_getEngines(request):
    engines = _backend.EngineType.objects.all()
    return [ { 'id': engine.id, 'name': engine.name } for engine in engines ]

@jsonrpc_auth_method('RPC.getFolders')
def rpc_getFolders(request):
    folders = _bookshelf.Folder.objects.filter(owner=request.user)
    return [ { 'guid': folder.guid, 'title': folder.title } for folder in folders ]

@jsonrpc_auth_method('RPC.getNotebooks')
def rpc_getNotebooks(request):
    pass

@jsonrpc_auth_method('RPC.newNotebook')
def rpc_newNotebook(request, engine_id):
    notebook = _notebook.Notebook(owner=request.user)
    notebook.save()

    engine = _backend.EngineType.objects.get(id=engine_id)
    access = allocateEngine(engine.backend.address, engine.name)

    backend = _backend.NotebookBackendRecord(notebook=notebook, engine_type=engine, access_id=access)
    backend.save()

    return { 'id': notebook.guid }

