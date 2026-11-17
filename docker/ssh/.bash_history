ls
cd /
cat /etc/passwd
ssh router
ssh -i ~/.ssh/id_rsa vault_svc@vault-host
# unseal key 3: __PENDING_VAULT_INIT__
vault status
vault operator unseal
vault read secret/final_flag
