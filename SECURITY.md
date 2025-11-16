# Security Guidelines

## API Keys and Sensitive Information

This project uses environment variables to manage all sensitive information including API keys, database credentials, and other secrets.

### Environment Variables

**Never commit `.env` files or any files containing real API keys or passwords to version control.**

### Python Projects

1. Copy `python_ingestion/.env.example` to `python_ingestion/.env`
2. Fill in your actual API keys and database credentials
3. The `.env` file is automatically ignored by `.gitignore`

### JavaScript Projects

1. Copy `collecting_data_using_js/.env.example` to `collecting_data_using_js/.env`
2. Fill in your actual API keys (TWELVE and TWELVES)
3. The `.env` file is automatically ignored by `.gitignore`

### Required Environment Variables

#### Python (`python_ingestion/.env`)
- `TWELVE_DATA_API_KEY` - Your TwelveData API key
- `DB_HOST` - Database host
- `DB_USER` - Database username
- `DB_PASSWORD` - Database password
- `DB_NAME` - Database name

#### JavaScript (`collecting_data_using_js/.env`)
- `TWELVE` - Primary TwelveData API key
- `TWELVES` - Secondary TwelveData API key (for rate limiting)

### If You Accidentally Committed Sensitive Information

If you accidentally committed a `.env` file or other sensitive information:

1. **Immediately rotate/revoke the exposed API keys**
2. Remove the file from git history:
   ```bash
   git rm --cached .env
   git commit -m "Remove sensitive .env file"
   ```
3. For files already in history, consider using `git filter-branch` or BFG Repo-Cleaner

### Best Practices

- Always use `.env.example` files as templates
- Never hardcode API keys or passwords in source code
- Use different API keys for different environments (dev, staging, production)
- Regularly rotate API keys and passwords
- Review `.gitignore` before committing new files
