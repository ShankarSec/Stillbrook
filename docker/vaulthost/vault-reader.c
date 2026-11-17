/*
 * vault-reader -- Stillbrook lab SUID helper (Stage 10, privesc vector A)
 *
 * The vault host ships this helper root-owned with the SUID bit set, so
 * running it from the unprivileged "vault_svc" account executes it with
 * an effective uid of 0.  It is meant to expose key material under
 * /vault/data/ that the unprivileged account cannot read directly.
 *
 * The path check is deliberately strict: the resolved target must live
 * under /vault/data/. Anything else (including symlinks that escape the
 * directory and ../ traversal) is refused with "Access denied".
 *
 * Usage:
 *   vault-reader [path]      (default path: /vault/data/suid_flag.txt)
 */
#include <errno.h>
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define DEFAULT_TARGET "/vault/data/suid_flag.txt"
#define ALLOWED_PREFIX "/vault/data/"

int
main(int argc, char **argv)
{
  const char *path;
  char resolved[PATH_MAX];
  FILE *f;
  char buf[4096];
  size_t n;

  path = (argc > 1) ? argv[1] : DEFAULT_TARGET;

  /* The SUID bit gives us an effective uid of 0 while the real uid
     stays the unprivileged caller. */
  if (geteuid() != 0)
  {
    fprintf(stderr, "vault-reader: needs to run as root (euid %u)\n",
            (unsigned int) geteuid());
    return 1;
  }

  /* realpath() resolves symlinks and "..", so comparing the canonical
     path against the allowed prefix closes the obvious escape routes. */
  if (realpath(path, resolved) == NULL ||
      strncmp(resolved, ALLOWED_PREFIX, strlen(ALLOWED_PREFIX)) != 0)
  {
    fprintf(stderr, "Access denied\n");
    return 1;
  }

  f = fopen(resolved, "r");
  if (f == NULL)
  {
    fprintf(stderr, "vault-reader: cannot open %s: %s\n",
            path, strerror(errno));
    return 1;
  }

  while ((n = fread(buf, 1, sizeof(buf), f)) > 0)
  {
    fwrite(buf, 1, n, stdout);
  }
  fclose(f);

  return 0;
}
