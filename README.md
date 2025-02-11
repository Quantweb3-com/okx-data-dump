好的，我来帮您为这个OKX数据下载工具编写一个README.md文件：

```markdown
# OKX 历史数据下载工具

这是一个用于下载OKX交易所历史数据的Python工具。支持现货（spot）、永续合约（swap）和交割合约（future）的交易数据下载。

## 功能特点

- 支持多种数据类型：
  - 逐笔交易数据 (trades)
  - 聚合交易数据 (aggtrades)
  - 资金费率数据 (swaprate)
  - K线数据 (klines，基于聚合交易数据生成)
- 支持多种交易品种：
  - 现货 (spot)
  - 永续合约 (swap)
  - 交割合约 (future)
- 支持自定义时间范围下载
- 异步并发下载，提高下载效率
- 自动重试机制，提高下载稳定性
- 数据自动保存为Parquet格式，节省存储空间

## 安装依赖

```bash
pip install pandas aiohttp tenacity tqdm
```

## 使用示例

```python
import datetime
from okx_dump.dump import DataDumper

# 初始化下载器
dumper = DataDumper(
    asset_type="swap",  # 可选: "spot", "swap", "future"
    symbols=["BTC-USDT-SWAP", "ETH-USDT-SWAP"],  # 可选，默认下载所有交易对
    start_date=datetime.date(2024, 1, 1),  # 可选，默认从2021-10-01开始
    end_date=datetime.date(2024, 1, 31),  # 可选，默认到昨天
    save_dir="./data",  # 可选，默认为 "./data/{asset_type}"
    proxy="http://your-proxy-url"  # 可选，设置代理
)

# 下载数据
dumper.dump_symbols(
    data_type="trades",  # 可选: "trades", "aggtrades", "swaprate", "klines"
    start_date=datetime.date(2024, 1, 1),  # 可选，覆盖初始化时的设置
    end_date=datetime.date(2024, 1, 31)  # 可选，覆盖初始化时的设置
)
```

## 数据存储结构

下载的数据将按以下结构保存：
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

## 数据格式

### 逐笔交易数据 (trades/aggtrades)
- trade_id: 交易ID
- side: 交易方向
- size: 交易数量
- price: 交易价格
- created_time: 创建时间（毫秒时间戳）
- timestamp: UTC时间戳

### 资金费率数据 (swaprate)
- contract_type: 合约类型
- funding_rate: 资金费率
- real_funding_rate: 实际资金费率
- funding_time: 结算时间（毫秒时间戳）
- timestamp: UTC时间戳

### K线数据 (klines)
- timestamp: UTC时间戳
- open: 开盘价
- high: 最高价
- low: 最低价
- close: 收盘价
- volume: 成交量

## 注意事项

1. 数据下载依赖网络连接，建议使用稳定的网络环境
2. 大量数据下载可能需要较长时间，请耐心等待
3. 下载的数据会自动保存为Parquet格式，可以使用pandas读取
4. 如果遇到网络问题，程序会自动重试
```
