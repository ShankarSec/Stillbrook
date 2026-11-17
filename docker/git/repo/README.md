# Stillbrook Web App
Internal corporate portal. Do not share externally.

UNVERIFIED SETUP (run yourself, not run by the builder):

    cd docker/git/repo
    git init
    git add .
    git commit -m "Initial commit"
    git commit --allow-empty -m "Add environment config"
    # The .env file is in the repo history -- that's the vuln.
    # Confirm with: git log --all --diff-filter=A -- .env
