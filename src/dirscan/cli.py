import asyncio
from pathlib import Path
from typing import Optional

import httpx
import typer

from .dedup import Dedup
from .format import to_json, to_sarif
from .logger import Logger

# 关闭自动补全
app = typer.Typer(add_completion=False)


@app.command(name="scan")  # 注册scan命令
def scan(
    # 定义命令参数，"..."表示没有就报错，数字表示默认值，第二个和第三个表示传参的标志，max,min限定int类型的参数值，help记录在help里
    # Typer自动把参数解析为str类型，如果是其它类型的话要增加类型注解。
    url=typer.Option(..., "--url", "-u", help="目标地址"),
    wordlist: Optional[Path] = typer.Option(
        Path("default.txt"),
        "--wordlist",
        "-w",
        help="字典文件",
    ),
    workers: int = typer.Option(10, "--threads", "-t", min=1, max=50, help="并发请求数"),
    methods=typer.Option("head", "--method", "-m", help="请求方法"),
    rate_limit: int = typer.Option(
        100, "--rate", "-r", min=0, help="速率限制，0表示不限，100表示每秒最多100请求"
    ),
    format=typer.Option("json", "--format", "-f", help="结果格式(json/sarif)"),
    output=typer.Option("out.json", "--output", "-o", help="保存结果文件"),
):
    good_method = ["get", "head"]
    method = methods.lower()
    if method not in good_method:
        print("仅限get，head方法")
        exit()
    logger = Logger()
    logger.info(f"开始扫描，目标：{url},请求方法：{method}字典:{wordlist},并发请求数：{workers}")
    dedup = Dedup(sim_threshold=0.9)
    # 运行协程
    asyncio.run(
        _amain(
            url, method, wordlist, workers, dedup, logger, rate_limit, format, output
        )
    )
    logger.info("扫描结束，日志已保存")


async def token_producer(queue, rate_limit):
    if rate_limit == 0:
        while True:
            await queue.put(True)
            await asyncio.sleep(0)
    else:
        while True:
            # 根据限定速率设置令牌队列，令牌满的时候await将添加令牌操作挂起，等令牌被拿走后继续填充，
            for _ in range(rate_limit):
                await queue.put(True)
            await asyncio.sleep(1)


async def _amain(
    url, method, wordlist, workers: int, dedup, logger, rate_limit: int, format, output
):
    # 异步打开tcp连接池，不阻塞线程
    async with httpx.AsyncClient(
        timeout=10, limits=httpx.Limits(max_keepalive_connections=workers)
    ) as client:
        with open(wordlist, encoding="utf-8") as f:
            paths = [l.strip() for l in f if l.strip()]
        if rate_limit != 0:
            # 设置令牌限制每秒最大发送量
            queue = asyncio.Queue(maxsize=rate_limit)
            # 执行创建令牌的任务
            asyncio.create_task(token_producer(queue, rate_limit))
        else:
            # 设置令牌限制每秒最大发送量
            queue = asyncio.Queue()
            # 执行创建令牌的任务
            asyncio.create_task(token_producer(queue, rate_limit))
        # 设置并发请求数，限制同时发送的http请求数
        sem = asyncio.Semaphore(workers)

        async def fetch(p: str):
            if rate_limit != 0:
                # 确保拿到令牌再进行下一步操作
                await queue.get()
            # 确保有空余请求
            async with sem:
                full_url = f"{url.rstrip('/')}{p}"
                try:
                    # 请求发送后就挂起await，结果返回后再进行下一步，不阻塞cpu
                    r = await client.request(method, full_url)
                    body = b""
                    # 如果是get请求，对结果进行查重判断，因为404模板的话有一份即可，不需要都存储
                    if method == "get":
                        body = r.content
                        if dedup.is_duplicate(body):
                            logger.info(f"[DEDUP] {r.status_code} {full_url}")
                            return {"url": full_url, "status": r.status_code}
                        # print(f"{r.status_code} {p}")
                    logger.info(f"{r.status_code} {full_url}")
                    return {"url": full_url, "status": r.status_code}
                except Exception:
                    # print(f"错误信息：{Exception}")
                    logger.info(f"错误信息：{Exception}")
                    return {"url": full_url, "status": "异常"}

        # 每个路径设立一个协程对象，执行fetch函数，这里用gather一起注册任务然后执行，等执行后按照顺序输出。
        results = await asyncio.gather(*(fetch(p) for p in paths))
        if format == "json":
            with open(output, "w", encoding="utf-8") as f:
                f.write(to_json(results))
        else:
            output = output.replace(".json", ".sarif")
            to_sarif(results, output_file=output)


if __name__ == "__main__":
    app()
