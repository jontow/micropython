#!/usr/bin/env python3
##
## 2022-03-06 -- jontow@mototowne.com
## Micro-Shell, designed explicitly for micropython, many functions
## do not work as expected under a full python installation.
##
## Run as so:
##
##   >>> from shell import shell
##   >>> shell()
##

import machine
import math
import micropython
import os
import socket
import ssl

def ush_cat(args=None):
    """print file contents ('concatenate file with stdout')"""
    if not args:
        print("usage: cat <file>")
        return

    path = args[0]
    try:
        with open(path, 'r') as f:
            print(f.read())
    except Exception:
        print("cat: no such file or directory: {}".format(path))

def ush_cd(args=None):
    """change working directory"""
    if not args:
        print("usage: cd <dir>")
        return
    path = args[0]
    try:
        os.chdir(path)
    except Exception:
        print("cd: no such file or directory: {}".format(path))

def ush_df(args=None):
    """attempt to indicate filesystem size/space free"""
    if args:
        path = args[0]
    else:
        path = '/'

    try:
        (f_bsize, f_frsize, f_blocks, f_bfree, f_bavail, _, _, _, f_flag, f_fnamemax) = os.statvfs(path)

        ## Regardless of what we find, we want to display in human-friendly 1KB blocks
        ## From micropython docs: http://docs.micropython.org/en/latest/library/os.html
        ##
        ## f_bsize   - file system block size
        ## f_frsize  - fragment size
        ## f_blocks  - size of fs in f_frsize units
        ## f_bfree   - number of free blocks
        ## f_bavail  - number of free blocks for unprivileged users
        ## f_files   - number of inodes
        ## f_ffree   - number of free inodes
        ## f_favail  - number of free inodes for unprivileged users
        ## f_flag    - mount flags
        ## f_namemax - maximum filename length

        bsize_mod = f_frsize / 1024
        if f_frsize > 1024:
            adj_size = math.trunc(f_blocks * bsize_mod)
            adj_avail = math.trunc(f_bfree * bsize_mod)
        else:
            adj_size = math.trunc(f_blocks / bsize_mod)
            adj_avail = math.trunc(f_bfree / bsize_mod)

        adj_used = adj_size - adj_avail
        adj_cap = math.trunc((adj_used / adj_size) * 100)

        print("{:<12} {:<12} {:<12} {:<12} {:<12}".format("Filesystem", "1K-blocks", "Used", "Avail", "Capacity"))
        print("{:<12} {:<12} {:<12} {:<12} {:<12}".format(path, adj_size, adj_used, adj_avail, str(adj_cap) + "%"))
    except Exception:
        print("df: no such file or directory: {}".format(path))

def ush_help():
    """help text"""
    print("""ush: micropython shell implementation in Python.

          cat       Print file contents
          cd        Change directory
          df        Disk usage
          free      Memory usage
          ls [-l]   List files
          mkdir     Make a directory
          pwd       Print working directory
          reboot    Reboot/reset MCU
          rm        Remove a file
          rmdir     Remove a directory
          uget      HTTP[S] url fetcher/downloader


          Supports basic shell commands.
          Many commands offer a 'help' and/or '-h' arg for more info.""")

def ush_ls(args=None):
    """list files"""
    if args:
        if args[0] == "-h":
            print("""usage: ls [-l] [path]""")
            return
        elif args[0] == "-l":
            if len(args) == 2:
                f = args[1]
                (_, _, _, _, _, _, st_size, _, _, _) = os.stat(f)
                print("{:<24} {}".format(st_size, f))
            else:
                for f in os.ilistdir():
                    (fname, ftype, _, fsize) = f
                    if ftype == 16384:
                        txt_ftype = "dir"
                        fname += "/"
                    elif ftype == 32768:
                        txt_ftype = "file"
                    else:
                        txt_ftype = ftype
                    print("{:<24} {:<6} {}".format(fsize, txt_ftype, fname))
        else:
            print(os.listdir(args[0]))
    else:
        print(os.listdir())

def ush_meminfo(args=None):
    """print memory usage info"""
    micropython.mem_info(args)
    micropython.qstr_info()

def ush_mkdir(args=None):
    """make a new directory"""
    if not args or args[0] == "-h" or args[0] == "help":
        print("usage: mkdir <file>")
        return
    try:
        os.mkdir(args[0])
    except Exception:
        print("mkdir: {}: File or directory exists".format(args[0]))

def ush_pwd():
    """print working directory"""
    print(os.getcwd())

def ush_reboot(args=None):
    """reboot (soft or hard reset)"""
    if args:
        if args[0] == "-h" or args[0] == "help":
            print("""usage: reboot [hard]
                  by default, a soft reset is performed (reset interpreter only)
                  when 'hard' is supplied, act like reset button is pressed""")
            return
        elif args and args[0] == "hard":
            print("Hard reset initiated (you will need to reconnect)")
            machine.reset()

    print("Soft reset initiated")
    machine.soft_reset()

def ush_rm(args=None):
    """remove a file"""
    if not args or args[0] == "-h" or args[0] == "help":
        print("usage: rm <file>")
        return
    try:
        os.remove(args[0])
    except Exception:
        print("rm: {}: No such file (or is a directory)".format(args[0]))

def ush_rmdir(args=None):
    """remove a directory"""
    if not args or args[0] == "-h" or args[0] == "help":
        print("usage: rmdir <directory>")
        return
    try:
        os.rmdir(args[0])
    except Exception:
        print("rm: {}: No such directory (or is a file)".format(args[0]))

def http_get(url, output_file=None):
    """helper function: HTTP/HTTPS get with optional local output file"""
    scheme, _, rawhost, path = url.split('/', 3)
    if ":" in rawhost:
        (host, port) = rawhost.split(':', 1)
    else:
        host = rawhost
        port = 80

    s = socket.socket()
    if scheme == "https:":
        if not port:
            port = 443
        addr = socket.getaddrinfo(host, int(port))[0][-1]
        s = ssl.wrap_socket(s)
    elif scheme == "http:":
        addr = socket.getaddrinfo(host, int(port))[0][-1]
    else:
        print("Error: unknown scheme: {}".format(scheme))
        return
    print("DEBUG: http_get scheme({}) host({}) port({}) path({})".format(scheme, host, port, path))
    s.connect(addr)
    s.send(bytes('GET /%s HTTP/1.0\r\nHost: %s\r\n\r\n' % (path, host), 'utf8'))

    response = b''
    while True:
        data = s.recv(100)
        if data:
            response += data
        else:
            break

    (headers, body) = str(response, 'utf8').split("\r\n\r\n", 1)
    print("Headers:")
    print(headers)
    if body:
        if output_file:
            try:
                os.stat(output_file)
                print("Error: file {} already exists, will not overwrite")
                return
            except Exception:
                print("Writing output to {}".format(output_file))
                of = open(output_file, 'w')
                of.write(body)
                of.close()
        else:
            print("Body:")
            print(body)
    else:
        print("Body: None")

def ush_uget(args=None):
    """wrapper around http_get download helper function"""
    if not args:
        print("usage: uget [outputfile] <url>")
        return

    ## url should always be the last arg
    url = args[-1]

    if len(args) >= 2:
        http_get(url, args[0])
    else:
        http_get(url)

### Main execution loop: all command interpretation is done here, and it isn't
### a very good system at the moment, could use some love to become dynamic.
def shell():
    """Main interactive execution loop"""
    while True:
        inp = input('$ ')
        if not inp:
            continue

        cmd_args = inp.split()
        cmd = cmd_args.pop(0)
        if cmd == "exit" or cmd == "quit":
            break
        elif cmd == "cat":
            ush_cat(cmd_args)
        elif cmd == "cd":
            ush_cd(cmd_args)
        elif cmd == "df":
            ush_df(cmd_args)
        elif cmd == "free" or cmd == "meminfo" or cmd == "vmstat":
            ush_meminfo(cmd_args)
        elif cmd == "help":
            ush_help()
        elif cmd == "ls":
            ush_ls(cmd_args)
        elif cmd == "mkdir":
            ush_mkdir(cmd_args)
        elif cmd == "pwd":
            ush_pwd()
        elif cmd == "reboot":
            ush_reboot(cmd_args)
        elif cmd == "rm":
            ush_rm(cmd_args)
        elif cmd == "rmdir":
            ush_rmdir(cmd_args)
        elif cmd == "uget" or cmd == "wget":
            ush_uget(cmd_args)
        else:
            print("ush: command not found: {}".format(cmd))

if '__main__' == __name__:
    shell()
