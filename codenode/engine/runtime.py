
from codenode.engine.introspection import introspect

def build_namespace():
    try:
        import matplotlib
        matplotlib.use('Agg')

        # XXX: must be in this order because of matplotlib.use()
        from codenode.external.mmaplotlib import codenode_plot
        import pylab

        namespace = dict(pylab.__dict__)

        namespace.update({
            'show': codenode_plot.show,
            'introspect': introspect,
        })
    except ImportError:
        namespace = {'introspect': introspect}

    return namespace

def find_port():
    import socket
    s = socket.socket()
    s.bind(('',0))
    port = s.getsockname()[1]
    s.close()
    del s
    return port

def ready_notification(port):
    """The backend process manager expects to receive a port number on
    stdout when the process and rpc server within the process are ready.
    """
    import sys
    sys.stdout.write('port:%s' % str(port))

