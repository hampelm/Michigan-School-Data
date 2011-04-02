# Chicago Tribune News Applications fabfile
# No copying allowed

from fabric.api import *

"""
Base configuration
"""
#name of the deployed site if different from the name of the project
env.site_name = 'schools'
env.project_name = 'schools'
#env.database_password = 'tener'
env.site_media_prefix = "assets"
env.admin_media_prefix = "admin_media"
env.path = '/home/users/mischool' % env
env.log_path = '/home/users/mischool/logs' % env
env.env_path = '%(path)s/env' % env
env.repo_path = '%(path)s/htdocs' % env
env.nginx_config_path = '.....'
env.python = 'python2.6'
env.repository_url = 'git@github.com:hampelm/Michigan-School-Data.git' % env

"""
Environments
"""
def production():
    """
    Work on production environment
    """
    env.settings = 'production'
    env.hosts = ['aawiki.aadl.org']
    env.user = 'mischool'

        
"""
Commands - setup
"""
def setup():
    """
    Setup a fresh virtualenv, install everything we need.
    
    Does NOT perform the functions of deploy().
    """    
    require('settings', provided_by=[production, staging])
    
    setup_directories()
    setup_virtualenv()
    clone_repo()
    checkout_latest()
    install_requirements()
#    install_conf() # not handling nginx conf

def setup_directories():
    """
    Create directories necessary for deployment.
    """
    run('mkdir -p %(env_path)s' % env)
    
def setup_virtualenv():
    """
    Setup a fresh virtualenv.
    """
    run('virtualenv -p %(python)s --no-site-packages %(env_path)s;' % env)
    run('source %(env_path)s/bin/activate; easy_install -U setuptools; easy_install pip;' % env)

def clone_repo():
    """
    Do initial clone of the git repository.
    """
    run('git clone %(repository_url)s %(repo_path)s' % env)

def checkout_latest():
    """
    Pull the latest code on the specified branch.
    """
    with cd(env.repo_path):
        run('git checkout %(branch)s;' % env)
        run('git pull origin %(branch)s' % env)

def install_requirements():
    """
    Install the required packages using pip.
    """
    run('source %(env_path)s/bin/activate; pip install -E %(env_path)s -r %(repo_path)s/requirements.txt' % env)

def install_conf():
    """
    Install the nginx site config file.
    """
    sudo('cp %(repo_path)s/configs/%(settings)s/nginx.conf %(nginx_config_path)s' % env)

    
"""
Commands - deployment
"""
def deploy():
    """
    Deploy the latest version of the site to the server and restart Apache2.
    
    Does not perform the functions of load_new_data().
    """    
    require('settings', provided_by=[production, staging])
            
    checkout_latest()
    gzip_assets()
    maintenance_down()
    
def reboot(): 
    """
    Restart the server.
    """
    sudo('/mnt/apps/bin/restart-all-apache.sh')
    
def maintenance_down():
    """
    Reinstall the normal site configuration.
    """
    install_conf()
    reboot()

"""
Commands - data
"""
def load_data():
    """
    Load data using the parser:
    """
    require('settings', provided_by=[production, staging])
    
    with cd(env.repo_path):
        run('python parser/parser.py')    
    

"""
Commands - miscellaneous
"""
    
def echo_host():
    """
    Echo the current host to the command line.
    """
    run('echo %(settings)s; echo %(hosts)s' % env)

"""
Shiva, destroyers of worlds
"""
# def shiva_the_destroyer():
#     """
#     Remove all directories, databases, etc. associated with the application.
#     """
#     with settings(warn_only=True):
#         run('rm -Rf %(path)s' % env)
#         run('rm -Rf %(log_path)s' % env)
#         pgpool_down()
#         run('dropdb %(project_name)s' % env)
#         run('dropuser %(project_name)s' % env)
#         pgpool_up()
#         sudo('rm %(apache_config_path)s' % env)
#         sudo('rm %(apache_config_path)s_api' % env)
#         reboot()
#         run('s3cmd del --recursive s3://%(s3_bucket)s/%(project_name)s' % env)

