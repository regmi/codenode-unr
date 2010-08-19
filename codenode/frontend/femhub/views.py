
from django.shortcuts import render_to_response
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User

from codenode.external.jsonrpc import jsonrpc_method

import codenode.frontend.bookshelf.models as _bookshelf
import codenode.frontend.notebook.models as _notebook
import codenode.frontend.backend.models as _backend

from codenode.frontend.backend.rpc import allocateEngine

def jsonrpc_auth_method(method, safe=False, validate=False):
    """Convenience function for authenticated Json RPC requests. """
    return jsonrpc_method(method, authenticated=True, safe=safe, validate=validate)

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

@jsonrpc_method('RPC.Account.isAuthenticated')
def rpc_Account_isAuthenticated(request):
    """ """
    return { 'auth': request.user.is_authenticated() }

@jsonrpc_method('RPC.Account.login')
def rpc_Account_login(request, username, password, remember):
    """Login to the system. """
    user = authenticate(username=username, password=password)

    if user is not None:
        if user.is_active:
            if not remember:
                request.session.set_expiry(0)
            login(request, user)
            return { 'ok': True }
        else:
            return { 'ok': False, 'reason': 'disabled' }
    else:
        return { 'ok': False, 'reason': 'failed' }

@jsonrpc_method('RPC.Account.logout')
def rpc_Account_logout(request):
    """Logout from the system. """
    logout(request)

@jsonrpc_method('RPC.Account.createAccount')
def rpc_Account_createAccount(request, username, email, password):
    """Create new user account ."""
    try:
        User.objects.get(username=username)
        return { 'ok': False, 'reason': 'exists' }
    except User.DoesNotExist:
        pass

    User.objects.create_user(username, email, password)
    return { 'ok': True }

@jsonrpc_method('RPC.Account.remindPassword')
def rpc_Account_remindPassword(request, username):
    """Create new random password and send it to the user. """
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return { 'ok': False, 'reason': 'does-not-exist' }

    password = User.objects.make_random_password()

    user.set_password(password)
    user.save()

    head = "[FEMhub Online Lab] Password Reminder Notification"
    body = """\
Dear %(username)s,

we received reqest to replace your old password with new,
auto-generated one. Your new password is:

%(password)s

The above password was E-mailed to you in clear text, so it
is suggested that you change it after first login with new
password.
""" % {'username': username, 'password': password}

    user.email_user(head, body)

    return { 'ok': True }

