from sys import argv
from os import remove
from os.path import exists
from subprocess import Popen


script = argv[0]
if '/' in script:
    script_path = script[:script.rindex('/') + 1]
else:
    script_path = ''

config = {}
file = open(f'{script_path}loggers.config')
for line in file:
    key, value = line.strip().split(',')
    config[key] = value

environ_vars = {'PATH': config['virtual_environment'],
                'ANDROID_DATA': '/data', 'ANDROID_ROOT': '/system'}


servers = []
arguments = []
scripts = []
file = open(config['logs'] + 'loggers.txt', 'r')
for line in file:
    if line == '\n':
        arguments = []
    elif not arguments:
        server = line[:-1]
        servers.append(server)
        arguments = [server]
        scripts.append(Popen(['python', script_path + 'logger.py'] + arguments,
                             env=environ_vars))
file.close()


try:
    for script in scripts:
        script.wait()
except KeyboardInterrupt:
    for server in servers:
        logging = config['logs'] + server + '/logging'
        if exists(logging):
            remove(logging)

