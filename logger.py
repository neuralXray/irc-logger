import irc.client
from irc.client import ServerNotConnectedError
from irc.client import ServerConnectionError

from sys import argv
from sys import path
from os import mkdir, remove, listdir
from os.path import exists, isdir
from datetime import datetime, timedelta
from time import sleep, time
from threading import Thread
from re import search, split
from subprocess import Popen, PIPE

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
file.close()

path.insert(0, config['working_directory'])

from utils import date_time_format, len_date_time


server = argv[1]
port = 6667


nicks = {}
hosts = {}
whois_nicks = {}
banned_in_channels = []
cannot_join = {}
finished = {}
preakick_channels = {}
akick_channels = {}
ignore_list = []
ignore_msg_list = []

ping_time = time()
reconnecting = False
disconnected = True
connected = False
my_ip = ''

access_nicks = {}
root_nicks = {}
search_queue = []
len_max = 422
clock = time()


if not exists(config['logs']):
    mkdir(config['logs'])


log_dir = config['logs'] + server + '/'
if not exists(log_dir):
    mkdir(log_dir)

logging_dir = log_dir + 'logging'
#assert not exists(logging_dir)
'''
if exists(logging_dir):
    print(f'{logging_dir} exists. This means you are still logging or you Ping timeout.')
    print('Do you want to start logging again? y/n')
    start_logging = ''
    while start_logging not in ['y', 'n']:
        start_logging = input()
        if start_logging not in ['y', 'n']:
            print('Possible answers are "y" or "n".')
    if start_logging == 'n':
        exit()
'''
file = open(logging_dir, 'w')
file.close()


year_month = datetime.now().strftime('%Y-%m')
year_month_log_dir = log_dir + year_month + '/'
if not exists(year_month_log_dir):
    mkdir(year_month_log_dir)


channel_log_dir = year_month_log_dir + server + '.log'
if exists(channel_log_dir):
    remove(channel_log_dir)

if not exists(config['logs'] + 'preakick.txt'):
    file = open(config['logs'] + 'preakick.txt', 'w')
    file.close()

if not exists(config['logs'] + 'akick.txt'):
    file = open(config['logs'] + 'akick.txt', 'w')
    file.close()

if not exists(config['logs'] + 'cbaned.txt'):
    file = open(config['logs'] + 'cbaned.txt', 'w')
    file.close()

if not exists(config['logs'] + 'ignore.txt'):
    file = open(config['logs'] + 'ignore.txt', 'w')
    file.close()

if not exists(config['logs'] + 'ignore_msg.txt'):
    file = open(config['logs'] + 'ignore_msg.txt', 'w')
    file.close()


def split_line(line):
    if line[-1] == '\n':
        return line[:-1].split(',')
    else:
        return line.split(',')


def load_config():
    global my_nick, password, my_ident, realname, channels, ignore_list, ignore_msg_list

    i = 0
    file = open(config['logs'] + 'loggers.txt', 'r')
    for line in file:
        if line[:-1] == server:
            i = 1
        elif i > 0:
            if i == 1:
                my_nick = line[:-1]
            elif i == 2:
                password = line[:-1]
                if password == 'None':
                    password = None
            elif i == 3:
                my_ident = line[:-1]
            elif i == 4:
                realname = line[:-1]
            elif i == 5:
                channels = split_line(line)[:40]
                channels = [channel.lower() for channel in channels]
            i = i + 1
    file.close()

    ignore_list = []
    file = open(config['logs'] + 'ignore.txt', 'r')
    for line in file:
        if line:
            s, m = split_line(line)
            if s == server:
                ignore_list.append(m)
    file.close()

    ignore_msg_list = []
    file = open(config['logs'] + 'ignore_msg.txt', 'r')
    for line in file:
        if line:
            s, m = split_line(line)
            if s == server:
                ignore_msg_list.append(m)
    file.close()


# Fix end logging if needed
def read_last_line(filename):
    # Works if filename isn't empty and if all lines end with newline
    file = open(filename, 'rb+')
    file.seek(-2, 2)
    while bool(file.tell()) and (file.read(1) != b'\n'):
        file.seek(-2, 1)
    pos = file.tell()
    line = file.readline().decode()
    if search('^\x00+$', line):
        file.truncate(pos)
        file.seek(pos - 2)
        while bool(file.tell()) and (file.read(1) != b'\n'):
            file.seek(-2, 1)
        line = file.readline().decode()
    file.close()
    return line

channel_dirs = {}
for month_dir in sorted(listdir(log_dir)):
    if isdir(f'{log_dir}{month_dir}'):
        for chan in listdir(f'{log_dir}{month_dir}'):
            if (chan[0] == '#') or (chan == '.log'):
                channel_dirs[chan] = f'{log_dir}{month_dir}/{chan}'

date_times = {}
year_month = datetime.now().strftime('%Y-%m')
for chan, directory in channel_dirs.copy().items():
    last_line = read_last_line(directory)
    if last_line == '\n':
        del channel_dirs[chan]
    else:
        d = last_line[:len_date_time - 1]
        date_time = datetime.strptime(d, date_time_format)
        date_times[d] = date_time
        channel_dirs[chan] = f'{log_dir}{year_month}/{chan}'

if channel_dirs:
    load_config()
    date_time = sorted(date_times.keys(), key=lambda d: date_times[d])[-1]
    reason = 'Ping timeout: 120 seconds'
    log = f'{date_time} *\tENDING LOGGING ({reason})\n\n'
    log_chan = f'{date_time} *\t{my_nick} has quit ({reason})\n{date_time} *\tENDING LOGGING\n\n'
    for chan, directory in channel_dirs.items():
        if exists(directory):
            file = open(directory, 'a')
        else:
            file = open(directory, 'w')
        if chan == '.log':
            file.write(log)
        else:
            file.write(log_chan)
        file.close()


def remove_akick_channel(channel, pre=''):
    global akick_channels, preakick_channels
    if pre:
        del preakick_channels[channel]
    else:
        del akick_channels[channel]
    file = open(config['logs'] + pre + 'akick.txt', 'r')
    lines = file.readlines()
    file.close()
    for line in lines:
        if line:
            _, s, c, _ = split_line(line)
            if (s == server) and (c == channel):
                lines.remove(line)
                file = open(config['logs'] + pre + 'akick.txt', 'w')
                file.writelines(lines)
                file.close()
                break


def logging(log, channel):
    datetime_now = datetime.now()
    date_time = datetime_now.strftime(date_time_format)
    year_month = datetime_now.strftime('%Y-%m')
    year_month_log_dir = log_dir + year_month + '/'
    if not exists(year_month_log_dir):
        mkdir(year_month_log_dir)

    if channel in root_nicks.keys():
        channel = '.' + channel
    channel_log_dir = year_month_log_dir + channel.lower() + '.log'
    if exists(channel_log_dir):
        file = open(channel_log_dir, 'a')
    else:
        file = open(channel_log_dir, 'w')

    file.write(f'{date_time} {log}\n')
    file.close()


def end_logging(reason):
    date_time_now = datetime.now()
    date_time = date_time_now.strftime(date_time_format)

    year_month = date_time_now.strftime('%Y-%m')
    year_month_log_dir = log_dir + year_month + '/'
    if not exists(year_month_log_dir):
        mkdir(year_month_log_dir)

    log = f'{date_time} *\tENDING LOGGING ({reason})\n\n'
    channel_log_dir = year_month_log_dir + '.log'
    if exists(channel_log_dir):
        file = open(channel_log_dir, 'a')
    else:
        file = open(channel_log_dir, 'w')
    file.write(log)
    file.close()

    log = f'{date_time} *\tENDING LOGGING\n\n'
    end_logging_channels = list(nicks.keys())
    for channel in end_logging_channels:
        channel_log_dir = year_month_log_dir + channel + '.log'
        if exists(channel_log_dir):
            file = open(channel_log_dir, 'a')
        else:
            file = open(channel_log_dir, 'w')
        file.write(log)
        file.close()


def welcome_thread(connection):
    global finished, cannot_join, preakick_channels, akick_channels
    sleep(10)
    load_config()
    preakick_channels = {}
    akick_channels = {}

    file = open(config['logs'] + 'preakick.txt', 'r')
    for line in file:
        if line:
            d, s, c, _ = split_line(line)
            if s == server:
                date_time_now = datetime.now()
                date_time_akick = datetime.strptime(d, date_time_format)
                preakick_channels[c] = date_time_akick
    file.close()
    file = open(config['logs'] + 'akick.txt', 'r')
    for line in file:
        if line:
            d, s, c, _ = split_line(line)
            if s == server:
                date_time_now = datetime.now()
                date_time_akick = datetime.strptime(d, date_time_format)
                akick_channels[c] = date_time_akick
    file.close()

    for channel in channels:
        if disconnected:
            break
        if channel in banned_in_channels:
            continue
        elif channel in preakick_channels.keys():
            time_delta = (datetime.now() - akick_channels[channel])
            seconds = 60*60*(1 + 24*7) - (time_delta.days*24*60*60 + time_delta.seconds)
            if seconds > 0:
                Thread(target=join_channel_thread, args=(connection, channel, secons,)).start()
                continue
        elif channel in akick_channels.keys():
            time_delta = (datetime.now() - akick_channels[channel])
            seconds = 60*60*(1 + 24*31) - (time_delta.days*24*60*60 + time_delta.seconds)
            if seconds > 0:
                Thread(target=join_channel_thread, args=(connection, channel, seconds,)).start()
                continue
        finished[channel] = False
        cannot_join[channel] = True
        try:
            connection.send_raw(f'join {channel}')
        except ServerNotConnectedError:
            break
        while (not disconnected) and (not cannot_join[channel]) and (not finished[channel]):
                sleep(1)
        del cannot_join[channel]
        del finished[channel]


def check_connected_thread(connection, client):
    global ping_time, reconnecting, access_nicks, root_nicks
    while True:
        if not exists(logging_dir):
            raise KeyboardInterrupt

        if time() - ping_time > 10*60:
            ping_time = time()
            reconnecting = True
            try:
                connection.reconnect()
            except ServerConnectionError:
                Thread(target=reconnect_thread, args=(connection,)).start()

        for n in list(access_nicks.keys()):
            if (time() - access_nicks[n] > 60*60) and (n not in hosts.keys()):
                del access_nicks[n]
                printout = 'ACCESS session expired'
                send_privmsg(connection, n, printout)
        for n in list(root_nicks.keys()):
            if (time() - root_nicks[n] > 60*60) and (n not in hosts.keys()):
                printout = 'ROOT session expired'
                send_privmsg(connection, n, printout)
                del root_nicks[n]

        sleep(10)


def joined_thread(connection, channel):
    global whois_nicks, finished
    if channel in nicks.keys():
        channel_nicks = nicks[channel]
        for nick in channel_nicks:
            if disconnected or (channel not in nicks.keys()):
                break
            if nick != my_nick:
                if nick in hosts.keys():
                    host = hosts[nick]
                    log = f'*\t{host} was joined'
                    logging(log, channel)
                else:
                    if nick in whois_nicks.keys():
                        whois_nicks[nick] = whois_nicks[nick] + [channel.lower()]
                    else:
                        whois_nicks[nick] = [channel.lower()]
                        try:
                            connection.send_raw(f'whois {nick}')
                        except ServerNotConnectedError:
                            break
                        sleep(5)
    if channel in finished.keys():
        finished[channel] = True


def join_channel_thread(connection, channel, seconds):
    # if bannedfromchan or inviteonlychan: seconds=(60 + 1)*60
    # elif unavailresource: seconds=10
    # elif preakick (kicked by CHaN): seconds=60*60*(1 + 24*7)
    sleep(seconds)
    if channel in channels:
        send_raw(connection, f'join {channel}')


def reconnect_thread(connection):
    sleep(10)
    try:
        connection.reconnect()
    except ServerConnectionError:
        Thread(target=reconnect_thread, args=(connection,)).start()


def connect_thread(connection):
    global connected
    sleep(10)
    try:
        connection.connect(server, port, my_nick, password=password,
                           username=my_ident, ircname=realname)
        connected = True
    except ServerConnectionError:
        Thread(target=connect_thread, args=(connection,)).start()


def find_nicks_now_thread(connection, nick_send, nick_search, ident_search, ip_search):
    clones_nicks = []
    clones = []
    if ip_search.endswith('.79j.0Ar7OI.virtual') and (server == 'irc.chathispano.com'):
        printouts = [f'*\t[{nick_search}] Unable to find clone(s) (IRCCloud)']
    else:
        for n, h in hosts.copy().items():
            k = h.find('@')
            ident = h[h.find('!') + 1:k]
            ip = h[k + 1:]
            if (ip == ip_search) and (n.lower() != nick_search.lower()) and (n not in clones_nicks):
                clones_nicks.append(n)
                clones.append(n + '!' + ident)
        if clones:
            printouts = [f'*\t[{nick_search}] Clone(s): ' + ', '.join(clones)]
        else:
            printouts = []

    present_in_channels = []
    for channel in nicks.keys():
        if nick_search.lower() in [nick.lower() for nick in nicks[channel].copy()]:
            present_in_channels.append(channel)
    if present_in_channels:
        present_in_channels.sort()
        printout = f'{nick_search} is in {len(present_in_channels)} common channel(s): ' + \
                       ', '.join(present_in_channels)
        printouts = printouts + [printout[i:i + len_max] for i in range(0, len(printout), len_max)]
    if nick_search == my_nick:
        not_present_in_channels = set(channels) - set(nicks.keys())
        if not_present_in_channels:
            printout = f'{nick_search} is not present in ' + ', '.join(not_present_in_channels)
            printouts = printouts + \
                        [printout[i:i + len_max] for i in range(0, len(printout), len_max)]

    if not printouts:
        printouts = [f"{nick_search} isn't present"]

    for printout in printouts:
        send_privmsg(connection, nick_send, printout)
        sleep(2)


def find_nicks_history_thread(connection):
    global search_queue
    while search_queue:
        nick_send, nick_search, ident_search, ip_search, months = search_queue[0]
        process = Popen(['python3', f'{config["working_directory"]}nicks_channels.py', server,
                         nick_search, ident_search, ip_search, months], stdout=PIPE, text=True)

        printouts = []
        for printout in process.stdout.read().split('\n')[1:]:
            printouts = printouts + \
                [printout[i:i + len_max] for i in range(0, len(printout), len_max)]

        for printout in printouts:
            send_privmsg(connection, nick_send, printout)
            sleep(2)

        del search_queue[0]


def privmsg_commands_thread(connection, nick, message):
    global access_nicks, search_queue, reconnecting, channels
    i = message.find(' ')
    if i == -1:
        command = message
        arguments = ''
    else:
        command = message[:i]
        arguments = message[i + 1:]
    command = command.upper()

    if command == 'IDENTIFY':
        if arguments == config['access']:
            printout = 'identified with ACCESS level'
            send_privmsg(connection, nick, printout)
            access_nicks[nick] = time()
        elif arguments == config['root']:
            printout = 'identified with ROOT level'
            send_privmsg(connection, nick, printout)

    elif (command == 'HELP') and (arguments.replace(' ', '') == ''):
        if nick in access_nicks.keys():
            printout = 'SEARCH nick ident ip [months=1]'
            send_privmsg(connection, nick, printout)
            sleep(2)
        if nick in root_nicks.keys():
            for printout in ['RAW command', 'LIST', 'LOAD_CONFIG']:
                send_privmsg(connection, nick, printout)
                sleep(2)

    elif (command == 'SEARCH') and (nick in access_nicks.keys()):
        arguments = split(' +', arguments)
        if (len(arguments) == 3) or (len(arguments) == 4):
            nick_search = arguments[0]
            ident_search = arguments[1]
            ip_search = arguments[2]
            if len(arguments) == 4:
                months = arguments[3]
                if not search('[0-9]+', months):
                    return None
            else:
                months = '1'
            Thread(target=find_nicks_now_thread,
                   args=(connection, nick, nick_search, ident_search, ip_search,)).start()
            if months != '0':
                search_id = nick, nick_search, ident_search, ip_search, months
                if search_id not in search_queue:
                    if search_queue:
                        search_queue.append(search_id)
                        printout = f'{len(search_queue)}º search queued'
                        send_privmsg(connection, nick, printout)
                    else:
                        search_queue.append(search_id)
                        Thread(target=find_nicks_history_thread, args=(connection,)).start()

    elif (command == 'RAW') and (nick in root_nicks.keys()):
            i = arguments.find(' ')
            join_akick = False
            if i == -1:
                command = arguments
                arguments = ''
            else:
                command = arguments[:i]
                arguments = arguments[i + 1:]
                command = command.lower()
                if command == 'join':
                    date_time_now = datetime.now()
                    for channel, date_time in preakick_channels.items():
                        if arguments.lower() == channel:
                            if date_time + timedelta(days=7, hours=1) > date_time_now:
                                join_akick = True
                                printout = f'preakick active in {arguments}'
                                send_privmsg(connection, nick, printout)
                                break
                    for channel, date_time in akick_channels.items():
                        if arguments.lower() == channel:
                            if date_time + timedelta(days=31, hours=1) > date_time_now:
                                join_akick = True
                                printout = f'akick active in {arguments}'
                                send_privmsg(connection, nick, printout)
                                break
            if not join_akick:
                if command == 'forcejoin':
                    command = 'join'
                try:
                    connection.send_raw(f'{command} {arguments}')
                    if (command == 'join') and (channel not in channels):
                        channels.append(channel)
                    elif (command == 'part') and (channel in channels):
                        channels.remove(channel)
                    elif command == 'privmsg':
                        i = arguments.find(' ')
                        if i == -1:
                            target = arguments
                            message = ''
                        else:
                            target = arguments[:i]
                            message = arguments[i + 1:]
                        target = target.lower()
                        log = f'\t<{my_nick}> {message}'
                        logging(log, target)
                except:
                    pass

    elif (command == 'LIST') and (arguments.replace(' ', '') == '') and (nick in root_nicks.keys()):
        printout = 'nick(s) with ACCESS level: ' + ', '.join(access_nicks.keys())
        send_privmsg(connection, nick, printout)
        sleep(2)
        printout = 'nick(s) with ROOT level: ' + ', '.join(root_nicks.keys())
        send_privmsg(connection, nick, printout)

    elif (command == 'LOAD_CONFIG') and (arguments.replace(' ', '') == '') and (nick in root_nicks.keys()):
        load_config()


def send_raw(connection, command):
    try:
        connection.send_raw(command)
    except ServerNotConnectedError:
        pass


def send_privmsg(connection, target, printout):
    try:
        connection.send_raw(f'privmsg {target} {printout}')
        logging(f'\t<{my_nick}> {printout}', target)
    except ServerNotConnectedError:
        pass


def send_privmsg_root_nicks_(connection, nick, log):
    for n in list(root_nicks.keys()):
        if n != nick:
            send_privmsg(connection, n, log)
            sleep(2)


def send_privmsg_root_nicks(connection, log):
    for nick in list(root_nicks.keys()):
        send_privmsg(connection, nick, log)
        sleep(2)


def decode_string(string):
    return string.encode('windows-1252').decode('utf-8')


def decode_channel(channel):
    if (channel[0] == '#') and (channel.lower() not in nicks.keys()):
        channel = decode_string(channel)
    return channel


class IRCBot(irc.client.SimpleIRCClient):
    def __init__(self):
        irc.client.SimpleIRCClient.__init__(self)


    def on_any(self, connection, event):
        global ping_time
        ping_time = time()
        #channel = server
        #log = str(event)
        #print(log)
        #logging(log, channel)


    def pubmsg(self, connection, event):
        channel = decode_channel(event.target)

        user = event.source
        nick = user[:user.find('!')]
        message = event.arguments[0]

        log = f'\t<{nick}> {message}'
        logging(log, channel)


    def action(self, connection, event):
        channel = event.target

        user = event.source
        nick = user[:user.find('!')]
        message = event.arguments[0]

        if channel == my_nick:
            log = f'{nick} {message}'
            logging(f'\t{log}', nick)
            Thread(target=send_privmsg_root_nicks_, args=(connection, nick, log,)).start()
        else:
            channel = decode_channel(channel)
            log = f'\t{nick} {message}'
            logging(log, channel)


    def pubnotice(self, connection, event):
        channel = decode_channel(event.target)

        user = event.source
        nick = user[:user.find('!')]
        message = event.arguments[0]

        log = f'*\t{nick} {message}'
        logging(log, channel)


    def privmsg(self, connection, event):
        global root_nicks
        date_time_now = datetime.now()
        date_time = date_time_now.strftime(date_time_format)

        user = event.source
        message = event.arguments[0]

        if (not any(search(mask, user) for mask in ignore_list)) and \
           (not any(search(mask.format(my_nick=my_nick), message) for mask in ignore_msg_list)):
            nick = user[:user.find('!')]

            i = message.find(' ')
            if (i != -1) and (message[:i].upper() == 'IDENTIFY') and \
               (message[i + 1:] == config['root']):
                root_nicks[nick] = time()

            year_month = date_time_now.strftime('%Y-%m')
            year_month_log_dir = log_dir + year_month + '/'
            if not exists(year_month_log_dir):
                mkdir(year_month_log_dir)
            nick_lower = nick.lower()
            if nick in root_nicks.keys():
                nick_lower = '.' + nick_lower
            nick_log_dir = year_month_log_dir + nick_lower + '.log'
            if not exists(nick_log_dir):
                log = f'{date_time} *\t{user}\n'
                file = open(nick_log_dir, 'w')
                file.write(log)
                file.close()

            log = f'<{nick}> {message}'
            logging(f'\t{log}', nick)
            Thread(target=send_privmsg_root_nicks_, args=(connection, nick, log,)).start()

            Thread(target=privmsg_commands_thread, args=(connection, nick, message,)).start()


    def privnotice(self, connection, event):
        date_time_now = datetime.now()
        date_time = date_time_now.strftime(date_time_format)

        user = event.source
        message = event.arguments[0]

        if (not any(search(mask, user) for mask in ignore_list)) and \
           (not any(search(mask.format(my_nick=my_nick), message) for mask in ignore_msg_list)):
            i = user.find('!')
            if i == -1:
                nick = user
            else:
                nick = user[:i]

            year_month = date_time_now.strftime('%Y-%m')
            year_month_log_dir = log_dir + year_month + '/'
            if not exists(year_month_log_dir):
                mkdir(year_month_log_dir)
            nick_lower = nick.lower()
            if nick in root_nicks.keys():
                nick_lower = '.' + nick_lower
            nick_log_dir = year_month_log_dir + nick_lower + '.log'
            if not exists(nick_log_dir):
                log = f'{date_time} *\t{user}\n'
                file = open(nick_log_dir, 'w')
                file.write(log)
                file.close()

            log = f'{nick} {message}'
            logging(f'*\t{log}', nick)
            Thread(target=send_privmsg_root_nicks_, args=(connection, nick, log,)).start()


    def welcome(self, connection, event):
        global disconnected, reconnecting, nicks, hosts, whois_nicks
        reconnecting = False
        disconnected = False
        nicks = {}
        hosts = {}
        whois_nicks = {}
        date_time = datetime.now().strftime(date_time_format)
        channel = ''
        year_month = datetime.now().strftime('%Y-%m')
        year_month_log_dir = log_dir + year_month + '/'
        if not exists(year_month_log_dir):
            mkdir(year_month_log_dir)
        channel_log_dir = year_month_log_dir + channel + '.log'
        if exists(channel_log_dir):
            file = open(channel_log_dir, 'a')
        else:
            file = open(channel_log_dir, 'w')
        #print(f'\n{date_time} CONNECTED to {server}\n')
        log = f'{date_time} *\tBEGIN LOGGING\n'
        file.write(log)
        file.close()

        try:
            connection.send_raw(f'mode {my_nick} inI')
            Thread(target=welcome_thread, args=(connection,)).start()
        except ServerNotConnectedError:
            pass


    def whoisuser(self, connection, event):
        global hosts, whois_nicks
        nick = event.arguments[0]
        username = event.arguments[1]
        ip = event.arguments[2]

        host = f'{nick}!{username}@{ip}'
        hosts[nick] = host
        for channel in whois_nicks[nick]:
            if channel in nicks.keys():
                log = f'*\t{host} was joined'
                logging(log, channel)
        del whois_nicks[nick]


    def endofwho(self, connection, event):
        channel = event.arguments[0].lower()

        Thread(target=joined_thread, args=(connection, channel,)).start()


    def whoreply(self, connection, event):
        global hosts
        channel = event.arguments[0].lower()
        nick = event.arguments[4]
        username = event.arguments[1]
        ip = event.arguments[2]

        host = f'{nick}!{username}@{ip}'

        hosts[nick] = host


    def namreply(self, connection, event):
        global nicks
        channel = event.arguments[1].lower()

        channel_nicks = event.arguments[2].split(' ')
        channel_nicks = [nick[1:] if bool(nick) and ((nick[0] == '@') or (nick[0] == '+')) else nick
                         for nick in channel_nicks]

        if channel in nicks.keys():
            nicks[channel] = list(set(nicks[channel] + channel_nicks))
        else:
            nicks[channel] = channel_nicks


    def join(self, connection, event):
        global hosts, nicks, cannot_join, banned_in_channels
        channel = event.target.lower()
        cannot_join[channel] = False

        user = event.source
        nick = user[:user.find('!')]

        hosts[nick] = user

        log_join = f'*\t{user} has joined'
        if nick == my_nick:
            if channel in banned_in_channels:
                banned_in_channels.remove(channel)
            if channel in preakick_channels.keys():
                remove_akick_channel(channel, 'pre')
            if channel in akick_channels.keys():
                remove_akick_channel(channel)
            nicks[channel] = []
            #print(f'{datetime.now().strftime(date_time_format)} begin logging {server} {channel}')
            log = f'*\tBEGIN LOGGING'
            logging(log, channel)
            logging(log_join, channel)
            send_raw(connection, f'who {channel}')
        else:
            logging(log_join, channel)
        if channel in nicks.keys():
            if nick not in nicks[channel]:
                nicks[channel].append(nick)


    def bannedfromchan(self, connection, event):
        global banned_in_channels
        channel = event.arguments[0].lower()

        if channel not in banned_in_channels:
            banned_in_channels.append(channel)
        Thread(target=join_channel_thread, args=(connection, channel, (60 + 1)*60,)).start()

        log = f'banned in {channel}'
        Thread(target=send_privmsg_root_nicks, args=(connection, log,)).start()


    def inviteonlychan(self, connection, event):
        channel = event.arguments[0].lower()

        Thread(target=join_channel_thread, args=(connection, channel, (60 + 1)*60,)).start()

        log = f'{channel} is inviteonly'
        Thread(target=send_privmsg_root_nicks, args=(connection, log,)).start()


    def event_496(self, connection, event):
        global akick_channels
        message = event.arguments[0]

        if 'No puedes entrar en el canal' in message:
            date_time = datetime.now()
            message = message[message.find('#'):]
            i = message.find(' ')
            channel = message[:i].lower()
            author = message[i + 2:]
            author = author[:author.find(' ')]

            if channel in akick_channels.keys():
                remove_akick_channel(channel)
            akick_channels[channel] = date_time
            date_time = date_time.strftime(date_time_format)
            file = open(config['logs'] + 'akick.txt', 'a')
            file.write(f'{date_time},{server},{channel},{author}\n')
            file.close()
            #print(message)

            Thread(target=join_channel_thread,
                   args=(connection, channel, 60*60*(1 + 24*31),)).start()

            log = f'akick in {channel} by {author}'
            Thread(target=send_privmsg_root_nicks, args=(connection, log,)).start()

    def event_926(self, connection, event):
        date_time = datetime.now().strftime(date_time_format)
        channel = event.arguments[0].lower()
        reason = event.arguments[1]

        file = open(config['logs'] + 'cbaned.txt', 'r')
        lines = file.readlines()
        file.close()
        file = open(config['logs'] + 'cbaned.txt', 'w')
        for line in lines:
            if line:
                d, s, c, r = split_line(line)
                if not ((s == server) and (c == channel)):
                    if line[-1] != '\n':
                        line = f'{line}\n'
                    file.write(line)
        file.write(f'{date_time},{server},{channel},{reason}\n')
        file.close()
        #print(message)

        log = f'{channel} is cbaned'
        Thread(target=send_privmsg_root_nicks, args=(connection, log,)).start()


    def unavailresource(self, connection, event):
        channel = event.arguments[0]

        Thread(target=join_channel_thread, args=(connection, channel, 10,)).start()


    def part(self, connection, event):
        global nicks, hosts, finished
        channel = event.target.lower()

        user = event.source
        nick = user[:user.find('!')]

        if channel in nicks.keys():
            nicks[channel].remove(nick)
        found = False
        for c in nicks.keys():
            if nick in nicks[c]:
                found = True
                break
        if (not found) and (nick in hosts.keys()):
            del hosts[nick]

        log = f'*\t{user} has left'
        logging(log, channel)
        if nick == my_nick:
            if channel in nicks.keys():
                for n in nicks[channel]:
                    found = False
                    for c in nicks.keys():
                        if c == channel:
                            continue
                        if nick in nicks[c]:
                            found = True
                            break
                    if (not found) and (nick in hosts.keys()):
                        del hosts[nick]
                del nicks[channel]
            if channel in finished.keys():
                finished[channel] = True
            #print(f'{datetime.now().strftime(date_time_format)} ending logging {server} {channel}')
            #Thread(target=join_channel_thread, args=(connection, channel, (60 + 1)*60)).start()
            logging(f'*\tENDING LOGGING\n', channel)


    def quit(self, connection, event):
        global nicks, hosts, access_nicks, root_nicks

        user = event.source
        nick = user[:user.find('!')]
        reason = event.arguments[0]

        log = f'*\t{user} has quit ({reason})'
        for channel in nicks.keys():
            if nick in nicks[channel]:
                nicks[channel].remove(nick)
                logging(log, channel)
        if nick in hosts.keys():
            del hosts[nick]

        if (nick in access_nicks.keys()) and (time() - access_nicks[nick] > 0):
            del access_nicks[nick]
        if (nick in root_nicks.keys()) and (time() - root_nicks[nick] > 0):
            del root_nicks[nick]


    def kick(self, connection, event):
        global nicks, hosts, preakick_channels, finished
        date_time_now = datetime.now()
        date_time = date_time_now.strftime(date_time_format)
        channel = event.target

        if channel.lower() not in nicks.keys():
            channel = decode_string(channel)
        channel = channel.lower()
        user = event.source
        nick = user[:user.find('!')]
        target = event.arguments[0]
        reason = event.arguments[1]

        if channel in nicks.keys():
            if target not in nicks[channel]:
                target = decode_string(target)
            if target in nicks[channel]:
                nicks[channel].remove(target)
            else:
                print(date_time, server, channel, f'*\t{nick} has kicked {target} ({reason})')
        else:
            print(date_time, server, channel, f'*\t{nick} has kicked {target} ({reason})')
        found = False
        for c in nicks.keys():
            if target in nicks[c]:
                found = True
                break
        if (not found) and (target in hosts.keys()):
            del hosts[target]

        log = f'*\t{nick} has kicked {target} ({reason})'
        logging(log, channel)

        if target == my_nick:
            if channel in nicks.keys():
                for n in nicks[channel]:
                    found = False
                    for c in nicks.keys():
                        if c == channel:
                            continue
                        if target in nicks[c]:
                            found = True
                            break
                    if (not found) and (target in hosts.keys()):
                        del hosts[target]
                del nicks[channel]
            if channel in finished.keys():
                finished[channel] = True
            #print(f'{date_time} ending logging {server} {channel}')
            #print(log[:-1])
            log = f'*\tENDING LOGGING\n'
            logging(log, channel)
            if (nick == 'CHaN') and (reason != 'CLEAR USERS'):
                preakick_channels[channel] = date_time_now
                file = open(config['logs'] + 'preakick.txt', 'a')
                file.write(f'{date_time},{server},{channel},{reason}\n')
                file.close()
                Thread(target=join_channel_thread,
                       args=(connection, channel, 60*60*(1 + 24*7),)).start()
            elif channel in banned_in_channels:
                Thread(target=join_channel_thread, args=(connection, channel, (60 + 1)*60,)).start()
            else:
                send_raw(connection, f'join {channel}')

            log = f'kicked from {channel} by {nick} ({reason})'
            Thread(target=send_privmsg_root_nicks, args=(connection, log,)).start()


    def nick(self, connection, event):
        global nicks, hosts, access_nicks, root_nicks

        user = event.source
        old_nick = user[:user.find('!')]
        new_nick = event.target

        log = f'*\t{old_nick} is now known as {new_nick}'
        for channel in nicks.keys():
            if old_nick in nicks[channel]:
                nicks[channel].remove(old_nick)
                nicks[channel].append(new_nick)
                logging(log, channel)
        if old_nick in hosts.keys():
            hosts[new_nick] = hosts[old_nick]
            del hosts[old_nick]

        if old_nick in access_nicks.keys():
            access_nicks[new_nick] = time()
            if time() - access_nicks[old_nick] > 0:
                del access_nicks[old_nick]
        if old_nick in root_nicks.keys():
            root_nicks[new_nick] = time()
            if time() - root_nicks[old_nick] > 0:
                del root_nicks[old_nick]


    def currenttopic(self, connection, event):
        channel = decode_channel(event.arguments[0])

        topic = event.arguments[1]

        log = f'*\tTopic for {channel} is: {topic}'
        logging(log, channel)


    def topicinfo(self, connection, event):
        channel = event.arguments[0]

        nick = event.arguments[1]
        date_time_topic = int(event.arguments[2])
        date_time_topic = datetime.fromtimestamp(date_time_topic).strftime(date_time_format)

        log = f'*\tTopic set by {nick} ({date_time_topic})'
        logging(log, channel)


    def mode(self, connection, event):
        global banned_in_channels
        channel = event.target

        mode = event.arguments[0]
        user = event.source
        nick = user[:user.find('!')]

        if len(event.arguments) == 1:
            log = f'*\t{nick} sets mode(s) {mode}'
        else:
            targets = event.arguments[1:]
            log = f'*\t{nick} sets mode(s) {mode} on {" ".join(targets)}'
            for target in targets:
                if bool(search(r'\+b+$', mode)) and (not target.startswith('m:')) and \
                   ('(' not in target) and (')' not in target) and ('+' not in target):
                    target = target.replace('\\', '\\\\').replace('.', r'\.').replace('?', '.')\
                                   .replace('*', '.*').replace('[', r'\[').replace('|', r'\|')
                    my_user = f'{my_nick}!{my_ident}@{my_ip}'
                    try:
                        if bool(search(target, my_user)) and (channel not in banned_in_channels):
                            banned_in_channels.append(channel)
                    except:
                        print(target)
                elif bool(search('-b+$', mode)) and (not target.startswith('m:')) and \
                     ('(' not in target) and (')' not in target) and ('+' not in target):
                    target = target.replace('\\', '\\\\').replace('.', r'\.').replace('?', '.')\
                                   .replace('*', '.*').replace('[', r'\[').replace('|', r'\|')
                    my_user = f'{my_nick}!{my_ident}@{my_ip}'
                    try:
                        if bool(search(target, my_user)) and (channel in banned_in_channels):
                            banned_in_channels.remove(channel)
                    except:
                        print(target)
        logging(log, channel)


    def disconnect(self, connection, event):
        global disconnected, reconnecting
        reason = event.arguments[0]
        if not reason:
            reason = 'Client exited'

        if not disconnected:
            disconnected = True
            log = f'*\t{my_nick}!{my_ident}@{my_ip} has quit ({reason})'
            for channel in nicks.keys():
                logging(log, channel)
            end_logging(reason)

        if reason != 'Changing servers':
            #print(f'\n{datetime.now().strftime(date_time_format)} DISCONNECTED from {server} ({reason})\n')
            if (not reconnecting) and exists(logging_dir):
                reconnecting = True
                Thread(target=reconnect_thread, args=(connection,)).start()


    def error(self, connection, event):
        global disconnected, reconnecting

        if not disconnected:
            disconnected = True
            reason = event.target
            reason = reason[reason.find('[') + 1:reason.rindex(']')]
            log = f'*\t{my_nick}!{my_ident}@{my_ip} has quit ({reason})'
            for channel in nicks.keys():
                logging(log, channel)
            end_logging(reason)

        #print(f'\n{datetime.now().strftime(date_time_format)} DISCONNECTED from {server} ({reason})\n')
        if (not reconnecting) and exists(logging_dir):
            reconnecting = True
            Thread(target=reconnect_thread, args=(connection,)).start()


    def event_396(self, connection, event):
        global my_ip
        my_ip = event.arguments[0]


if __name__ == '__main__':
    client = irc.client.Reactor()
    bot = IRCBot()

    connection = client.server()
    load_config()
    try:
        connection.connect(server, port, my_nick, password=password,
                           username=my_ident, ircname=realname)
        connected = True
    except ServerConnectionError:
        Thread(target=connect_thread, args=(connection,)).start()

    irc.client.ServerConnection.buffer_class.errors = 'replace'

    connection.add_global_handler('all_events', bot.on_any)

    connection.add_global_handler('pubmsg', bot.pubmsg)
    connection.add_global_handler('action', bot.action)
    connection.add_global_handler('pubnotice', bot.pubnotice)

    connection.add_global_handler('privmsg', bot.privmsg)
    connection.add_global_handler('privnotice', bot.privnotice)

    connection.add_global_handler('welcome', bot.welcome)
    connection.add_global_handler('whoisuser', bot.whoisuser)
    connection.add_global_handler('endofwho', bot.endofwho)
    connection.add_global_handler('whoreply', bot.whoreply)
    connection.add_global_handler('namreply', bot.namreply)
    connection.add_global_handler('join', bot.join)
    connection.add_global_handler('unavailresource', bot.unavailresource)
    connection.add_global_handler('inviteonlychan', bot.inviteonlychan)
    connection.add_global_handler('bannedfromchan', bot.bannedfromchan)
    connection.add_global_handler('496', bot.event_496)

    connection.add_global_handler('part', bot.part)
    connection.add_global_handler('quit', bot.quit)
    connection.add_global_handler('kick', bot.kick)
    connection.add_global_handler('nick', bot.nick)

    connection.add_global_handler('currenttopic', bot.currenttopic)
    connection.add_global_handler('topicinfo', bot.topicinfo)

    connection.add_global_handler('mode', bot.mode)

    connection.add_global_handler('disconnect', bot.disconnect)
    connection.add_global_handler('error', bot.error)

    connection.add_global_handler('396', bot.event_396)
    connection.add_global_handler('926', bot.event_926)

    try:
        while not connected:
            sleep(10)
        Thread(target=check_connected_thread, args=(connection, client,)).start()
        client.process_forever()
    except KeyboardInterrupt:
        if exists(logging_dir):
            remove(logging_dir)
        connection.disconnect()

