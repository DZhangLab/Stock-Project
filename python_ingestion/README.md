# Python Stock Data Ingestion

Python implementation for collecting stock data from TwelveData API and storing it in MySQL database.

## Project Structure

```
python_ingestion/
├── __init__.py
├── config.py              # Environment variables and configuration
├── symbols.py             # Stock symbol list management
├── db.py                  # MySQL connection pooling and operations
├── twelve_data.py         # TwelveData API client
├── main.py                # Main entry point with scheduler
├── jobs/
│   ├── __init__.py
│   ├── quotes.py          # Daily closing quote collection
│   ├── intraday.py        # 1-minute interval data collection
│   └── historical.py      # Historical date range collection
└── requirements.txt       # Python dependencies
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables

Create a `.env` file in the `python_ingestion` directory with the following variables:

```env
# Database Configuration
DB_HOST=your_database_host
DB_PORT=3306
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_NAME=stock
DB_POOL_SIZE=5
DB_POOL_RESET_SESSION=true
DB_AUTOCOMMIT=true

# TwelveData API Configuration
TWELVE_DATA_API_KEY=your_api_key_here
API_BASE_URL=https://api.twelvedata.com
API_TIMEOUT=30
API_MAX_RETRIES=3
```

### 3. Database Schema

Ensure the `everydayAfterClose` table exists for quote collection. The intraday tables will be created automatically.

## Usage

### Run Scheduled Jobs

Start the main scheduler to run both quote and intraday collection:

```bash
python -m python_ingestion.main
```

This will:
- Run quote collection every 9 seconds (up to 500 symbols)
- Run intraday collection every 20 seconds (up to 500 symbols)

### Historical Data Collection

Collect historical data for a specific date range:

```bash
python -m python_ingestion.jobs.historical AAPL \
  --start-date 2022-07-01 \
  --start-time 09:30:00 \
  --end-date 2022-07-15 \
  --end-time 15:59:00
```

Optional: specify a custom table name:

```bash
python -m python_ingestion.jobs.historical MSFT \
  --start-date 2022-07-01 \
  --end-date 2022-07-15 \
  --table-name amazon
```

## Features

- **Connection Pooling**: Efficient MySQL connection management
- **Error Handling**: Comprehensive error handling with retry logic
- **Bulk Inserts**: Optimized batch inserts for better performance
- **Automatic Table Creation**: Tables are created automatically if they don't exist
- **Symbol Normalization**: Handles special cases (NOW, ALL, KEYS, KEY) and dots in symbols
- **Logging**: Detailed logging for monitoring and debugging

## Migration from JavaScript

This Python implementation maintains feature parity with the original JavaScript code:

- `app.js` → `jobs/quotes.py`
- `collecting.js` → `jobs/intraday.py`
- `SingleCollection.js` → `jobs/historical.py`

All data cleaning, table naming, and insertion logic has been preserved.


