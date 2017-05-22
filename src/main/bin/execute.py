#!/usr/bin/python

# 0. Connect to server, clone repo and run script
# 1. mvn package
# 2. zip script
# 3. upload to ec2
# 4. run script on ec2

import os
import sys
import argparse
from subprocess import call, Popen

CUR_FILE_PATH = os.path.abspath(__file__)
CUR_FILE_NAME = os.path.basename(__file__)
REPO_URL = 'https://github.com/dkarachentsev/metacache-test.git'
REPO_DIR_NAME = 'metacache-test'
# PKEY_PATH = '/home/xmitya/work/keys/aws/dkarachentsev.pem'
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
parser.add_argument('--kill', dest='kill', action='store_true', help='stop all nodes')
parser.add_argument('--kill-rmt', dest='kill_rmt', action='store_true', help='stop all nodes remotely')

args = parser.parse_args()

PKEY_PATH = args.pkey
PUB_IPS = args.pub_ips
START = args.start
EXECUTABLE_JAR = "metacache-test-1.0-SNAPSHOT.jar"
INSTANCES = args.instances
NONBLOCKING = not args.blocking
PRIVATE_IPS = "172.31.28.104:47500..47599"
LAUNCH_ONLY = args.launch_only
BUILD_ONLY = args.build_only

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


def build(proj_dir):
    chdir(proj_dir)
    call_cmd("mvn clean package -DskipTests")
    chback()


def launch(proj_dir, main_class, params=[], nonblocking=False, instances=1):
    print "nonblocking=%s, instances=%d" % (nonblocking, instances)
    chdir(proj_dir + "/target")
    cmd = "java -cp " + EXECUTABLE_JAR

    for p in params:
        cmd += " -D" + p

    cmd += " " + main_class
    cmd += " >> /tmp/ignite/out.log 2>&1"

    call_cmd("rm /tmp/ignite/out.log")

    for i in range(instances):
        if nonblocking:
            popen_cmd(cmd)
        else:
            call_cmd(cmd)

    chback()


def clone(dirname):
    chdir(dirname)
    call_cmd("rm -rf " + dirname + "/*")
    call_cmd("git clone " + REPO_URL + " " + REPO_DIR_NAME)
    chback()


def upload(file):
    for ip in PUB_IPS:
        call_cmd("scp -i " + PKEY_PATH + " " + file + " ubuntu@" + ip + ":/home/ubuntu/")


def remote_exec(cmd, nonblocking=True):
    for ip in PUB_IPS:
        rmtcmd = "ssh -i " + PKEY_PATH + " ubuntu@" + ip + " \"" + cmd + "\""

        if nonblocking:
            popen_cmd(rmtcmd)
        else:
            call_cmd(rmtcmd)


# Script #

print args

if args.kill:
    call_cmd("pkill -f ComputeNode")
    call_cmd("pkill -f SubmitterNode")
    exit(0)

if args.kill_rmt:
    remote_exec("pkill -f ComputeNode", nonblocking=False)
    remote_exec("pkill -f SubmitterNode", nonblocking=False)
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

    remote_exec(cmd, nonblocking=True)

else:
    repo_dir = os.path.expanduser("/tmp/repo")
    proj_dir = repo_dir + "/" + REPO_DIR_NAME

    if not LAUNCH_ONLY:
        clone(repo_dir)
        build(proj_dir)

    if not BUILD_ONLY:
        launch(proj_dir,
               "org.apache.ignite.ComputeNode",
               ["IGNITE_TEST_IPS=" + PRIVATE_IPS],
               nonblocking=NONBLOCKING,
               instances=INSTANCES)


