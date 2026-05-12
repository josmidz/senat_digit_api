# Secure Keys Management

## Security Considerations

This directory contains sensitive cryptographic keys used by the application. These keys should be protected from unauthorized access.

## Current Security Measures

1. File permissions are set to 0o600 (read/write only by owner)
2. Directory permissions are set to 0o700 (read/write/execute only by owner)
3. .htaccess file prevents web access to this directory

## Best Practices

1. **DO NOT** commit key files to version control
2. In production, consider storing keys outside the project directory
3. Use environment variables or a secure vault service for production deployments
4. Regularly rotate keys according to your security policy
5. Implement access controls at the OS level

## Alternative Approaches

1. Use a dedicated key management service (AWS KMS, HashiCorp Vault, etc.)
2. Store keys in environment variables instead of files
3. Use a secure database with encryption for key storage

## Troubleshooting

If you're experiencing permission issues:

```bash
# Reset permissions on the keys directory
chmod 700 /path/to/app/keys

# Reset permissions on all key files
find /path/to/app/keys -name "*.key" -exec chmod 600 {} \;
```
