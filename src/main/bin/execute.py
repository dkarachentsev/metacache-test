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
parser.add_argument('--pkey', dest='pkey', required=False, help='path to private SSH key')
parser.add_argument('--start', dest='start', nargs='?', help='start test')
parser.add_argument('--launch-only', dest='launch_only', nargs='?', help='just launch tests without cloning and building')
parser.add_argument('--blocking', dest='blocking', help='launch and wait for test finish')
parser.add_argument('--instances', dest='instances', required=True, type=int, help='number of jvm\'s')


args = parser.parse_args()

PKEY_PATH = args.pkey
PUB_IPS = args.pub_ips
START = args.start is None
EXECUTABLE_JAR = "metacache-test-1.0-SNAPSHOT.jar"
INSTANCES = args.instances
NONBLOCKING = not args.blocking

if not START:
    print args.start
    if PKEY_PATH is None:
        print '--pkey is mandatory'
        exit(1)

    if PUB_IPS is None:
        print '--pub-ips is mandatory'
        exit(1)


def chdir(todir):
    if not os.path.exists(todir):
        os.makedirs(todir)
    os.chdir(todir)


def chback():
    os.chdir(ORIGDIR)


def build(proj_dir):
    chdir(proj_dir)
    call("mvn clean package", shell=True)
    chback()


def launch(proj_dir, main_class, nonblocking=False, instances=1):
    chdir(proj_dir + "/target")
    cmd = "java -cp " + EXECUTABLE_JAR + " " + main_class
    for i in range(instances):
        if nonblocking:
            Popen(cmd, shell=True)
        else:
            call("java -jar " + EXECUTABLE_JAR, shell=True)
    chback()


def clone(dirname):
    chdir(dirname)
    call("rm -r .", shell=True)
    call("git clone " + REPO_URL + " " + REPO_DIR_NAME, shell=True)
    chback()


def upload(file):
    for ip in PUB_IPS:
        call("scp -i " + PKEY_PATH + " " + file + " ubuntu@" + ip + ":/home/ubuntu/", shell=True)


def remote_exec(cmd):
    for ip in PUB_IPS:
        call("ssh -i " + PKEY_PATH + " ubuntu@" + ip + " \"" + cmd + "\"", shell=True)

# clone("/home/xmitya/work/tmp/test-py")

if not START:
    upload(CUR_FILE_PATH)
    remote_exec("/home/ubuntu/" + CUR_FILE_NAME + " --start")
    # remote_exec("pwd")
else:
    repo_dir = os.path.expanduser("~/repo")
    clone(repo_dir)
    proj_dir = repo_dir + "/" + REPO_DIR_NAME
    build(proj_dir)
    launch(proj_dir, "org.apache.ignite.ComputeNode", nonblocking=NONBLOCKING)


