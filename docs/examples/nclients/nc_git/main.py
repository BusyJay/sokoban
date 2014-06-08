from datetime import datetime
import os

import sh

__author__ = 'jay'


def _parse_log(logs, begin_track, end_track):
    in_a_commit = False
    history = []
    temp_messages = []
    commit_id = None
    i = 0
    while i < len(logs):
        log = logs[i]
        i += 1
        if in_a_commit:
            if log.startswith(end_track + commit_id):
                history[-1]['commit_message'] = '\n'.join(temp_messages)
                in_a_commit = False
            else:
                temp_messages.append(log)
        else:
            if log.startswith(begin_track):
                commit_id = log[len(begin_track):]
                temp_messages = []
                in_a_commit = True
                history.append({
                    'version': commit_id,
                    'author': logs[i],
                    'email': logs[i + 1],
                    'date': datetime.fromtimestamp(long(logs[i + 2])),
                    'changed_files': [],
                })
                i += 3  # another 3 record have been read
            elif not log.isspace() and log:
              # then it should be a list of files that have been changed
                log = log.split('\t', 1)
                action = log[0].rsplit(None, 1)[-1]
                if action == 'D':
                    history[-1]['changed_files'].append(('delete',
                                                         log[-1]))
                elif action[0] == 'R':
                    origin, updated = log[-1].split('\t')
                    history[-1]['changed_files'].append(('move',
                                                         origin, updated))
                    if action[1] != '1':
                        history[-1]['changed_files'].append(('modified',
                                                             updated))
                elif action == 'M':
                    history[-1]['changed_files'].append(('modified',
                                                         log[-1]))
                elif action == 'A':
                    history[-1]['changed_files'].append(('add', log[-1]))
                else:
                    raise ValueError("unknown action type: %s" % action)
    return history


class NetClient(object):
    def __init__(self, form, logger, **kwargs):
        # noinspection PyUnresolvedReferences
        self.git = sh.git.bake(_tty_out=False)
        self.url = form['url']
        self.branch_name = form['branch_name']
        self.project_path = None
        self.logger = logger

    def open_project(self, project_path):
        self.git = self.git.bake(git_dir=project_path)
        self.project_path = project_path
        # convenient for `with self.open_project() as nc:`
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def update_project(self):
        self.logger.info('updating the project...')
        if os.path.exists(self.project_path):
            self.git.fetch()
            return
        self.git.clone(self.url, self.project_path, bare=True)
        self.git('symbolic-ref', 'HEAD', 'refs/heads/' + self.branch_name)
        self.logger.info('updated.')

    def get_version(self):
        if not os.path.exists(self.project_path):
            return None  # project has not been initialed
        return self.git('rev-parse', 'HEAD').strip()

    def get_lazy_change_log(self, end_pos='HEAD',
                            begin_pos=None, max_count=-1):
        """get an iterator for change log.

         All logs is return from oldest to newest.
        :param end_pos: enclosed end point of commit
        :param begin_pos: unenclosed begin point of commit
        :param max_count: get max_count newest log
        """
        commits = [commit.split()[0] for commit in
                   self.git.log((begin_pos and
                                 ('%s..' % begin_pos) or '') + end_pos,
                                oneline=True, reverse=True)]
        if max_count != -1:
            commits = commits[:max_count]
        for commit in commits:
            log = self.get_change_log(begin_pos=None, end_pos=commit,
                                      max_count=1, reverse=False)
            # get_change_log only returns change log.
            # some commits (like init commit) change nothing,
            #  so may not be found.
            if not log:
                continue
            log = log[0]
            yield log

    def get_change_log(self, end_pos='HEAD', begin_pos=None,
                       max_count=-1, reverse=True):
        """Get all change log from repo

        You are likely want to set reverse to False when max_count is 1.
        :param end_pos:
        :param begin_pos:
        :param max_count:
        :param reverse:
        :return:
        """
        begin_track = 'begin commit '
        end_track = 'end commit '
        log_format = '%n'.join(('format:' + begin_track + '%H',
                                '%an', '%ae', '%ct', '%B', end_track + '%H'))
        logs = self.git.whatchanged((begin_pos and ('%s..' % begin_pos) or '')
                                    + end_pos, M=True, format=log_format,
                                    reverse=reverse, m=True,
                                    max_count=max_count).split('\n')
        return _parse_log(logs, begin_track, end_track)

    def get_file(self, source_path, version='HEAD'):
        """return a file, well a directory is also ok, referenced by path.

        :param version: specific version of file
        :param source_path:
        :return:
        """
        return str(self.git.show(version + ':' + source_path))

    # noinspection PyUnresolvedReferences
    def copy_file(self, source_path, target_base_path,
                  version='HEAD', cleanup=True):
        """copy a file or directory to target base path.

        for example, copy doc/readme.md to /tmp will result in
         /tmp/doc/readme.md
        :param source_path: if None, will checkout all files
        :param target_base_path: if specify, will copy the file to that
         directory rather than return as string. You may use absolute path.
        :param version:
        :param cleanup: whether cleanup all the untracked file
        :return:
        """
        git = self.git.bake(work_tree=target_base_path)
        if source_path:
            source_path = os.path.join(target_base_path, source_path)
            parent_path = source_path is None and os.path.dirname(source_path)
        else:
            source_path = parent_path = target_base_path
        if not os.path.exists(parent_path):
            sh.mkdir(parent_path, p=True)
        git.checkout(version, source_path)
        if cleanup:
            git.clean(f=True, d=True)


if __name__ == '__main__':
    from time import time
    begin_time = time()
    form = {'url': 'https://code.engineering.redhat.com/gerrit/p/gitview.git',
            'branch_name': 'develop'}
    nc = NetClient(form)
    with nc.open_project('/tmp/gitview') as nc:
        nc.update_project()
        changes = nc.get_change_log()
        print changes
        print nc.get_version()
        path = changes[-1]['changed_files'][0][-1]
        print nc.get_file(path, changes[-1]['version'])
        nc.copy_file(path, '/tmp/test_gitview', changes[-1]['version'])
        assert os.path.exists(os.path.join('/tmp/test_gitview', path))
    with nc.open_project('/tmp/gitview') as nc:
        nc.update_project()
        for change in nc.get_lazy_change_log('3b6e304', begin_pos='9285fedfa'):
            print change

    print time() - begin_time
