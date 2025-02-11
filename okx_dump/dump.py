from typing import Literal
import datetime
import tenacity
import pandas as pd
from tqdm.asyncio import tqdm
import os
import asyncio
import aiohttp
import aiohttp.client_exceptions
import aiohttp.web_exceptions
import aiohttp.http_exceptions


class DataDumper:
    _info = {"spot": {}, "swap": {}, "future": {}}

    def __init__(
        self,
        asset_type: Literal["spot", "swap", "future"],
        symbols: list[str] | None = None,
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
        save_dir: str | None = None,
        quote_currency: str | None = None,
        chunk_size: int = 1024 * 16,
        proxy: str | None = None,
    ):
        self._loop = asyncio.get_event_loop()
        self._chunk_size = chunk_size
        self._proxy = proxy
        if start_date is None:
            start_date = datetime.datetime(
                2021, 10, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
            ).date()
        if end_date is None:
            end_date = (
                datetime.datetime.now(datetime.timezone.utc)
                - datetime.timedelta(days=1)
            ).date()

        self.asset_type = asset_type
        self._info[asset_type] = self.get_exchange_info(asset_type=asset_type, quote_currency=quote_currency)

        if symbols is None:
            self.symbols = list(self._info[asset_type].keys())
        else:
            self.symbols = symbols

        self.start_date = start_date
        self.end_date = end_date
        if save_dir is None:
            self.save_dir = os.path.join("./data", asset_type)
        else:
            self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
    
    
    async def _get_exchange_info(
        self,
        asset_type: Literal["spot", "swap", "future"] = "spot",
    ):
        exchange_map = {"spot": "okex", "swap": "okex-swap", "future": "okex-futures"}
        async with aiohttp.ClientSession(trust_env=True, proxy=self._proxy) as session:
            async with session.get(f"https://api.tardis.dev/v1/exchanges/{exchange_map[asset_type]}") as response:
                return await response.json()
        
    def get_exchange_info(
        self,
        asset_type: Literal["spot", "swap", "future"] = "spot",
        quote_currency: str | None = None,
    ):
        if self._info[asset_type]:
            return self._info[asset_type]

        start = datetime.datetime(
            2021, 10, 1, 0, 0, 0, tzinfo=datetime.timezone.utc
        ).date()
        end = (
            datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
        ).date()

        data = self._loop.run_until_complete(self._get_exchange_info(asset_type=asset_type))

        info = {}
        for symbol in data["datasets"]["symbols"][1:]:
            symbol_info = {}
            id = symbol["id"]
            symbol_info["id"] = id

            # 将ISO格式的日期字符串转换为datetime对象
            available_since = (
                datetime.datetime.strptime(
                    symbol["availableSince"].split(".")[0], "%Y-%m-%dT%H:%M:%S"
                )
                .replace(tzinfo=datetime.timezone.utc)
                .date()
            )

            available_to = (
                datetime.datetime.strptime(
                    symbol["availableTo"].split(".")[0], "%Y-%m-%dT%H:%M:%S"
                )
                .replace(tzinfo=datetime.timezone.utc)
                .date()
            )

            if available_since < start:
                available_since = start
            if available_to > end:
                available_to = end

            symbol_info["start_date"] = available_since
            symbol_info["end_date"] = available_to
            if asset_type == "spot":
                base = id.split("-")[0]
                quote = id.split("-")[-1]
                symbol_info["base"] = base
                symbol_info["quote"] = quote
            elif asset_type == "swap":
                symbol_info["base"] = id.split("-")[0]
                symbol_info["quote"] = id.split("-")[1]
            elif asset_type == "future":
                symbol_info["base"] = id.split("-")[0]
                symbol_info["quote"] = id.split("-")[1]
            if quote_currency is None or quote_currency == symbol_info["quote"]:
                info[symbol_info["id"]] = symbol_info
        self._info[asset_type] = info
        return info

    def generate_url(
        self,
        symbol: str,
        data_type: Literal["aggtrades", "trades", "swaprate"],
        date: datetime.date,
    ):
        base_url = f"https://www.okx.com/cdn/okex/traderecords/{data_type}/daily"
        date_str = date.strftime("%Y%m%d")
        file_name = f"{symbol}-{data_type}-{date.strftime('%Y-%m-%d')}.zip"
        url = f"{base_url}/{date_str}/{file_name}"
        return {"url": url, "file_name": file_name, "date": date.strftime("%Y-%m-%d")}
    
    @tenacity.retry(
        retry=tenacity.retry_if_exception_type(Exception),
        stop=tenacity.stop_after_attempt(5),
        wait=tenacity.wait_exponential(exp_base=2, multiplier=2, min=8, max=64),
    )
    async def _async_download_symbol_data(
        self,
        symbol: str,
        data_type: Literal["aggtrades", "trades", "swaprate"],
        date: datetime.date,
    ):
        res = self.generate_url(symbol=symbol, data_type=data_type, date=date)
        
        
        async with aiohttp.ClientSession(trust_env=True, proxy=self._proxy) as session:
            async with session.get(res["url"]) as response:
                response.raise_for_status()
                
                zip_path = os.path.join(self.save_dir, data_type, res["date"], res["file_name"])
                parquet_path = zip_path.replace(".zip", ".parquet")
                if not os.path.exists(parquet_path):
                    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
                    
                    if data_type in ["trades", "aggtrades"]:
                        with open(zip_path, "wb") as f:
                            async for chunk in response.content.iter_chunked(self._chunk_size):
                                f.write(chunk)
                    else:
                        content = await response.read()
                        with open(zip_path, "wb") as f:
                            f.write(content)
                
                    if data_type == "aggtrades":
                        df = pd.read_csv(
                            zip_path,
                            encoding="unicode_escape",
                            names=["trade_id", "side", "size", "price", "created_time"],
                            header=0,
                        )
                        df["timestamp"] = pd.to_datetime(
                            df["created_time"], unit="ms", utc=True
                        )
                        df.sort_values(by="timestamp", inplace=True)
                        df.to_parquet(parquet_path, index=False)
                    elif data_type == "swaprate":
                        df = pd.read_csv(
                            zip_path,
                            encoding="unicode_escape",
                            names=["contract_type", "funding_rate", "real_funding_rate", "funding_time"],
                            header=0,
                        )
                        df["timestamp"] = pd.to_datetime(
                            df["funding_time"], unit="ms", utc=True
                        )
                        df.to_parquet(parquet_path, index=False)
                    elif data_type == "trades":
                        df = pd.read_csv(
                            zip_path,
                            encoding="unicode_escape",
                            names=["trade_id", "side", "size", "price", "created_time"],
                            header=0,
                        )
                        df["timestamp"] = pd.to_datetime(
                            df["created_time"], unit="ms", utc=True
                        )
                        df.sort_values(by="timestamp", inplace=True)
                        df.to_parquet(parquet_path, index=False)
                    os.remove(zip_path)
                return parquet_path

    async def _aggregate_symbol_kline(self, symbol, date: datetime.date):
        parquet_path = await self._async_download_symbol_data(
            symbol=symbol, data_type="aggtrades", date=date
        )  # we use aggtrades to generate kline
        save_path = parquet_path.replace("aggtrades", "klines")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        if os.path.exists(save_path):
            return
        df = pd.read_parquet(parquet_path)
        ohlcv = (
            df.set_index("timestamp")
            .resample("1min")
            .agg(
                {
                    "price": ["first", "max", "min", "last"],  # OHLC
                    "size": "sum",  # volume
                }
            )
        )
        ohlcv.columns = ["open", "high", "low", "close", "volume"]
        # For rows with no trading volume, fill ohlc with the previous row's close, i.e., ohlcv are all the previous row's close
        no_trade_mask = (ohlcv["volume"] == 0) | (ohlcv["volume"].isna())
        ohlcv.loc[no_trade_mask, ["open", "high", "low", "close"]] = ohlcv[
            "close"
        ].shift(1)
        ohlcv["volume"] = ohlcv["volume"].fillna(0)
        ohlcv.reset_index(inplace=True)
        ohlcv.to_parquet(save_path, index=False)
        return save_path
    
    def _dump_symbol_data(
        self,
        symbol: str,
        data_type: Literal["aggtrades", "trades", "swaprate", "klines"],
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
    ):
        info = self._info[self.asset_type]
        if symbol not in info:
            raise ValueError(f"symbol {symbol} not found in {self.asset_type}")

        symbol_info = info[symbol]
        if start_date is None:
            start_date = symbol_info["start_date"]
        if end_date is None:
            end_date = symbol_info["end_date"]

        if start_date > end_date:
            raise ValueError(
                f"start_date {start_date} is greater than end_date {end_date}"
            )

        if start_date < symbol_info["start_date"]:
            start_date = symbol_info["start_date"]
        if end_date > symbol_info["end_date"]:
            end_date = symbol_info["end_date"]

        date_list = []
        while start_date <= end_date:
            date_list.append(start_date)
            start_date += datetime.timedelta(days=1)

        if data_type == "klines":
            func = self._aggregate_symbol_kline
            params = [(symbol, date) for date in date_list]
        else:
            func = self._async_download_symbol_data
            params = [(symbol, data_type, date) for date in date_list]

        self._loop.run_until_complete(tqdm.gather(*[func(*param) for param in params], leave=False, desc=f"Dumping {symbol} {data_type}"))
        
        
    def dump_symbols(
        self,
        data_type: Literal["aggtrades", "trades", "swaprate", "klines"],
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
    ):
        for symbol in tqdm(self.symbols, desc="Dumping symbols", leave=False):
            self._dump_symbol_data(
                symbol=symbol,
                data_type=data_type,
                start_date=start_date,
                end_date=end_date,
            )


if __name__ == "__main__":
    dumper = DataDumper(
        asset_type="swap",
        symbols=["BTC-USDT-SWAP", "ETH-USDT-SWAP", "SOL-USDT-SWAP", "1INCH-USDT-SWAP"],
    )
    dumper.dump_symbols(
        data_type="trades",
        start_date=datetime.date(2024, 1, 1),
        # end_date=datetime.date(2024, 1, 1),
    )
