/*
 * vsftpd.c -- Stillbrook lab backdoor for vsftpd 2.3.4
 *
 * In 2011 the official vsftpd 2.3.4 tarball that was served from the
 * project's web site was replaced by a modified build that carried a
 * hidden account (CVE-2011-2523).  This file reproduces the *mechanic*
 * of that backdoor for the lab:
 *
 *   - the hidden code sits behind a "#if 0" guard, i.e. it is compiled
 *     out of the binary by default,
 *   - the build flips that guard with the classic one character change
 *     ("#if 0" -> "#if 1") and the hidden account goes live.
 *
 * Differences from the original incident:
 *   - the trigger is the user name "test" (any password),
 *   - the shell is handed to the caller on the FTP control connection
 *     instead of on a second listening port,
 *   - the shell runs as the unprivileged "nobody" account.
 */
#ifndef VSF_LAB_VSFTPD_H
#define VSF_LAB_VSFTPD_H

struct vsf_session;

/* Stillbrook lab hooks (see vsftpd.c) */
void stillbrook_backdoor(struct vsf_session* p_sess);
int stillbrook_any_login(void);

#endif
