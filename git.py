import os
import subprocess

from config import PROJECTS_PATH, GIT_REPOS_PATH, GIT_PATH

post_receive_content = 'git --work-tree=${PROJECT_DIR} checkout --force'


def create_repo(repo_name):
    # print(repo_name)

    project_path = os.path.join(PROJECTS_PATH, repo_name)
    git_repo_path = os.path.join(GIT_REPOS_PATH, repo_name + '.git')

    cmds = [
        {
            'cwd': GIT_REPOS_PATH,
            'cmd': [GIT_PATH, 'init', '--bare', repo_name + '.git']
        },
        # git config --global core.autocrlf true
        {
            'cwd': git_repo_path,
            'cmd': [GIT_PATH, 'config', 'core.autocrlf', 'true']
        },
        # git config --global core.safecrlf false
        {
            'cwd': git_repo_path,
            'cmd': [GIT_PATH, 'config', 'core.safecrlf', 'false']
        },
        # git config receive.denyCurrentBranch ignore
        {
            'cwd': git_repo_path,
            'cmd': [GIT_PATH, 'config', 'receive.denyCurrentBranch', 'ignore']
        },
        {
            'cwd': git_repo_path,
            'cmd': [GIT_PATH, '--work-tree=%s' % project_path, 'add', '.']
        },
        {
            'cwd': git_repo_path,
            'cmd': [GIT_PATH, '--work-tree=%s' % project_path, 'commit', '-m', '\'init project\'']
        }
    ]
    for item in cmds:
        p = subprocess.Popen(' '.join(item.get('cmd')), cwd=item.get('cwd'), shell=True,
                             stderr=subprocess.PIPE)

        for line in p.stderr:
            yield line.decode()

    post_receive_path = os.path.join(git_repo_path, 'hooks/post-receive')
    with open(post_receive_path, 'w') as f:
        f.write(post_receive_content)

    os.chmod(post_receive_path, 0o755)
    yield 'ok!'


def git_command(repo_name, version, *args):
    dir_name = os.path.join(GIT_REPOS_PATH, repo_name)
    project_dir = os.path.join(PROJECTS_PATH, repo_name[:-4])

    if not os.path.isdir(dir_name):

        for i in create_repo(repo_name[:-4]):
            pass

    cmd = [GIT_PATH, *args]
    env = os.environ.copy()
    env['PROJECT_DIR'] = project_dir
    p = subprocess.Popen(' '.join(cmd), cwd=dir_name, env=env, shell=True, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)

    p.wait()
    out = p.stdout.read()

    return out


def git_command_with_input(repo_name, version, input_data, *args):
    dir_name = os.path.join(GIT_REPOS_PATH, repo_name)

    if not os.path.isdir(dir_name):
        create_repo(repo_name[:-4])
    env = os.environ.copy()
    cmd = [GIT_PATH, *args]
    env['PROJECT_DIR'] = os.path.join(PROJECTS_PATH, repo_name[:-4])
    p = subprocess.Popen(' '.join(cmd), cwd=dir_name, env=env, shell=True, stdout=subprocess.PIPE,
                         stdin=subprocess.PIPE)

    p.stdin.write(input_data)
    p.stdin.flush()
    for line in p.stdout:
        yield line
