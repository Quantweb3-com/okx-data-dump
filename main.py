from okx_dump import DataDumper
import datetime

dumper = DataDumper(
    asset_type="swap",
    quote_currency="USDT",
    save_dir="/share/okx_data"
)

dumper.dump_symbols(
    data_type="swaprate-all",
    start_date=datetime.date(2023, 1, 1),
)
