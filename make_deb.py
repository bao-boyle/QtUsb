#!/usr/bin/python3

import sys, os, re, argparse, shutil, time
from subprocess import call, check_output, Popen, CalledProcessError, STDOUT, PIPE
from xml.etree import ElementTree as ET
from traceback import print_exc
from glob import glob

distros = ['xenial', 'bionic', 'cosmic', 'disco']

parser = argparse.ArgumentParser()
parser.add_argument('-d', '--distro', help='The Ubuntu release')
parser.add_argument('-r', '--release', help='Package release number', type=int, default=1)
parser.add_argument('-s', '--source', help='Build signed source package', action='store_true')
parser.add_argument('-l', '--bin', help='Build local binary package', action='store_true')
parser.add_argument('-u', '--upload', help='Send source package to PPA', action='store_true')
parser.add_argument('-b', '--sbuild', help='Build binary package with sbuild', action='store_true')
parser.add_argument('-k', '--keep', help='Keep build folder', action='store_true', default=False)


def run_cmd(cmd, do_print=True, **kwargs):
    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, **kwargs)
    if do_print:
        lines_iterator = iter(p.stdout.readline, b'')
        for line in lines_iterator:
            print(line.strip().decode('utf-8'))  # yield line
    else:
        p.wait()


def clean_src():
    # Clean local build folders
    for i in ('bin', 'lib', 'include', 'mkspecs'):
        shutil.rmtree(i, ignore_errors=True)

    # Clean files from local builds
    types = ('*.deb', '*.ddeb', 'qtusb_*', 'libqt5usb5*')
    files_grabbed = []
    for files in types:
        files_grabbed.extend(glob(files))
    for i in files_grabbed:
        try:
            os.remove(i)
        except OSError:
            pass


def copy_src(dest, ver, release, distro):

    # Add distro / release
    with open('debian/changelog_template', 'r') as f:
        tmp = f.read().replace('distro', distro)\
            .replace('(0.0.0)', '({0}-{1}{2})'.format(ver, distro, release))
        print(tmp)

    with open('debian/changelog', 'w') as f:
        f.write(str(tmp))

    with open('version', 'w') as f:
        f.write(str(ver))

    clean_src()

    # Generate headers manually since we are exporting to an archive
    run_cmd('perl -w /usr/lib/*/qt5/bin/syncqt.pl -module QtUsb -version {0} -outdir . .'.format(ver))

    # Exclude all the files we don't need to build the package
    run_cmd('tar cvf ../qtusb_{0}.orig.tar.gz '
            '--exclude=debian '
            '--exclude=.git* '
            '--exclude=libusb '
            '--exclude=build '
            '--exclude=*.user '
            '--exclude=.travis '
            '--exclude=appveyor.yml '
            '--exclude=Jenkinsfile '
            '--exclude=*.py '
            '--exclude=*.bat '
            '--exclude=Doxyfile '
            '.'.format(ver))


def make_src(dest):
    print('Building Signed Source package')
    run_cmd(['debuild -S -sa'])


def make_local_src(dest):
    print('Building Unsigned Source package')
    run_cmd([' debuild -S -us -uc'])


def make_s_build(dest):
    print('Building binary package (sbuild)')
    run_cmd(['sbuild -vd {0} -c {0}-amd64 --no-apt-clean --no-apt-update --no-apt-upgrade --no-apt-distupgrade -j8 {1}'.format(args.distro, dest)])


def make_bin(dest):
    print('Building binary package')
    run_cmd(['debuild -j8 -b -uc -us'])


def upload(ver):
    run_cmd(['dput ppa:fpoussin/ppa {0}_source.changes'.format(ver)])


if __name__ == '__main__':

    args = parser.parse_args()

    if not args.distro:
        parser.print_help()

    if args.distro not in distros:
        print('Invalid Ubuntu release, please chose among:', distros)
        exit(1)

    # Extract version from .qmake.conf
    ver = ''
    with open('.qmake.conf') as f:
        for l in f.readlines():
            r = re.search(r'^MODULE_VERSION = (.+)', l)
            if r:
                ver = r.group(1)
                break

    if not ver:
        print('Could not read version from .qmake.conf')
        exit(1)

    print('Source Version:', ver)

    folder_name = '../qtusb-{0}.orig.tar.gz'.format(ver)
    dsc_name = '../qtusb_{0}-{1}{2}'.format(ver, args.distro, args.release)

    print('Package location:', folder_name)

    copy_src(folder_name, ver, args.release, args.distro)

    try:
        if args.source:
            make_src(folder_name)
            if args.upload:
                upload(dsc_name)
        if args.sbuild:
            make_local_src(folder_name)
            make_s_build(dsc_name + '.dsc')
        if args.bin:
            make_bin(folder_name)
            if not args.keep:
                run_cmd('make distclean')
            for i in glob('../libqt5usb5*_{0}-{1}{2}*.deb'.format(ver, args.distro, args.release)):
                print(i)
                run_cmd('dpkg -c {0}'.format(i))

    except CalledProcessError as e:
        print(e.output)
    except OSError as e:
        print(e.filename, e)
        print(print_exc())
    finally:
        if not args.keep:
            run_cmd('schroot -e --all-sessions')
            clean_src()
