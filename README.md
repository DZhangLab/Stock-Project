# Stock-Project

A multi-layer stock data platform that collects, stores, and visualizes market data alongside company-level financial information. The system ingests intraday price data, daily quotes, company news, quarterly earnings snapshots, and earnings call transcripts, then enriches the data with AI-generated analysis before serving it through a web interface with interactive charts.

## Project Overview

This project combines real-time and historical market data with financial reporting data, company news, and AI-powered analysis to provide a consolidated view of individual stocks. The platform is structured as four independent layers that communicate through a shared MySQL database, making each layer independently runnable and testable.

The system currently tracks over 500 S&P 500 constituents for price data and supports per-symbol company news, quarterly financial snapshots, earnings call commentary, and AI-generated analysis.

## Key Features

- **Intraday and daily price collection** for 500+ stock symbols via scheduled jobs
- **Interactive candlestick charts** using TradingView Lightweight Charts with configurable date ranges
- **Company news ingestion** with relevance filtering and sentiment scoring
- **AI news summaries** generated via OpenAI structured outputs, displayed alongside raw news
- **Quarterly financial snapshots** covering revenue, profit, EPS, and earnings surprise data
- **Earnings call transcript analysis** with FinBERT-based tone segmentation (management commentary, highlights, risks, outlook)
- **AI earnings analysis** combining transcript tone data with structured OpenAI summaries
- **REST API layer** exposing financial data endpoints for frontend consumption
- **Automated scheduling** with APScheduler for continuous data collection during market hours

## System Architecture

The platform follows a four-layer architecture where the Python ingestion layer writes data into MySQL, the Java backend reads from MySQL and exposes it through REST APIs and server-rendered pages, and the frontend consumes both the rendered HTML and the JSON APIs.

```
+---------------------------+
|   Frontend (Browser)      |   Thymeleaf templates, Lightweight Charts,
|   HTML / JS / CSS         |   jQuery, Bootstrap, fetch API
+---------------------------+
            |
+---------------------------+
|   Backend Service Layer   |   Java / Spring Boot / JPA
|   REST APIs + SSR Pages   |   StockController, FinancialsController
+---------------------------+
            |
+---------------------------+
|   Data Storage Layer      |   MySQL
|   Shared + Per-Symbol     |   Intraday bars, quotes, news, earnings,
|   Tables                  |   AI summaries, quarterly snapshots
+---------------------------+
            |
+---------------------------+
|   Data Ingestion Layer    |   Python / APScheduler
|   API Clients + AI Jobs   |   Twelve Data, Alpha Vantage, OpenAI,
|                           |   FinBERT tone analysis
+---------------------------+
```

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| Data Ingestion | Python 3, APScheduler, Requests, PyTorch, Hugging Face Transformers (FinBERT) |
| Data Storage | MySQL 8, mysql-connector-python, Spring Data JPA / Hibernate |
| Backend | Java 8+, Spring Boot 2.7, Thymeleaf, Maven |
| Frontend | HTML, CSS, JavaScript, Bootstrap 3, jQuery, TradingView Lightweight Charts |
| External APIs | Twelve Data (quotes, intraday), Alpha Vantage (news, earnings, transcripts), OpenAI Responses API |

## Repository Structure

```
Stock-Project/
├── python_ingestion/               # Python data ingestion layer
│   ├── main.py                     # APScheduler entry point
│   ├── refresh_all.py              # One-shot full data refresh
│   ├── config.py                   # Environment-based configuration
│   ├── db.py                       # MySQL connection pooling and operations
│   ├── symbols.py                  # S&P 500 symbol list and table name normalization
│   ├── alpha_vantage.py            # Alpha Vantage API client (news, earnings, financials)
│   ├── twelve_data.py              # Twelve Data API client (quotes, time series)
│   ├── openai_responses_client.py  # OpenAI structured output client
│   ├── earnings_tone.py            # FinBERT-based earnings tone analyzer
│   ├── requirements.txt            # Python dependencies
│   ├── .env.example                # Environment variable template
│   ├── jobs/                       # Individual ingestion job modules
│   │   ├── quotes.py               # Daily closing quote collection
│   │   ├── intraday.py             # 1-minute intraday bar collection
│   │   ├── apple_news.py           # Company news ingestion
│   │   ├── company_news_ai_summary.py  # AI-generated news summaries
│   │   ├── aapl_quarterly_snapshot.py  # Quarterly financial snapshots
│   │   ├── aapl_earnings_commentary.py # Earnings transcript summarization
│   │   └── aapl_earnings_ai_analysis.py # AI earnings analysis with tone data
│   ├── maintenance/                # Backfill and catch-up scripts
│   └── migrations/                 # Database migration scripts
├── JavaFiles/stockproject/         # Java Spring Boot backend
│   ├── pom.xml                     # Maven project configuration
│   └── src/main/
│       ├── java/.../controller/    # StockController, FinancialsController
│       ├── java/.../service/       # Service layer (news, earnings, quotes, etc.)
│       ├── java/.../dao/           # JPA repositories
│       ├── java/.../entity/        # JPA entity classes
│       └── resources/
│           ├── application.properties  # Spring Boot configuration
│           └── templates/          # Thymeleaf HTML templates
│               └── graphpages/     # Chart and stock pages
├── collecting_data_using_js/       # Legacy Node.js data collection (predecessor)
└── README.md
```

## Setup and Configuration

### Prerequisites

- Python 3.10+
- Java 8+ (JDK)
- MySQL 8.0+
- Maven 3.6+
- API keys for: Twelve Data, Alpha Vantage, OpenAI

### Database Setup

Create a MySQL database named `stock`:

```sql
CREATE DATABASE stock CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

The Python ingestion layer creates tables automatically on first run. The Spring Boot backend uses JPA and expects the tables to already exist.

### Python Ingestion Configuration

```bash
cd python_ingestion
cp .env.example .env
```

Edit `.env` with your credentials:

```
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=stock

TWELVE_DATA_API_KEY=your_twelve_data_key
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
OPENAI_API_KEY=your_openai_key
```

Install Python dependencies:

```bash
pip install -r requirements.txt
```

### Spring Boot Configuration

Database connection is configured in `JavaFiles/stockproject/src/main/resources/application.properties`. Update the datasource URL, username, and password to match your MySQL instance.

## How to Run

### Start the Python Ingestion Scheduler

The scheduler runs continuous data collection jobs during market hours:

```bash
python -m python_ingestion.main
```

### Run a One-Shot Data Refresh

Runs every ingestion step once in dependency-safe order, then exits:

```bash
python -m python_ingestion.refresh_all
```

### Run Individual Ingestion Jobs

Each job module supports standalone execution with a `--symbol` argument:

```bash
python -m python_ingestion.jobs.apple_news --symbol AAPL
python -m python_ingestion.jobs.aapl_quarterly_snapshot --symbol MSFT
python -m python_ingestion.jobs.aapl_earnings_commentary --symbol GOOGL
python -m python_ingestion.jobs.aapl_earnings_ai_analysis --symbol AAPL
```

### Start the Spring Boot Backend

```bash
cd JavaFiles/stockproject
./mvnw spring-boot:run
```

The web interface will be available at `http://localhost:8080`. Navigate to `/stock/list` to select a stock, or go directly to `/stock/AAPL` for a specific symbol.

### REST API Endpoints

The backend exposes financial data through JSON endpoints under `/api/financials`:

| Endpoint | Description |
|----------|-------------|
| `GET /api/financials/quarterly/recent?symbol=AAPL` | Recent quarterly financial snapshots with YoY calculations |
| `GET /api/financials/earnings?symbol=AAPL&period=FY2025Q1` | Earnings call commentary for a specific quarter |
| `GET /api/financials/earnings-ai?symbol=AAPL&period=FY2025Q1` | AI-generated earnings analysis with tone data |
| `GET /api/financials/earnings-ai/periods?symbol=AAPL` | Available earnings analysis periods for a symbol |
| `GET /api/financials/news-ai/by-date?symbol=AAPL` | AI news summary for a date range |

## Current Scope

The platform is functional for its core use case: collecting, storing, and visualizing stock data with integrated financial analysis. The current state includes:

- **Price data collection** is fully automated for 500+ symbols with 1-minute intraday resolution and daily closing quotes.
- **Company news, quarterly snapshots, and earnings analysis** modules are generalized to support any symbol, with the scheduler currently configured to run these jobs for AAPL.
- **The web frontend** renders interactive candlestick charts with overlaid news, AI summaries, quarterly financials, and earnings analysis for any symbol that has data in the database.
- **AI analysis** uses OpenAI for structured news and earnings summaries, and FinBERT for earnings call tone classification.

## Future Improvements

- Extend the scheduler to run news, earnings, and AI analysis jobs across multiple symbols
- Add an `ACTIVE_SYMBOLS` configuration to control which symbols receive full analysis
- Improve frontend UI/UX beyond the current Bootstrap 3 layout
- Add additional chart indicators and overlays (volume, moving averages)
- Expand company fundamentals coverage (balance sheet, cash flow)
- Add automated testing for ingestion jobs and backend services
- Containerize the application stack for easier deployment

## Notes

- **API rate limits**: Twelve Data and Alpha Vantage free tiers have daily and per-minute rate limits. The scheduler is configured with staggered job timing and delays between API calls to stay within these limits. Heavy multi-symbol usage may require premium API plans.
- **Configuration secrets**: API keys and database credentials are stored in `.env` files that are excluded from version control via `.gitignore`. Never commit credentials to the repository.
- **Project context**: This project was developed as a research-oriented platform for exploring stock data ingestion, financial analysis pipelines, and full-stack web visualization.
