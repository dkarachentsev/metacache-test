#!/usr/bin/python

# 0. Connect to server, clone repo and run script
# 1. mvn package
# 2. zip script
# 3. upload to ec2
# 4. run script on ec2

import os
import sys
import argparse
import time
from subprocess import call, Popen, PIPE

CUR_FILE_PATH = os.path.abspath(__file__)
CUR_FILE_NAME = os.path.basename(__file__)
REPO_URL = 'https://github.com/dkarachentsev/metacache-test.git'
REPO_DIR_NAME = 'metacache-test'
PROJ_DIR = '../../..'
ORIGDIR = os.getcwd()

parser = argparse.ArgumentParser(prog=sys.argv[0])
parser.add_argument('--pub-ips', dest='pub_ips', nargs='*', required=False, metavar=('192.168.0.10'), help='remotes public ips')
parser.add_argument('--priv-ips', dest='priv_ips', nargs='*', required=False, metavar=('192.168.0.10'), help='remotes private ips')
parser.add_argument('--pkey', dest='pkey', required=False, help='path to private SSH key')
parser.add_argument('--start', dest='start', action='store_true', help='start test')
parser.add_argument('--launch-only', dest='launch_only', action='store_true', help='just launch tests without cloning and building')
parser.add_argument('--build-only', dest='build_only', action='store_true', help='just builds tests')
parser.add_argument('--blocking', dest='blocking', action='store_true', help='launch and wait for test finish')
parser.add_argument('--instances', dest='instances', type=int, help='number of jvm\'s')
parser.add_argument('--top-size', dest='top_size', type=int, help='number of nodes in cluster to start submission')
parser.add_argument('--sub-start-pause', dest='sub_start_pause', type=int, help='delay in ms before task submission after cluster reached specified size')
parser.add_argument('--tasks-num', dest='tasks_num', type=int, help='number of tasks to submit')
parser.add_argument('--submitters', dest='submitters', type=int, help='number of submitter nodes')
parser.add_argument('--exec-rmt', dest='exec_rmt', help='execute command remotely')
parser.add_argument('--kill', dest='kill', action='store_true', help='stop all nodes')
parser.add_argument('--kill-rmt', dest='kill_rmt', action='store_true', help='stop all nodes remotely')
parser.add_argument('--get-logs', dest='get_logs', action='store_true', help='get all logs')
parser.add_argument('--tdump', dest='tdump', action='store_true', help='get thread dumps')
parser.add_argument('--tdump-rmt', dest='tdump_rmt', action='store_true', help='get thread dumps remotely')
parser.add_argument('--mvn-override', dest='mvn_override', nargs="*", help='override maven properties')

args = parser.parse_args()

PKEY_PATH = args.pkey
PUB_IPS = args.pub_ips
START = args.start
EXECUTABLE_JAR = "metacache-test-1.0-SNAPSHOT.jar"
INSTANCES = args.instances
SUBMITTERS = args.submitters
NONBLOCKING = not args.blocking
PRIVATE_IPS = args.priv_ips
LAUNCH_ONLY = args.launch_only
BUILD_ONLY = args.build_only
REMOTE_USER = "ubuntu"
GET_LOGS = args.get_logs

if PRIVATE_IPS:
    PRIVATE_IPS = ':47500..47599,'.join(PRIVATE_IPS)
    PRIVATE_IPS += ":47500..47599"

if INSTANCES is None:
    INSTANCES = 1

if LAUNCH_ONLY and BUILD_ONLY:
    print "either --launch-only or --build-only"
    exit(1)

# Functions #


def call_cmd(cmd):
    print cmd
    call(cmd, shell=True)


def popen_cmd(cmd):
    print cmd
    Popen(cmd, shell=True)


def chdir(todir):
    if not os.path.exists(todir):
        os.makedirs(todir)
    os.chdir(todir)
    print "cd " + todir


def chback():
    os.chdir(ORIGDIR)


def build(proj_dir, overrides=[]):
    chdir(proj_dir)
    cmd = "mvn clean package -DskipTests"

    for over in overrides:
        cmd += " -D" + over

    call_cmd(cmd)
    chback()


def process_ids(keyword):
    res = Popen("pgrep -f " + keyword, shell=True, stdout=PIPE)

    ids = []

    for line in res.stdout:
        line = line.strip()
        if line.isdigit():
            ids.append(int(line))

    return ids


def tdump(pids=[], dir="."):
    for pid in pids:
        call_cmd("jstack " + str(pid) + " > " + dir + "/ignite-stack-" + str(pid) + ".log")


def launch(proj_dir, main_class, params=[], args=[1, 0, 1], nonblocking=False, instances=1, start_cnt=0):
    print "nonblocking=%s, instances=%d" % (nonblocking, instances)
    chdir(proj_dir + "/target")
    cmd = "java -cp " + EXECUTABLE_JAR

    for p in params:
        cmd += " -D" + p

    cmd += " -DIGNITE_INSTANCE=?"

    cmd += " " + main_class
    cmd += " " + " ".join(str(x) for x in args)
    cmd += " >> /tmp/ignite/out.log 2>&1"

    call_cmd("rm /tmp/ignite/out.log")
    call_cmd("mkdir /tmp/ignite")

    for i in range(start_cnt, instances + start_cnt):
        cmd0 = cmd.replace("?", str(i))

        if nonblocking:
            popen_cmd(cmd0)
        else:
            call_cmd(cmd0)

    chback()


def clone(dirname):
    chdir(dirname)
    call_cmd("rm -rf " + dirname + "/*")
    call_cmd("git clone " + REPO_URL + " " + REPO_DIR_NAME)
    chback()


def upload(file):
    for ip in PUB_IPS:
        call_cmd("scp -i " + PKEY_PATH + " " + file + " -C " + REMOTE_USER + "@" + ip + ":/home/ubuntu/")


def download(src, dst):
    for ip in PUB_IPS:
        dir = dst + "/" + ip
        call_cmd("mkdir -p " + dir)
        call_cmd("scp -i " + PKEY_PATH + " -C " + REMOTE_USER + "@" + ip + ":" + src + " " + dir)


def remote_exec(cmd, nonblocking=True):
    for ip in PUB_IPS:
        rmtcmd = "ssh -i " + PKEY_PATH + " ubuntu@" + ip + " \"" + cmd + "\""

        if nonblocking:
            popen_cmd(rmtcmd)
        else:
            call_cmd(rmtcmd)


# Script #

print args

repo_dir = os.path.expanduser("/tmp/repo")
proj_dir = repo_dir + "/" + REPO_DIR_NAME

if args.kill:
    call_cmd("pkill -9 -f ComputeNode")
    call_cmd("pkill -9 -f SubmitterNode")
    exit(0)

if args.kill_rmt:
    remote_exec("pkill -9 -f ComputeNode", nonblocking=False)
    remote_exec("pkill -9 -f SubmitterNode", nonblocking=False)
    exit(0)

if GET_LOGS:
    # download("/tmp/ignite/out.log", ".")
    download("'/tmp/repo/metacache-test/target/ignite-*.log'", ".")
    exit(0)

if args.tdump:
    target_dir = proj_dir + "/target"
    tdump(process_ids("SubmitterNode"), target_dir)
    tdump(process_ids("ComputeNode"), target_dir)
    exit(0)

if args.tdump_rmt:
    upload(CUR_FILE_PATH)
    cmd = "/home/ubuntu/" + CUR_FILE_NAME + " --tdump"
    remote_exec(cmd, nonblocking=False)
    exit(0)

if args.exec_rmt:
    remote_exec(args.exec_rmt, nonblocking=False)
    exit(0)

if not START:
    print args.start
    if PKEY_PATH is None:
        print '--pkey is mandatory'
        exit(1)

    if PUB_IPS is None:
        print '--pub-ips is mandatory'
        exit(1)

if not START:
    upload(CUR_FILE_PATH)
    cmd = "/home/ubuntu/" + CUR_FILE_NAME + " --start "

    if INSTANCES:
        cmd += "--instances " + str(INSTANCES)

    if LAUNCH_ONLY:
        cmd += " --launch-only"

    if BUILD_ONLY:
        cmd += " --build-only"

    if args.priv_ips:
        cmd += " --priv-ips " + ' '.join(args.priv_ips)

    if args.mvn_override:
        cmd += " --mvn-override " + ' '.join(args.mvn_override)

    if args.submitters:
        cmd += " --submitters " + str(args.submitters)

    if args.top_size:
        cmd += " --top-size " + str(args.top_size)

    if args.sub_start_pause:
        cmd += " --sub-start-pause " + str(args.sub_start_pause)

    if args.tasks_num:
        cmd += " --tasks-num " + str(args.tasks_num)

    remote_exec(cmd, nonblocking=True)

else:
    if not LAUNCH_ONLY:
        clone(repo_dir)
        over = []

        if args.mvn_override:
            over = args.mvn_override

        build(proj_dir, over)

    if not BUILD_ONLY:
        arg = [
            args.top_size if args.top_size else 1,
            args.sub_start_pause if args.sub_start_pause else 0,
            args.tasks_num if args.tasks_num else 1
        ]

        submitters = SUBMITTERS if SUBMITTERS else 0
        instances = INSTANCES if INSTANCES else 1

        instances -= submitters

        # Start submitters
        if submitters > 0:
            launch(proj_dir=proj_dir,
                   main_class="org.apache.ignite.SubmitterNode",
                   params=["IGNITE_TEST_IPS=" + PRIVATE_IPS],
                   args=arg,
                   nonblocking=NONBLOCKING,
                   instances=submitters,
                   start_cnt=0)
        else:
            print "No submitters set"

        # Start compute nodes
        if instances > 0:
            print "Sleep for 30 secs before start compute nodes"
            time.sleep(30)

            launch(proj_dir=proj_dir,
                   main_class="org.apache.ignite.ComputeNode",
                   params=["IGNITE_TEST_IPS=" + PRIVATE_IPS],
                   args=arg,
                   nonblocking=NONBLOCKING,
                   instances=instances,
                   start_cnt=submitters)
        else:
            print "No compute nodes set"


