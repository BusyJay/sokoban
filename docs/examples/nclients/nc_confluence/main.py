import os
import functools
import json
import mimetypes
from urlparse import urlparse
import kerberos

import requests


__author__ = 'jay'


class PermissionDenied(Exception):
    pass


class OperationError(Exception):
    pass


class _ApiRequest(object):
    """A simple wrap of confluence's json-rpc api
    """
    JSON_RPC_API = 'rpc/json-rpc/confluenceservice-v2/%s'

    def __init__(self, context_url, logger, username, password):
        if not context_url:
            raise ValueError
        self.logger = logger
        self.session = requests.session()
        self._prepare()
        self._login(context_url, username, password)

        final_url = context_url
        if final_url[-1] != '/':
            final_url += '/'
        final_url += self.JSON_RPC_API

        self.final_url = final_url

    def __getattr__(self, item):
        def _api(*args, **kwargs):
            if len(args):
                data = json.dumps(args)
            else:
                data = json.dumps(kwargs)
            res = self.session.post(
                self.final_url % item, data,
                headers={'content-type': 'application/json'})
            if not res.ok:
                raise OperationError
            try:
                res = json.loads(res.text)
            except Exception:
                self.logger.error(res.content)
                raise
            return res
        return _api

    def _prepare(self):
        ca_path = requests.utils.DEFAULT_CA_BUNDLE_PATH
        for path in ('/etc/ssl/certs/ca-certificates.crt',
                     '/etc/pki/tls/certs/ca-bundle.crt'):
            if os.path.exists(path):
                ca_path = path
                break
        # a little hack
        self.session.request = functools.partial(self.session.request,
                                                 verify=ca_path)

    def _login(self, context_url, username, password):
        # use kerberos login, should be remove for security consideration
        if not username and not password:
            host = urlparse(context_url).hostname
            result, kbr_ctx = kerberos.authGSSClientInit('HTTP@%s' % host)
            if result < 1:
                raise OperationError("Kerberos login not support!")
            kerberos.authGSSClientStep(kbr_ctx, '')
            cret = 'Negotiate %s' % kerberos.authGSSClientResponse(kbr_ctx)
            step_auth_url = context_url
            if step_auth_url[-1] != '/':
                step_auth_url += '/'
            step_auth_url += 'step-auth-gss'
            res = self.session.get(step_auth_url, headers={
                'Authorization': cret,
            })
        else:
            # prepare some cookies
            self.session.get(context_url)
            res = self.session.get(context_url, params={'os_authType': 'basic'},
                                  auth=(username, password))
        if not res.ok or not res.headers.get('X-AUSERNAME', None):
            # TODO delete me
            print res.text, res.headers
            raise PermissionDenied("Failed to login")

    def close(self):
        self.session.close()


class NetClient(object):
    OperationError = OperationError
    PermissionDenied = PermissionDenied

    def __init__(self, form, logger, **kwargs):
        self._api_clinet = _ApiRequest(form['context_url'], logger,
                                       form['username'], form['password'])
        self._space = form['space']
        self._parent_id = None
        self.logger = logger
        parent_page_title = form.get('parent_page_title', None) or None
        if parent_page_title:
            parent_page = self.get_page(title=parent_page_title)
            if parent_page:
                self._parent_id = parent_page[0]

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def register_attachment(self, attach, owner_page_id,
                            filename, content_type=None):
        attachment = {
            'fileName': filename,
            'contentType': content_type or mimetypes.guess_type(filename)[0]
        }
        try:
            attach_data = getattr(attach, 'read')()
        except AttributeError:
            attach_data = attach
        res = self._api_clinet.addAttachment(owner_page_id, attachment,
                                             attach_data.encode("base64"))
        if 'error' in res:
            raise self.OperationError(res['error'])
        return res['id'], res['url']

    def move_attachment(self, spid, sn, tpid, tn):
        return self._api_clinet.moveAttachment(str(spid), sn,
                                               str(tpid), tn) is True

    def delete_attachment(self, pid, name):
        return self._api_clinet.removeAttachment(str(pid), name) is True

    def _store_page(self, title, content, pid=None, version=None,
                    parent_id=None, mark_home=False):
        parent_id = parent_id or self._parent_id
        page = {'space': self._space, 'title': title}
        try:
            page['content'] = content.read()
        except AttributeError:
            page['content'] = content
        if pid:
            page['id'] = pid
        if version:
            page['version'] = version
        if parent_id:
            page['parentId'] = parent_id
        if mark_home:
            page['homePage'] = mark_home
        res = self._api_clinet.storePage(page)
        if 'error' in res:
            raise self.OperationError(res['error'])
        return (res['id'], res['version'], res['url'],
                res['content'], res['parentId'], res['title'])

    def register_page(self, *args, **kwargs):
        return self._store_page(*args, **kwargs)

    def get_all_pages(self, parent_id=None):
        """
        :return: summary of all pages under parent_id
        """
        parent_id = parent_id or self._parent_id
        if parent_id:
            pages = self._api_clinet.getDescendents(parent_id)
        else:
            pages = self._api_clinet.getPages(self._space)
        return pages

    def get_page(self, pid=None, title=None):
        if pid:
            res = self._api_clinet.getPage(str(pid))
        else:
            res = self._api_clinet.getPage(self._space, title)
        if 'error' in res:
            raise self.OperationError(res['error'])
        return (res['id'], res['version'], res['title'],
                res['url'], res['content'], res['parentId'])

    def modified_page(self, pid, version, **kwargs):
        kwargs['pid'] = str(pid)
        kwargs['version'] = version
        return self._store_page(**kwargs)

    def move_page(self, spid, tpid, position):
        return self._api_clinet.movePage(spid, tpid, position) is True

    def delete_page(self, pid):
        return self._api_clinet.removePage(pid) is True

    def close(self):
        self._api_clinet.close()
