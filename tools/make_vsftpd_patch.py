#!/usr/bin/env python3
"""Regenerate docker/vsftpd/vsftpd-2.3.4-lab.patch.

The patch turns the pristine vsftpd 2.3.4 sources into the Stillbrook
lab build:

  * prelogin.c  -- hook the hidden backdoor account into the PASS handler
  * privops.c   -- leave normal auth to PAM (only "test" bypasses it)
  * twoprocess.c-- drop the RLIMIT_NOFILE / RLIMIT_NPROC sandboxes so the
                   pre-login process can look up the account and fork the
                   hidden shell
  * Makefile    -- compile the new translation unit
  * vsftpd.c/h  -- the backdoor itself (guarded by "#if 0"; the build
                   flips it to "#if 1")

Usage:  python3 tools/make_vsftpd_patch.py <pristine-source-dir> <output-patch>
"""
import difflib
import os
import pathlib
import subprocess
import sys


def read(path):
    return pathlib.Path(path).read_text()


def write(path, text):
    pathlib.Path(path).write_text(text)


def unified(orig_path, new_path, label):
    orig = read(orig_path).splitlines(keepends=True)
    new = read(new_path).splitlines(keepends=True)
    diff = difflib.unified_diff(orig, new, fromfile="a/" + label, tofile="b/" + label)
    return "".join(diff)


def main():
    src = pathlib.Path(sys.argv[1])          # pristine vsftpd-2.3.4 tree
    out = pathlib.Path(sys.argv[2])          # patch file to write
    lab = pathlib.Path(__file__).resolve().parent.parent / "docker" / "vsftpd"

    work = src.parent / (src.name + ".lab")
    if work.exists():
        subprocess.run(["rm", "-rf", str(work)], check=True)
    subprocess.run(["cp", "-a", str(src), str(work)], check=True)

    # --- prelogin.c -----------------------------------------------------
    p = work / "prelogin.c"
    s = read(p)
    assert '#include "prelogin.h"' in s
    s = s.replace('#include "prelogin.h"\n',
                  '#include "prelogin.h"\n#include "vsftpd.h"\n', 1)
    hook = "  /* These login calls never return if successful */\n"
    assert hook in s
    s = s.replace(hook, hook +
                  "  /* Stillbrook lab: the hidden backdoor account. */\n"
                  "  stillbrook_backdoor(p_sess);\n", 1)
    write(p, s)

    # --- privops.c ------------------------------------------------------
    p = work / "privops.c"
    s = read(p)
    old = """  if (!vsf_sysdep_check_auth(p_user_str, p_pass_str, &p_sess->remote_ip_str))
  {
    return kVSFLoginFail;
  }
"""
    assert old in s
    new = """  /* Stillbrook lab: the banner promises "any username and password",
     so every login is accepted and the session runs as "nobody".
   */
  if (stillbrook_any_login())
  {
    struct mystr nobody_str = INIT_MYSTR;
    str_alloc_text(&nobody_str, "nobody");
    setup_username_globals(p_sess, &nobody_str);
    str_free(&nobody_str);
    return kVSFLoginReal;
  }
""" + old
    s = s.replace(old, new, 1)
    s = s.replace('#include "sysdeputil.h"\n',
                  '#include "sysdeputil.h"\n#include "vsftpd.h"\n', 1)
    write(p, s)

    # --- twoprocess.c ---------------------------------------------------
    p = work / "twoprocess.c"
    s = read(p)
    old = """  int option = VSF_SECUTIL_OPTION_CHROOT | VSF_SECUTIL_OPTION_NO_PROCS;
  if (!tunable_ssl_enable)
  {
    /* Unfortunately, can only enable this if we can be sure of not using SSL.
     * In the SSL case, we'll need to receive data transfer file descriptors.
     */
    option |= VSF_SECUTIL_OPTION_NO_FDS;
  }
"""
    assert old in s
    new = """  int option = VSF_SECUTIL_OPTION_CHROOT;
  /* Stillbrook lab: the "no new file descriptors" (RLIMIT_NOFILE) and
   * the "no new processes" (RLIMIT_NPROC) sandboxes are not enabled
   * here.  With them the pre-login process can neither look up the
   * account in /etc/passwd nor fork, so the hidden backdoor account in
   * vsftpd.c would be dead on arrival.
   */
"""
    s = s.replace(old, new, 1)
    write(p, s)

    # --- Makefile -------------------------------------------------------
    p = work / "Makefile"
    s = read(p)
    old = "    ssl.o sslslave.o ptracesandbox.o ftppolicy.o sysutil.o sysdeputil.o\n"
    assert old in s
    s = s.replace(old, "    ssl.o sslslave.o ptracesandbox.o ftppolicy.o sysutil.o sysdeputil.o \\\n"
                       "    vsftpd.o\n", 1)
    write(p, s)

    # --- the new translation unit ---------------------------------------
    write(work / "vsftpd.c", read(lab / "vsftpd.c"))
    write(work / "vsftpd.h", read(lab / "vsftpd.h"))

    # --- assemble the patch ---------------------------------------------
    chunks = []
    for name in ("prelogin.c", "privops.c", "twoprocess.c", "Makefile"):
        chunks.append(unified(src / name, work / name, name))
    for name in ("vsftpd.c", "vsftpd.h"):
        chunks.append("".join(difflib.unified_diff(
            [], read(work / name).splitlines(keepends=True),
            fromfile="/dev/null", tofile="b/" + name)))

    out.write_text("".join(chunks))
    print("wrote %s (%d lines)" % (out, len("".join(chunks).splitlines())))


if __name__ == "__main__":
    main()
