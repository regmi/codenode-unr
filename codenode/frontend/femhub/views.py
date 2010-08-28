
from django.shortcuts import render_to_response
from django.contrib.auth import authenticate, login, logout
from django.template import loader, Context, TemplateDoesNotExist
from django.contrib.auth.models import User
from django.utils import simplejson as json
from django.conf import settings

from codenode.external.jsonrpc import jsonrpc_method

from codenode.frontend.bookshelf.models import Folder
from codenode.frontend.notebook.models import Notebook, Cell
from codenode.frontend.backend.models import EngineType

import codenode.frontend.bookshelf.models as _bookshelf
import codenode.frontend.notebook.models as _notebook
import codenode.frontend.backend.models as _backend

from codenode.frontend.backend.rpc import allocateEngine

def jsonrpc_auth_method(method, safe=False, validate=False):
    """Convenience function for authenticated Json RPC requests. """
    return jsonrpc_method(method, authenticated=True, safe=safe, validate=validate)

def femhub(request):
    """Render the main page of Online Lab. """
    if settings.DEBUG:
        debug = '-debug'
    else:
        debug = ''

    return render_to_response('femhub/femhub.html', {'debug': debug})

@jsonrpc_method('RPC.hello')
def rpc_hello(request):
    return "Hello from FEMhub Online Lab"

@jsonrpc_auth_method('RPC.Template.render')
def rpc_Template_render(request, template, context=None):
    """Render a template given the arguments. """
    try:
        template = loader.get_template(template)
    except TemplateDoesNotExist:
        return { 'ok': False, 'reason': 'does-not-exist' }

    rendered = template.render(Context(context or {}))

    return { 'ok': True, 'rendered': rendered }

@jsonrpc_auth_method('RPC.Backend.getEngines')
def rpc_Backend_getEngines(request):
    """Return a list of all available engines. """
    engines = []

    for engine in EngineType.objects.all():
        engines.append({
            'id': engine.id,
            'name': engine.name,
            'description': engine.description,
        })

    return { 'ok': True, 'engines': engines }

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

@jsonrpc_auth_method('RPC.Folders.addRoot')
def rpc_Folders_addRoot(request, title):
    """Add new root folder. """
    folder = Folder(owner=request.user, title=title)
    folder.save()
    return { 'ok': True, 'guid': folder.guid }

@jsonrpc_auth_method('RPC.Folders.getRoot')
def rpc_Folders_getRoot(request):
    """Get root folder. """
    try:
        folder = Folder.objects.get(owner=request.user, parent__isnull=True)
    except Folder.DoesNotExist:
        folder = Folder(owner=request.user, title="My folders")
        folder.save()

    return { 'ok': True, 'guid': folder.guid, 'title': folder.title }

@jsonrpc_auth_method('RPC.Folders.addFolder')
def rpc_Folders_addFolder(request, guid, title):
    """Add new folder with the given title to the parent. """
    try:
        parent = Folder.objects.get(guid=guid)
    except Folder.DoesNotExist:
        return { 'ok': False, 'reason': 'does-not-exist' }

    folder = Folder(owner=request.user, parent=parent, title=title)
    folder.save()

    return { 'ok': True, 'guid': folder.guid }

@jsonrpc_auth_method('RPC.Folders.getFolders')
def rpc_Folders_getFolders(request, guid):
    """Get a list of folders for the given parent's guid. """
    try:
        parent = Folder.objects.get(guid=guid)
    except Folder.DoesNotExist:
        return { 'ok': False, 'reason': 'does-not-exist' }

    folders = Folder.objects.filter(owner=request.user, parent=parent)

    return [ { 'ok': True, 'guid': folder.guid, 'title': folder.title } for folder in folders ]

@jsonrpc_auth_method('RPC.Folders.renameFolder')
def rpc_Folders_renameFolder(request, guid, title):
    """Set new title to the given folder. """
    try:
        folder = Folder.objects.get(owner=request.user, guid=guid)
    except Folder.DoesNotExist:
        return { 'ok': False, 'reason': 'does-not-exist' }

    folder.title = title
    folder.save()

    return { 'ok': True }

@jsonrpc_auth_method('RPC.Folders.deleteFolder')
def rpc_Folders_deleteFolder(request, guid):
    """Delete the given folder. """
    try:
        folder = Folder.objects.get(owner=request.user, guid=guid)
    except Folder.DoesNotExist:
        return { 'ok': False, 'reason': 'does-not-exist' }

    folder.delete()

    return { 'ok': True }

@jsonrpc_auth_method('RPC.Folders.moveFolder')
def rpc_Folders_moveFolder(request, parent_guid, folder_guid):
    """Move the given folder to a new location. """
    try:
        parent = Folder.objects.get(owner=request.user, guid=parent_guid)
    except Folder.DoesNotExist:
        return { 'ok': False, 'reason': 'does-not-exist' }

    try:
        folder = Folder.objects.get(owner=request.user, guid=folder_guid)
    except Folder.DoesNotExist:
        return { 'ok': False, 'reason': 'does-not-exist' }

    folder.parent = parent
    folder.save()

    return { 'ok': True }

@jsonrpc_auth_method('RPC.Notebooks.addNotebook')
def rpc_Notebooks_addNotebook(request, engine_guid, folder_guid, title='untitled'):
    """Add new notebook with the given title to the folder. """
    try:
        folder = Folder.objects.get(owner=request.user, guid=folder_guid)
    except Folder.DoesNotExist:
        return { 'ok': False, 'reason': 'does-not-exist' }

    notebook = Notebook(owner=request.user, folder=folder, title=title)
    notebook.save()

    ### XXX: this has to be improved
    engine = _backend.EngineType.objects.get(id=engine_guid)
    access = allocateEngine(engine.backend.address, engine.name)

    backend = _backend.NotebookBackendRecord(notebook=notebook, engine_type=engine, access_id=access)
    backend.save()
    ################################

    return { 'ok': True, 'guid': notebook.guid }

@jsonrpc_auth_method('RPC.Notebooks.renameNotebook')
def rpc_Notebooks_renameNotebook(request, guid, title):
    """Set new title to the given notebook. """
    try:
        notebook = Notebook.objects.get(owner=request.user, guid=guid)
    except Notebooks.DoesNotExist:
        return { 'ok': False, 'reason': 'does-not-exist' }

    notebook.title = title
    notebook.save()

    return { 'ok': True }

@jsonrpc_auth_method('RPC.Notebooks.deleteNotebook')
def rpc_Notebooks_deleteNotebook(request, guid):
    """Delete the given notebook. """
    try:
        notebook = Notebook.objects.get(owner=request.user, guid=guid)
    except Notebooks.DoesNotExist:
        return { 'ok': False, 'reason': 'does-not-exist' }

    notebook.delete()

    return { 'ok': True }

@jsonrpc_auth_method('RPC.Notebooks.getNotebooks')
def rpc_Notebooks_getNotebooks(request, guid):
    """Get all notebooks from the given location. """
    try:
        folder = Folder.objects.get(owner=request.user, guid=guid)
    except Folder.DoesNotExist:
        return { 'ok': False, 'reason': 'does-not-exist' }

    notebooks = []

    for notebook in Notebook.objects.filter(owner=request.user, folder=folder):
        mapping = notebook.backend.all()

        if len(mapping):
            engine_name = mapping[0].engine_type.name
        else:
            engine_name = u'(undefined)'

        notebooks.append({
            'guid': notebook.guid,
            'title': notebook.title,
            'engine': engine_name,
            'datetime': notebook.last_modified_time().strftime("%Y-%m-%d %H:%M:%S"),
        })

    return { 'ok': True, 'notebooks': notebooks }

@jsonrpc_auth_method('RPC.Notebooks.moveNotebooks')
def rpc_Notebooks_moveNotebooks(request, folder_guid, notebooks_guid):
    """Move the given notebooks to a new location. """
    try:
        folder = Folder.objects.get(owner=request.user, guid=folder_guid)
    except Folder.DoesNotExist:
        return { 'ok': False, 'reason': 'does-not-exist' }

    for notebook_guid in notebooks_guid:
        try:
            notebook = Notebook.objects.get(owner=request.user, guid=notebook_guid)
        except Folder.DoesNotExist:
            return { 'ok': False, 'reason': 'does-not-exist' }

        notebook.folder = folder
        notebook.save()

    return { 'ok': True }

@jsonrpc_auth_method('RPC.Notebooks.saveNotebook')
def rpc_Notebooks_saveNotebook(request, guid, cellsdata, orderlist):
    """Save the given notebook. """
    try:
        notebook = Notebook.objects.get(owner=request.user, guid=guid)
    except Folder.DoesNotExist:
        return { 'ok': False, 'reason': 'does-not-exist' }

    for cellid, data in cellsdata.items():
        cells = Cell.objects.filter(guid=cellid, notebook=notebook)

        content = data["content"]
        style = data["cellstyle"]
        props = data["props"]

        if len(cells) > 0:
            cell = cells[0]
            cell.content = content
            cell.type = u"text"
            cell.style = style
            cell.props = props
            cell.save()
        else:
            cell = Cell(guid=cellid,
                        notebook=notebook,
                        owner=notebook.owner,
                        content=content,
                        type=u"text",
                        style=style,
                        props=props)
            notebook.cell_set.add(cell)

    notebook.orderlist = orderlist
    notebook.save()

    return { 'ok': True }

@jsonrpc_auth_method('RPC.Notebooks.getCells')
def rpc_Notebooks_getCells(request, guid, type=None):
    """Retrieve cells from the given notebook. """
    try:
        notebook = Notebook.objects.get(owner=request.user, guid=guid)
    except Folder.DoesNotExist:
        return { 'ok': False, 'reason': 'does-not-exist' }

    if notebook.orderlist == 'orderlist':
        return { 'ok': True }

    def style_to_type(style):
        if style == 'outputtext':
            return 'output'

        if style == 'outputimage':
            return 'image'

        if style == 'text':
            return 'content'

        return style

    data, cells = {}, []

    for cell in Cell.objects.filter(notebook=notebook):
        ctype, guid = style_to_type(cell.style), cell.guid

        if type is None or ctype == type:
            data[guid] = {
                'guid': guid,
                'type': type,
                'content': cell.content,
            }

    orderlist = json.loads(notebook.orderlist)

    for guid in orderlist:
        if guid in data:
            cells.append(data[guid])

    return { 'ok': True, 'cells': cells }

