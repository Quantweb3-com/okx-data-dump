from okx_dump import DataDumper
import datetime

dumper = DataDumper(
    asset_type="swap",
    quote_currency="USDT",
)

dumper.dump_symbols(
    data_type="klines",
    start_date=datetime.date(2024, 1, 1),
)
