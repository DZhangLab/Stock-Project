#!/usr/bin/env python3
"""
Standalone stock data visualization script
Generates chart files directly without requiring a web server
"""
import sys
import os
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add project path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import pandas as pd
    import matplotlib.pyplot as plt
    import mplfinance as mpf
    from mysql.connector import connect
    from python_ingestion.config import load_config
    from python_ingestion.db import get_db_manager
except ImportError as e:
    print(f"❌ Missing required libraries: {e}")
    print("Please run: pip install pandas matplotlib mplfinance mysql-connector-python")
    sys.exit(1)


def plot_candlestick(symbol, start_date=None, end_date=None, output_dir="charts"):
    """
    Generate candlestick chart for a stock
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
        start_date: Start date (format: 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS')
        end_date: End date (format: 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS')
        output_dir: Output directory
    """
    config = load_config()
    db = get_db_manager()
    
    # If no date specified, use the most recent day's data
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    
    # Normalize table name (handle special characters)
    table_name = symbol.replace('.', '_').replace('/', '_').upper()
    
    # Query data
    query = """
    SELECT timePoint as datetime, minuteOpen as open, minuteHigh as high, 
           minuteLow as low, minuteClose as close, minuteVolume as volume
    FROM {}
    WHERE timePoint BETWEEN %s AND %s
    ORDER BY timePoint ASC
    """
    
    try:
        # Use dictionary cursor to get results
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query.format(table_name), (start_date, end_date))
            results = cursor.fetchall()
            cursor.close()
        
        if not results:
            print(f"❌ No data found for {symbol} between {start_date} and {end_date}")
            print(f"   Table name: {table_name}")
            print(f"   Hint: Check if table exists or adjust date range")
            return None
        
        # Convert to DataFrame
        df = pd.DataFrame(results)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df = df.set_index('datetime')
        
        # Ensure correct data types
        df['open'] = pd.to_numeric(df['open'], errors='coerce')
        df['high'] = pd.to_numeric(df['high'], errors='coerce')
        df['low'] = pd.to_numeric(df['low'], errors='coerce')
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        
        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Generate filename
        start_str = start_date.replace(' ', '_').replace(':', '-')[:10]
        end_str = end_date.replace(' ', '_').replace(':', '-')[:10]
        filename = f"{symbol}_{start_str}_to_{end_str}_candle.png"
        filepath = output_path / filename
        
        # Plot candlestick chart
        mpf.plot(
            df,
            type='candle',
            style='yahoo',
            title=f"{symbol} K-Line Chart\n{start_date[:10]} to {end_date[:10]}",
            ylabel='Price ($)',
            ylabel_lower='Volume',
            volume=True,
            savefig=dict(fname=str(filepath), dpi=150, bbox_inches='tight')
        )
        
        print(f"✅ Generated candlestick chart for {symbol}")
        print(f"   File path: {filepath.absolute()}")
        print(f"   Data points: {len(df)}")
        return str(filepath.absolute())
        
    except Exception as e:
        print(f"❌ Error generating chart: {e}")
        import traceback
        traceback.print_exc()
        return None


def plot_line_chart(symbol, start_date=None, end_date=None, output_dir="charts"):
    """
    Generate line chart for a stock
    """
    config = load_config()
    db = get_db_manager()
    
    if not end_date:
        end_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if not start_date:
        start_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    
    table_name = symbol.replace('.', '_').replace('/', '_').upper()
    
    query = """
    SELECT timePoint as datetime, minuteClose as close, minuteVolume as volume
    FROM {}
    WHERE timePoint BETWEEN %s AND %s
    ORDER BY timePoint ASC
    """
    
    try:
        # Use dictionary cursor to get results
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query.format(table_name), (start_date, end_date))
            results = cursor.fetchall()
            cursor.close()
        
        if not results:
            print(f"❌ No data found for {symbol}")
            return None
        
        df = pd.DataFrame(results)
        df['datetime'] = pd.to_datetime(df['datetime'])
        df['close'] = pd.to_numeric(df['close'], errors='coerce')
        df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        start_str = start_date.replace(' ', '_').replace(':', '-')[:10]
        end_str = end_date.replace(' ', '_').replace(':', '-')[:10]
        filename = f"{symbol}_{start_str}_to_{end_str}_line.png"
        filepath = output_path / filename
        
        # Create chart
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), sharex=True)
        
        # Price line chart
        ax1.plot(df['datetime'], df['close'], linewidth=2, color='blue')
        ax1.set_ylabel('Price ($)', fontsize=12)
        ax1.set_title(f"{symbol} Price Chart - {start_date[:10]} to {end_date[:10]}", fontsize=14)
        ax1.grid(True, alpha=0.3)
        
        # Volume bar chart
        ax2.bar(df['datetime'], df['volume'], color='orange', alpha=0.6)
        ax2.set_ylabel('Volume', fontsize=12)
        ax2.set_xlabel('Time', fontsize=12)
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✅ Generated line chart for {symbol}")
        print(f"   File path: {filepath.absolute()}")
        return str(filepath.absolute())
        
    except Exception as e:
        print(f"❌ Error generating chart: {e}")
        import traceback
        traceback.print_exc()
        return None


def list_available_symbols():
    """List available stock symbols in the database"""
    db = get_db_manager()
    
    query = """
    SELECT DISTINCT table_name 
    FROM information_schema.tables 
    WHERE table_schema = 'stock' 
    AND table_name NOT LIKE 'everydayAfterClose'
    ORDER BY table_name
    """
    
    try:
        with db.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query)
            results = cursor.fetchall()
            cursor.close()
        symbols = [row.get('table_name', row.get('TABLE_NAME', '')) for row in results if row]
        return [s for s in symbols if s]
    except Exception as e:
        print(f"❌ Error querying stock list: {e}")
        return []


def main():
    parser = argparse.ArgumentParser(description='Generate stock data visualization charts')
    parser.add_argument('symbol', nargs='?', help='Stock symbol (e.g., AAPL, MSFT)')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--type', choices=['candle', 'line'], default='candle', 
                       help='Chart type: candle (candlestick) or line (line chart)')
    parser.add_argument('--output-dir', default='charts', help='Output directory (default: charts)')
    parser.add_argument('--list', action='store_true', help='List all available stock symbols')
    
    args = parser.parse_args()
    
    if args.list:
        print("📊 Available stock symbols:")
        symbols = list_available_symbols()
        if symbols:
            for i, sym in enumerate(symbols, 1):
                print(f"   {i}. {sym}")
        else:
            print("   (No data available)")
        return
    
    if not args.symbol:
        print("❌ Please specify a stock symbol")
        print("   Usage: python plot_stock.py <SYMBOL> [options]")
        print("   Example: python plot_stock.py AAPL --start 2024-11-10 --end 2024-11-10")
        print("   List all stocks: python plot_stock.py --list")
        return
    
    if args.type == 'candle':
        plot_candlestick(args.symbol, args.start, args.end, args.output_dir)
    else:
        plot_line_chart(args.symbol, args.start, args.end, args.output_dir)


if __name__ == "__main__":
    main()

