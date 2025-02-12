import tenacity
import aiohttp.client_exceptions

count = 0

class CustomException(Exception):
    def __init__(self, message, status):
        self.message = message
        self.status = status
        super().__init__(self.message)

def should_retry(x):
    print(x.status)
    return not isinstance(x, CustomException) or x.status in [500, 502, 503, 504, 429, 408]


@tenacity.retry(stop=tenacity.stop_after_attempt(5), wait=tenacity.wait_fixed(1))
def retry():
    global count
    print(f"retry {count}")
    count += 1
    try:
        raise CustomException("test", 500)
    except CustomException as e:
        if e.status in [500, 502, 503, 504, 429, 408]:
            raise tenacity.TryAgain
        else:
            print("not retry")
    

retry()
