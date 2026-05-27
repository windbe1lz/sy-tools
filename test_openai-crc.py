import email
from wsgiref import headers
from openai import OpenAI
from datetime import datetime
import json
import os
import random
import requests
import concurrent.futures

# 初始化客户端
client = OpenAI(
    api_key="sk-8f6a0078594144e2bdd83272bdbc199c",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

user_question = """商业银行法第二章第二十三条是什么内容"""

user_email = "pwc@aishenyuan.com"
# Bearer token
user_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyIjoiNjkxYWMyY2MzZmRkZDgwY2EzZjFmNjU1IiwidGVuYW50X2lkIjoiNjhjYzE3NjMxOWUyYWMwMDAxMzM2MWFjIiwiZW1haWwiOiJwd2NAYWlzaGVueXVhbi5jb20iLCJleHAiOjE3NjQ5MjQyMTN9.Ops8ws9tBGA1og3b4jYlGZRL163d1cnDrrLpgy9wnWQ"
# 元数据过滤列表
user_metadata_filters = [
    {
        "key": "department",
        "operator": "contains",
        "value": ['雪花','医商','怡宝','金控','建材','数科','华创','燃气','置地',
                  '微电子','五丰','电力','医药','三九','万家','化材','集团','江中',
                  '健康','隆地','双鹤','信托','资产','长电'],
    }
]

tools = [
    # 通用-审计定性知识库
    {
        "type": "function",
        "function": {
            "name": "retrieve_general_audit_qualitative_knowledgebase",
            "description": "从《通用-审计定性知识库》中检索内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "检索知识库时输入的内容",
                    }
                },
                "required": ["question"],
            }
        }
    },
    # 通用-地方级法律法规知识库
    {
        "type": "function",
        "function": {
            "name": "retrieve_general_local_law_knowledgebase",
            "description": "从《通用-地方级法律法规知识库》中检索内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "检索知识库时输入的内容",
                    }
                },
                "required": ["question"],
            }
        }
    },
    # 通用-国家级法律法规知识库
    {
        "type": "function",
        "function": {
            "name": "retrieve_general_national_law_knowledgebase",
            "description": "从《通用-国家级级法律法规知识库》中检索内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "检索知识库时输入的内容",
                    }
                },
                "required": ["question"],
            }
        }
    },
    # 通用-审计通用知识库
    {
        "type": "function",
        "function": {
            "name": "retrieve_general_audit_knowledgebase",
            "description": "从《通用-审计通用知识库》中检索内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "检索知识库时输入的内容",
                    }
                },
                "required": ["question"],
            }
        }
    },
    # 通用-审计案例库
    {
        "type": "function",
        "function": {
            "name": "retrieve_general_audit_case_knowledgebase",
            "description": "从《通用-审计案例知识库》中检索内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "检索知识库时输入的内容",
                    }
                },
                "required": ["question"],
            }
        }
    },
    # 华润内部-华润各事业部制度知识库
    {
        "type": "function",
        "function": {
            "name": "retrieve_crc_business_units_policy_knowledgebase",
            "description": "从《华润内部-华润各事业部制度知识库》中检索内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "检索知识库时输入的内容",
                    }
                },
                "required": ["question"],
            }
        }
    },
    # 华润内部-华润检查要点清单知识库
    {
        "type": "function",
        "function": {
            "name": "retrieve_crc_checklist_knowledgebase",
            "description": "从《华润内部-华润检查要点清单知识库》中检索内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "检索知识库时输入的内容",
                    }
                },
                "required": ["question"],
            }
        }
    },
    # 华润内部-华润内部制度知识库
    {
        "type": "function",
        "function": {
            "name": "retrieve_crc_internal_policy_knowledgebase",
            "description": "从《华润内部-华润内部制度知识库》中检索内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "检索知识库时输入的内容",
                    }
                },
                "required": ["question"],
            }
        }
    },
    # 华润内部-华润审计案例知识库
    {
        "type": "function",
        "function": {
            "name": "retrieve_crc_audit_case_knowledgebase",
            "description": "从《华润内部-华润审计案例知识库》中检索内容",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "检索知识库时输入的内容",
                    }
                },
                "required": ["question"],
            }
        }
    }
]
# 通用-审计定性知识库
def retrieve_general_audit_qualitative_knowledgebase(arguments):
    knowledge_id = "693117368edb1306002e9a57"
    body = {
        "query": arguments["question"],
        "email": user_email,
        "knowledge_id": knowledge_id,
        "top_k" : 2,
        "score_threshold" : 0.3,
        "retrieval_type": "hybrid",
        "rerank_enabled": True,
        "keyword_enabled": True,
        # "metadata_filters":user_metadata_filters
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }
    response = requests.post("https://deepparser.crc.com.cn/v1/api/rag/retrieval", json=body, headers=headers)
    try:
        result = response.json()
        records = result.get("records", [])
        
        # 只筛选字段：score, content, file_url
        filtered_records = []
        for record in records:
            filtered_record = {
                "score": record.get("score"),
                "content": record.get("content"),
                "metadata": record.get("metadata"),
            }
            
            filtered_records.append(filtered_record)
        
        return json.dumps(filtered_records, ensure_ascii=False) if filtered_records else "未找到相关内容"
    except json.JSONDecodeError:
        return "知识库服务响应格式错误"
    
# 通用-地方级法律法规知识库
def retrieve_general_local_law_knowledgebase(arguments):
    knowledge_id = "6931170c8edb13000b06bee3"
    body = {
        "query": arguments["question"],
        "email": user_email,
        "knowledge_id": knowledge_id,
        "top_k" : 2,
        "score_threshold" : 0.3,
        "retrieval_type": "hybrid",
        "rerank_enabled": True,
        "keyword_enabled": True,
        # "metadata_filters":user_metadata_filters
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }
    response = requests.post("https://deepparser.crc.com.cn/v1/api/rag/retrieval", json=body, headers=headers)
    try:
        result = response.json()
        records = result.get("records", [])
        
        # 只筛选字段：score, content, file_url
        filtered_records = []
        for record in records:
            filtered_record = {
                "score": record.get("score"),
                "content": record.get("content"),
                "metadata": record.get("metadata"),
            }
            
            filtered_records.append(filtered_record)
        
        return json.dumps(filtered_records, ensure_ascii=False) if filtered_records else "未找到相关内容"
    except json.JSONDecodeError:
        return "知识库服务响应格式错误"
    
# 通用-国家级法律法规知识库
def retrieve_general_national_law_knowledgebase(arguments):
    knowledge_id = "6931171bae418404e0c795b5"
    body = {
        "query": arguments["question"],
        "email": user_email,
        "knowledge_id": knowledge_id,
        "top_k" : 2,
        "score_threshold" : 0.3,
        "retrieval_type": "hybrid",
        "rerank_enabled": True,
        "keyword_enabled": True,
        # "metadata_filters":user_metadata_filters
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }
    response = requests.post("https://deepparser.crc.com.cn/v1/api/rag/retrieval", json=body, headers=headers)
    try:
        result = response.json()
        records = result.get("records", [])
        
        # 只筛选字段：score, content, file_url
        filtered_records = []
        for record in records:
            filtered_record = {
                "score": record.get("score"),
                "content": record.get("content"),
                "metadata": record.get("metadata"),
            }
            
            filtered_records.append(filtered_record)
        
        return json.dumps(filtered_records, ensure_ascii=False) if filtered_records else "未找到相关内容"
    except json.JSONDecodeError:
        return "知识库服务响应格式错误"
    
# 通用-审计通用知识库
def retrieve_general_audit_knowledgebase(arguments):
    knowledge_id = "69311751ef772e07e5e349c2"
    body = {
        "query": arguments["question"],
        "email": user_email,
        "knowledge_id": knowledge_id,
        "top_k" : 2,
        "score_threshold" : 0.3,
        "retrieval_type": "hybrid",
        "rerank_enabled": True,
        "keyword_enabled": True,
        # "metadata_filters":user_metadata_filters
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }
    response = requests.post("https://deepparser.crc.com.cn/v1/api/rag/retrieval", json=body, headers=headers)
    try:
        result = response.json()
        records = result.get("records", [])
        
        # 只筛选字段：score, content, file_url
        filtered_records = []
        for record in records:
            filtered_record = {
                "score": record.get("score"),
                "content": record.get("content"),
                "metadata": record.get("metadata"),
            }
            
            filtered_records.append(filtered_record)
        
        return json.dumps(filtered_records, ensure_ascii=False) if filtered_records else "未找到相关内容"
    except json.JSONDecodeError:
        return "知识库服务响应格式错误"
    
# 通用-审计案例库
def retrieve_general_audit_case_knowledgebase(arguments):
    knowledge_id = "693117268edb1306115e6070"
    body = {
        "query": arguments["question"],
        "email": user_email,
        "knowledge_id": knowledge_id,
        "top_k" : 2,
        "score_threshold" : 0.3,
        "retrieval_type": "hybrid",
        "rerank_enabled": True,
        "keyword_enabled": True,
        # "metadata_filters":user_metadata_filters
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }
    response = requests.post("https://deepparser.crc.com.cn/v1/api/rag/retrieval", json=body, headers=headers)
    try:
        result = response.json()
        records = result.get("records", [])
        
        # 只筛选字段：score, content, file_url
        filtered_records = []
        for record in records:
            filtered_record = {
                "score": record.get("score"),
                "content": record.get("content"),
                "metadata": record.get("metadata"),
            }
            
            filtered_records.append(filtered_record)
        
        return json.dumps(filtered_records, ensure_ascii=False) if filtered_records else "未找到相关内容"
    except json.JSONDecodeError:
        return "知识库服务响应格式错误"
# 华润内部-华润各事业部制度知识库
def retrieve_crc_business_units_policy_knowledgebase(arguments):
    knowledge_id = "693107394747a40534f7663a"
    body = {
        "query": arguments["question"],
        "email": user_email,
        "knowledge_id": knowledge_id,
        "top_k" : 2,
        "score_threshold" : 0.3,
        "retrieval_type": "hybrid",
        "rerank_enabled": True,
        "keyword_enabled": True,
        # "metadata_filters":user_metadata_filters
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }
    response = requests.post("https://deepparser.crc.com.cn/v1/api/rag/retrieval", json=body, headers=headers)
    try:
        result = response.json()
        records = result.get("records", [])
        
        # 只筛选字段：score, content, file_url
        filtered_records = []
        for record in records:
            filtered_record = {
                "score": record.get("score"),
                "content": record.get("content"),
                "metadata": record.get("metadata"),
            }
            
            filtered_records.append(filtered_record)
        
        return json.dumps(filtered_records, ensure_ascii=False) if filtered_records else "未找到相关内容"
    except json.JSONDecodeError:
        return "知识库服务响应格式错误"
    
# 华润内部-华润检查要点清单知识库
def retrieve_crc_checklist_knowledgebase(arguments):
    knowledge_id = "6931070aae4184000bdad346"
    body = {
        "query": arguments["question"],
        "email": user_email,
        "knowledge_id": knowledge_id,
        "top_k" : 2,
        "score_threshold" : 0.3,
        "retrieval_type": "hybrid",
        "rerank_enabled": True,
        "keyword_enabled": True,
        # "metadata_filters":user_metadata_filters
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }
    response = requests.post("https://deepparser.crc.com.cn/v1/api/rag/retrieval", json=body, headers=headers)
    try:
        result = response.json()
        records = result.get("records", [])
        
        # 只筛选字段：score, content, file_url
        filtered_records = []
        for record in records:
            filtered_record = {
                "score": record.get("score"),
                "content": record.get("content"),
                "metadata": record.get("metadata"),
            }
            
            filtered_records.append(filtered_record)
        
        return json.dumps(filtered_records, ensure_ascii=False) if filtered_records else "未找到相关内容"
    except json.JSONDecodeError:
        return "知识库服务响应格式错误"
    
# 华润内部-华润内部制度知识库
def retrieve_crc_internal_policy_knowledgebase(arguments):
    knowledge_id = "693116ee4747a405123522d9"
    body = {
        "query": arguments["question"],
        "email": user_email,
        "knowledge_id": knowledge_id,
        "top_k" : 2,
        "score_threshold" : 0.3,
        "retrieval_type": "hybrid",
        "rerank_enabled": True,
        "keyword_enabled": True,
        # "metadata_filters":user_metadata_filters
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }
    response = requests.post("https://deepparser.crc.com.cn/v1/api/rag/retrieval", json=body, headers=headers)
    try:
        result = response.json()
        records = result.get("records", [])
        
        # 只筛选字段：score, content, file_url
        filtered_records = []
        for record in records:
            filtered_record = {
                "score": record.get("score"),
                "content": record.get("content"),
                "metadata": record.get("metadata"),
            }
            
            filtered_records.append(filtered_record)
        
        return json.dumps(filtered_records, ensure_ascii=False) if filtered_records else "未找到相关内容"
    except json.JSONDecodeError:
        return "知识库服务响应格式错误"
    
# 华润内部-华润审计案例知识库
def retrieve_crc_audit_case_knowledgebase(arguments):
    knowledge_id = "693116fa4747a4055b1abfd1"
    body = {
        "query": arguments["question"],
        "email": user_email,
        "knowledge_id": knowledge_id,
        "top_k" : 2,
        "score_threshold" : 0.3,
        "retrieval_type": "hybrid",
        "rerank_enabled": True,
        "keyword_enabled": True,
        # "metadata_filters":user_metadata_filters
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {user_token}"
    }
    response = requests.post("https://deepparser.crc.com.cn/v1/api/rag/retrieval", json=body, headers=headers)
    try:
        result = response.json()
        records = result.get("records", [])
        
        # 只筛选字段：score, content, file_url
        filtered_records = []
        for record in records:
            filtered_record = {
                "score": record.get("score"),
                "content": record.get("content"),
                "metadata": record.get("metadata"),
            }
            
            filtered_records.append(filtered_record)
        
        return json.dumps(filtered_records, ensure_ascii=False) if filtered_records else "未找到相关内容"
    except json.JSONDecodeError:
        return "知识库服务响应格式错误"
    


# 定义工具函数映射表
tool_functions = {
    "retrieve_general_audit_qualitative_knowledgebase": retrieve_general_audit_qualitative_knowledgebase,
    "retrieve_general_local_law_knowledgebase": retrieve_general_local_law_knowledgebase,
    "retrieve_general_national_law_knowledgebase": retrieve_general_national_law_knowledgebase,
    "retrieve_general_audit_knowledgebase": retrieve_general_audit_knowledgebase,
    "retrieve_general_audit_case_knowledgebase": retrieve_general_audit_case_knowledgebase,
    "retrieve_crc_business_units_policy_knowledgebase": retrieve_crc_business_units_policy_knowledgebase,
    "retrieve_crc_checklist_knowledgebase": retrieve_crc_checklist_knowledgebase,
    "retrieve_crc_internal_policy_knowledgebase": retrieve_crc_internal_policy_knowledgebase,
    "retrieve_crc_audit_case_knowledgebase": retrieve_crc_audit_case_knowledgebase
}


def get_response(messages):
    completion = client.chat.completions.create(
        model="qwen-plus",
        messages=messages,
        tools=tools,  # type: ignore[arg-type]
        parallel_tool_calls=True
    )
    return completion


# 初始化消息（纯 dict）
prompt = """你是一个智能知识检索路由助手。你掌管着9个独立的知识库工具。

**任务目标**：根据用户输入，自主判断并调用相关的知识库工具检索信息。

**核心原则**：
1. **最大化检索（宁多勿漏）**：不要害怕选多。只要该知识库可能包含答案的一丁点线索，就必须调用它。
2. **多库协同**：如果问题复杂，请务必跨库检索（例如同时调用库A和库B）。
3. **唯一性**：严禁对同一个知识库进行重复调用。

请直接根据用户问题，返回工具调用结果。"""
messages = [{"role": "assistant", "content": prompt},
            {"role": "user", "content": user_question}]

# 第一次调用
response = get_response(messages)
assistant_message = response.choices[0].message

# 👇 关键修改：转为 dict 再 append
assistant_dict = assistant_message.model_dump()  # ✅ OpenAI 官方推荐方式
# 如果 model_dump 不可用（旧版），用 dict(assistant_message) 替代
messages.append(assistant_dict)

# 在工具调用循环中替换为并行调用
if assistant_dict.get("tool_calls"):
    tool_calls = assistant_dict["tool_calls"]
    
    # 并行执行所有工具调用
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(tool_calls)) as executor:
        # 提交所有任务
        future_to_tool = {}
        for tool_call in tool_calls:
            tool_call_id = tool_call["id"]
            func_name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])
            
            print(f"准备调用工具 [{func_name}]，参数：{arguments}")
            
            if func_name in tool_functions:
                future = executor.submit(tool_functions[func_name], arguments)
                future_to_tool[future] = (tool_call_id, func_name)
            else:
                # 处理未知函数的情况
                pass
        
        # 收集所有结果
        for future in concurrent.futures.as_completed(future_to_tool):
            tool_call_id, func_name = future_to_tool[future]
            try:
                tool_result = future.result()
            except Exception as exc:
                tool_result = f"工具调用出错: {exc}"
            
            tool_message = {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": tool_result,
            }
            print(f"工具 [{func_name}] 返回：{tool_message['content']}")
            messages.append(tool_message)

# # 检查是否需要工具调用
# if not assistant_dict.get("tool_calls"):
#     print(f"无需调用查询工具，直接回复：{assistant_dict.get('content', '')}")
# else:
#     # 进入工具调用循环
#     while assistant_dict.get("tool_calls"):
#         for tool_call in assistant_dict["tool_calls"]:
#             print(f"工具调用：{tool_call}")
#             tool_call_id = tool_call["id"]
#             func_name = tool_call["function"]["name"]
#             arguments = json.loads(tool_call["function"]["arguments"])
            
#             print(f"正在调用工具 [{func_name}]，参数：{arguments}")
#             # 动态调用相应工具函数
#             if func_name in tool_functions:
#                 tool_result = tool_functions[func_name](arguments)
#             else:
#                 tool_result = f"未知工具函数: {func_name}"
            
#             tool_message = {
#                 "role": "tool",
#                 "tool_call_id": tool_call_id,
#                 "content": tool_result,
#             }
#             print(f"工具返回：{tool_message['content']}")
#             messages.append(tool_message)
        
        # 工具调用循环结束后，合并所有工具返回结果
        all_tool_results = []
        for message in messages:
            if message.get("role") == "tool":
                tool_content = message.get("content", "")
                if tool_content and tool_content != "未找到相关内容":
                    # 尝试解析JSON内容
                    try:
                        parsed_content = json.loads(tool_content)
                        if isinstance(parsed_content, list):
                            for item in parsed_content:
                                if item.get("content"):
                                    all_tool_results.append(item["content"])
                        else:
                            all_tool_results.append(tool_content)
                    except json.JSONDecodeError:
                        # 如果不是JSON格式，直接添加
                        all_tool_results.append(tool_content)

        # 合并所有结果作为最终回复
        if all_tool_results:
            final_response = "\n\n".join(all_tool_results)
            print(f"合并后的最终回复：\n{final_response}")
        else:
            print("未找到相关检索结果")
    
    print(f"助手最终回复：{assistant_dict.get('content', '')}")
    # print(messages)