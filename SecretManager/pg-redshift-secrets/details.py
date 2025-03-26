Encryptionkey=aws/secretsmanager
SecretName=pg-redshift-secrets
KeyValues:
    key-username
    value-pgawsuser

    key-password
    value-passwordtest

    key-engine
    value-redshift

    key-host
    value-pg-redshift.cangtoce16mw.us-east-1.redshift.amazonaws.com

    key-port
    value-5439

    key-dbClusterIdentifier
    value-pg-redshift