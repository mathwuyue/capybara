import asyncio
import os
import time
import traceback
from datetime import datetime

import dashscope
from dotenv import load_dotenv
from loguru import logger
from openai import AsyncOpenAI

load_dotenv()


client = AsyncOpenAI(api_key=os.getenv("LITELLM_KEY"), base_url="http://127.0.0.1:4000")

SEARCH_OPTIONS = {
    "forced_search": False,  # 强制开启联网搜索
    "search_strategy": "pro",  # 模型将搜索10条互联网信息
}


async def llm(
    query: str,
    model: str = os.getenv("MODEL"),
    sys_msg=None,
    stream=False,
    temperature=0.85,
    top_p=0.8,
    history=[],
    json_format=None,
    is_text=False,
    is_reasoning=False,
    is_search=False,
    thinking_budget=0,
    is_advanced_search=False,
) -> str:
    if sys_msg:
        messages = (
            [{"role": "system", "content": sys_msg}]
            + history
            + [{"role": "user", "content": query}]
        )
    else:
        messages = history + [{"role": "user", "content": query}]
    if is_reasoning:
        top_p = 0.95
    try:
        start = time.time()
        if is_advanced_search:
            if not thinking_budget:
                thinking_budget = 32768
            response = dashscope.Generation.call(
                # 若没有配置环境变量，请用阿里云百炼API Key将下行替换为：api_key="sk-xxx"
                api_key=os.getenv("DASHSCOPE_API_KEY"),
                model=model,
                messages=messages,
                enable_thinking=is_reasoning,
                enable_search=True,  # 开启联网搜索的参数
                search_options=SEARCH_OPTIONS.update(
                    {
                        "enable_source": True,  # 使返回结果包含搜索来源的信息，OpenAI 兼容方式暂不支持返回
                        "enable_citation": True,  # 开启角标标注功能
                        "citation_format": "[ref_<number>]",  # 角标形式为[ref_i]
                    }
                ),
                stream=stream,
                incremental_output=True,
                result_format="message",
                thinking_budget=thinking_budget,
                top_p=top_p,
            )
        else:
            extra_body = {"enable_thinking": is_reasoning, "enable_search": is_search}
            if is_search:
                extra_body.update({"search_options": SEARCH_OPTIONS})
            if thinking_budget > 0:
                extra_body.update({"thinking_budget": thinking_budget})
            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                stream=stream,
                response_format=json_format,
                extra_body=extra_body,
                top_p=top_p,
            )
        print("llm time:", time.time() - start)
        if not is_text:
            return response
        assert stream is False
        return response.choices[0].message.content
    except Exception as e:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        error_msg = (
            f"{timestamp} - Model: {model} - Error: {str(e)}\n{traceback.format_exc()}"
        )
        logger.error(error_msg)
        print(error_msg)


def chunk_to_dict(chunk) -> dict:
    if isinstance(chunk, dict):
        return chunk
    return chunk.model_dump()


if __name__ == "__main__":
    response = asyncio.run(llm("你好", "qwen-plus"))
    print(response)
