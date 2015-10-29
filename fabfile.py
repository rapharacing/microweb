import os

from fabric.api import env
from fabric.api import sudo
from fabric.api import prefix

from fabric.contrib.project import rsync_project
from fabric.context_managers import settings

from contextlib import contextmanager

env.hosts = []

env.serve_root = '/srv/www/django'
env.project_name = 'microweb'
env.virtualenv_name = 'microwebenv'

env.project_root = os.path.join(env.serve_root, env.project_name)
env.virtualenv_root = os.path.join(env.serve_root, env.virtualenv_name)
env.requirements_path = os.path.join(env.project_root, 'requirements.txt')

env.activate = 'source %s' % os.path.join(env.virtualenv_root, 'bin/activate')

@contextmanager
def activate_virtualenv():

    with prefix(env.activate):
        yield

def dev_env():
    env.hosts.append('wpy01.dev.microcosm.cc')

def dev2_env():
    env.hosts.append('wpyrapha.dev.microcosm.cc')

def prod_env():
    env.hosts.append('wpyrapha.microcosm.cc:2020')

def test_env():
    env.hosts.append('deployment@dev.microco.sm')

def destroy_virtualenv():

    sudo('rm -rf %s' % env.virtualenv_root, user='django')

def create_virtualenv():

    sudo('virtualenv %s' % env.virtualenv_root, user='django')

def install_requirements():

    with activate_virtualenv():
        sudo('pip install -r %s' % env.requirements_path, user='django')

def collectstatic():

    with activate_virtualenv():
        sudo('python %s collectstatic --noinput' % os.path.join(env.project_root, 'manage.py'), user='django')

def rsync():

    rsync_project(
        env.serve_root,
        extra_opts='--exclude .git/ --exclude ENV/ --delete --rsync-path="sudo -u django rsync"'
    )

def start_service():

    sudo('service microweb start', user='root')

def stop_service():

    sudo('service microweb stop', user='root')

def restart_service():

    sudo('service microweb restart', user='root')

def restart_memcached():

    sudo('service memcached restart', user='root')

def first_deploy():

    create_virtualenv()
    rsync()
    install_requirements()
    collectstatic()
    start_service()

def redeploy():

    rsync()
    install_requirements()
    collectstatic()
    restart_service()
