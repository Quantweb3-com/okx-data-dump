# OKX Historical Data Download Tool

A Python tool for downloading historical data from OKX exchange. Supports downloading trading data for spot, swap, and futures markets.

## Features

- Multiple data types supported:
  - Trade-by-trade data (trades)
  - Aggregated trade data (aggtrades)
  - Funding rate data (swaprate)
  - Candlestick data (klines, generated from aggregated trades)
- Multiple market types supported:
  - Spot
  - Perpetual Swap
  - Futures
- Customizable time range for downloads
- Asynchronous concurrent downloading for improved efficiency
- Automatic retry mechanism for improved stability
- Data automatically saved in Parquet format for storage efficiency

## Dependencies

```bash
pip install pandas aiohttp tenacity tqdm
```

## Usage Example

```python
import datetime
from okx_dump.dump import DataDumper

# Initialize downloader
dumper = DataDumper(
    asset_type="swap",  # Options: "spot", "swap", "future"
    symbols=["BTC-USDT-SWAP", "ETH-USDT-SWAP"],  # Optional, downloads all pairs by default
    start_date=datetime.date(2024, 1, 1),  # Optional, defaults to 2021-10-01
    end_date=datetime.date(2024, 1, 31),  # Optional, defaults to yesterday
    save_dir="./data",  # Optional, defaults to "./data/{asset_type}"
    proxy="http://your-proxy-url"  # Optional, set proxy
)

# Download data
dumper.dump_symbols(
    data_type="trades",  # Options: "trades", "aggtrades", "swaprate", "klines"
    start_date=datetime.date(2024, 1, 1),  # Optional, overrides initialization setting
    end_date=datetime.date(2024, 1, 31)  # Optional, overrides initialization setting
)
```

## Data Storage Structure

Downloaded data will be saved in the following structure:
```
data/
├── spot/
│   ├── trades/
│   │   └── 2024-01-01/
│   │       └── BTC-USDT-trades-2024-01-01.parquet
│   └── klines/
│       └── 2024-01-01/
│           └── BTC-USDT-klines-2024-01-01.parquet
├── swap/
└── future/
```

## Data Formats

### Trade Data (trades/aggtrades)
- trade_id: Trade ID
- side: Trade direction
- size: Trade size
- price: Trade price
- created_time: Creation time (millisecond timestamp)
- timestamp: UTC timestamp

### Funding Rate Data (swaprate)
- contract_type: Contract type
- funding_rate: Funding rate
- real_funding_rate: Actual funding rate
- funding_time: Settlement time (millisecond timestamp)
- timestamp: UTC timestamp

### Candlestick Data (klines)
- timestamp: UTC timestamp
- open: Opening price
- high: Highest price
- low: Lowest price
- close: Closing price
- volume: Trading volume

## Notes

1. Data download depends on network connection, stable network environment recommended
2. Large data downloads may take considerable time, please be patient
3. Downloaded data is automatically saved in Parquet format, readable with pandas
4. The program will automatically retry in case of network issues
