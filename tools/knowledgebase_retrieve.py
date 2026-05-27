from collections.abc import Generator
from pyexpat import model
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage
from dify_plugin.entities.model.llm import LLMModelConfig
from dify_plugin.entities.model.message import SystemPromptMessage, UserPromptMessage
from dify_plugin.entities.model.message import PromptMessageTool

import email
from wsgiref import headers
from openai import OpenAI
from datetime import datetime
import json
import os
import random
import requests
import concurrent.futures

class SyToolsTool(Tool):



    # print(messages)
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:

        user_question = tool_parameters.get('query')
        if isinstance(user_question, str):
            user_question = {"question": user_question}
        user_email = tool_parameters.get('email')
        user_token = tool_parameters.get('token')
        # if tool_parameters.get('top_k'):
        #     user_top_k = tool_parameters.get('top_k')
        # else:
        #     user_top_k = 5
        # if tool_parameters.get('score_threshold'):
        #     user_score_threshold = tool_parameters.get('score_threshold')
        # else:
        #     user_score_threshold = 0.3
        # if tool_parameters.get('retrieval_type'):
        #     user_retrieval_type = tool_parameters.get('retrieval_type')
        # else:
        #     user_retrieval_type = 'hybrid'
        # if tool_parameters.get('rerank_enabled'):
        #     user_rerank_enabled = tool_parameters.get('rerank_enabled')
        # else:
        #     user_rerank_enabled = False
        # if tool_parameters.get('keyword_enabled'):
        #     user_keyword_enabled = tool_parameters.get('keyword_enabled')
        # else:
        #     user_keyword_enabled = True

        if tool_parameters.get('metadata'):
            # 元数据过滤列表
            user_metadata_filters = tool_parameters.get('metadata')
            if isinstance(user_metadata_filters, str):
                user_metadata_filters = json.loads(user_metadata_filters)

            user_metadata_filters_1 = None
            user_metadata_filters_2 = None

            target_filter_item = None
            
            # 确保 raw_metadata 是列表
            if isinstance(user_metadata_filters, list):
                for item in user_metadata_filters:
                    # 找到 key 等于 ye_wu_dan_yuan 的那个字典
                    if item.get('key') == 'ye_wu_dan_yuan':
                        target_filter_item = item
                        break
            
            # 3. 如果找到了目标项，进行拆分逻辑
            if target_filter_item and 'value' in target_filter_item:
                all_values = target_filter_item['value']
                
                # 容错处理：万一 value 是字符串而不是列表，转成列表
                if isinstance(all_values, str):
                    all_values = [v.strip() for v in all_values.split(',')]

                # A. 构造 CR001 的过滤器
                if 'CR001' in all_values:
                    # 复制原始字典结构（保留 key, operator 等）
                    user_metadata_filters_1 = target_filter_item.copy()
                    # 强制修改 value 只包含 CR001
                    user_metadata_filters_1['value'] = ['CR001']
                    user_metadata_filters_1 = [user_metadata_filters_1]

                # B. 构造排除 CR001 的过滤器 (业务单元)
                # 筛选出不等于 CR001 的所有项
                bu_values = [v for v in all_values if v != 'CR001']
                
                if bu_values:
                    # 复制原始字典结构
                    user_metadata_filters_2 = target_filter_item.copy()
                    # 修改 value 为剩余的业务单元列表
                    user_metadata_filters_2['value'] = bu_values
                    user_metadata_filters_2 = [user_metadata_filters_2]
        tools = []
        if tool_parameters.get('gen_laws_kb') == True:
            tool1 = {"name": "retrieve_general_national_law_knowledgebase"}
            tools.append(tool1)
        if tool_parameters.get('gen_question_list_kb') == True:
            tool2 = {"name": "retrieve_audit_issue_list_knowledgebase"}
            tools.append(tool2)
        if tool_parameters.get('gen_audit_case_kb') == True:
            tool3 = {"name": "retrieve_general_audit_case_knowledgebase"}
            tools.append(tool3)
        if tool_parameters.get('gen_audit_qualitative_kb') == True:
            tool4 = {"name": "retrieve_general_audit_qualitative_knowledgebase"}
            tools.append(tool4)
        if tool_parameters.get('gen_audit_kb') == True:
            tool5 = {"name": "retrieve_general_audit_knowledgebase"}
            tools.append(tool5)


        # 通用-审计定性知识库
        def retrieve_general_audit_qualitative_knowledgebase(arguments):
            knowledge_id = "6936743c4747a4160787e52b"
            body = {
                "query": arguments["question"],
                "email": user_email,
                "knowledge_id": knowledge_id,
                "top_k" : 3,
                "score_threshold" : 0.3,
                "retrieval_type": "hybrid",
                # "rerank_enabled": True,
                "keyword_enabled": True
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
                    file_name = {"file_name": record.get("metadata").get("file_name")}
                    filtered_record = {
                        "score": record.get("score"),
                        "content": record.get("content"),
                        "metadata": file_name
                    }
                    
                    filtered_records.append(filtered_record)
                
                return json.dumps(filtered_records, ensure_ascii=False)
            except json.JSONDecodeError:
                return json.dumps([], ensure_ascii=False)
        

        # # 通用-审计定性知识库
        # def retrieve_general_audit_qualitative_knowledgebase(arguments):
        #     knowledge_id = "6936743c4747a4160787e52b"
        #     question = arguments["question"]
        #     question_parts = question.split(" ") if question.strip() else [question]
        #     all_records = []

        #     for part in question_parts:
        #         body = {
        #             "query": part.strip(),
        #             "email": user_email,
        #             "knowledge_id": knowledge_id,
        #             "top_k" : 3,
        #             "score_threshold" : 0.3,
        #             "retrieval_type": "hybrid",
        #             # "rerank_enabled": True,
        #             "keyword_enabled": True
        #         }

        #         headers = {
        #             "Content-Type": "application/json",
        #             "Authorization": f"Bearer {user_token}"
        #         }
        #         response = requests.post("https://deepparser.crc.com.cn/v1/api/rag/retrieval", json=body, headers=headers)
        #         try:
        #             result = response.json()
        #             records = result.get("records", [])
        #             all_records.extend(records)

        #         except json.JSONDecodeError:
        #             continue


        #     seen_contents = set()
        #     filtered_records = []
        #     for record in all_records:
        #         content = record.get("content")
        #         if content and content not in seen_contents:
        #             filtered_record = {
        #                 "score": record.get("score"),
        #                 "content": content,
        #                 # "metadata": record.get("metadata"),
        #             }
        #             filtered_records.append(filtered_record)
        #             seen_contents.add(content)
            
        #     # 限制总结果数量，按分数排序
        #     filtered_records.sort(key=lambda x: x.get("score", 0), reverse=True)

        #     filtered_records = filtered_records[:6]
            
        #     return json.dumps(filtered_records, ensure_ascii=False)
            
        # 通用-审计问题清单库
        def retrieve_audit_issue_list_knowledgebase(arguments):
            knowledge_id = "69367466ef772e14c557e700"
            body = {
                "query": arguments["question"],
                "email": user_email,
                "knowledge_id": knowledge_id,
                "top_k" : 4,
                "score_threshold" : 0.3,
                "retrieval_type": "hybrid",
                # "rerank_enabled": True,
                "keyword_enabled": True
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
                    file_name = {"file_name": record.get("metadata").get("file_name")}
                    filtered_record = {
                        "score": record.get("score"),
                        "content": record.get("content"),
                        "metadata": file_name
                    }
                    
                    filtered_records.append(filtered_record)
                
                return json.dumps(filtered_records, ensure_ascii=False)
            except json.JSONDecodeError:
                return json.dumps([], ensure_ascii=False)

            
        # 通用-国家级法律法规知识库
        def retrieve_general_national_law_knowledgebase(arguments):
            knowledge_id = "69367456ae418413190f3ca8"
            body = {
                "query": arguments["question"],
                "email": user_email,
                "knowledge_id": knowledge_id,
                "top_k" : 4,
                "score_threshold" : 0.3,
                "retrieval_type": "hybrid",
                "rerank_enabled": True,
                "keyword_enabled": True
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
                    file_name = {"file_name": record.get("metadata").get("file_name")}
                    filtered_record = {
                        "score": record.get("score"),
                        "content": record.get("content"),
                        "metadata": file_name
                    }
                    
                    filtered_records.append(filtered_record)
                
                return json.dumps(filtered_records, ensure_ascii=False)
            except json.JSONDecodeError:
                return json.dumps([], ensure_ascii=False)

            
        # 通用-审计通用知识库
        def retrieve_general_audit_knowledgebase(arguments):
            knowledge_id = "69367430ae4184137b44c123"
            body = {
                "query": arguments["question"],
                "email": user_email,
                "knowledge_id": knowledge_id,
                "top_k" : 4,
                "score_threshold" : 0.3,
                "retrieval_type": "hybrid",
                # "rerank_enabled": True,
                "keyword_enabled": True
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
                    file_name = {"file_name": record.get("metadata").get("file_name")}
                    filtered_record = {
                        "score": record.get("score"),
                        "content": record.get("content"),
                        "metadata": file_name
                    }
                    
                    filtered_records.append(filtered_record)
                
                return json.dumps(filtered_records, ensure_ascii=False)
            except json.JSONDecodeError:
                return json.dumps([], ensure_ascii=False)
            
        # 通用-审计案例库
        def retrieve_general_audit_case_knowledgebase(arguments):
            knowledge_id = "69367448ae418413190f3ca7"
            body = {
                "query": arguments["question"],
                "email": user_email,
                "knowledge_id": knowledge_id,
                "top_k" : 2,
                "score_threshold" : 0.3,
                "retrieval_type": "hybrid",
                # "rerank_enabled": True,
                "keyword_enabled": True
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
                    file_name = {"file_name": record.get("metadata").get("file_name")}
                    filtered_record = {
                        "score": record.get("score"),
                        "content": record.get("content"),
                        "metadata": file_name
                    }
                    
                    filtered_records.append(filtered_record)
                
                return json.dumps(filtered_records, ensure_ascii=False)
            except json.JSONDecodeError:
                return json.dumps([], ensure_ascii=False)
            
        # 华润内部-华润各事业部制度知识库
        def retrieve_crc_business_units_policy_knowledgebase(arguments):
            knowledge_id = "693674828edb13150a6c0f6f"

            # 检索集团库
            body1 = {
                "query": arguments["question"],
                "email": user_email,
                "knowledge_id": knowledge_id,
                "top_k" : 8,
                "score_threshold" : 0.4,
                "retrieval_type": "hybrid",
                "rerank_enabled": True,
                "keyword_enabled": True,
                "metadata_filters":user_metadata_filters_1
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {user_token}"
            }
            filtered_records = []
            response = requests.post("https://deepparser.crc.com.cn/v1/api/rag/retrieval", json=body1, headers=headers)

            result = response.json()
            records = result.get("records", [])
            try:
                # 只筛选字段：score, content, file_url
                for record in records:
                    file_name = {"file_name": record.get("metadata").get("file_name")}
                    filtered_record = {
                        "score": record.get("score"),
                        "content": record.get("content"),
                        "metadata": file_name
                    }
                    
                    filtered_records.append(filtered_record)

                # 检索业务单元库
                if user_metadata_filters_2:
                    body2 = {
                        "query": arguments["question"],
                        "email": user_email,
                        "knowledge_id": knowledge_id,
                        "top_k" : 30,
                        "score_threshold" : 0.25,
                        "retrieval_type": "hybrid",
                        "rerank_enabled": True,
                        "keyword_enabled": True,
                        "metadata_filters":user_metadata_filters_2
                    }
                    response2 = requests.post("https://deepparser.crc.com.cn/v1/api/rag/retrieval", json=body2, headers=headers)
                    result2 = response2.json()
                    records2 = result2.get("records", [])
                    
                    # 只筛选字段：score, content, file_url
                    for record in records2:
                        file_name = {"file_name": record.get("metadata").get("file_name")}
                        filtered_record = {
                            "score": record.get("score"),
                            "content": record.get("content"),
                            "metadata": file_name
                        }
                        
                        filtered_records.append(filtered_record)
                    
                return json.dumps(filtered_records, ensure_ascii=False)
            except json.JSONDecodeError:
                return json.dumps([], ensure_ascii=False)
            
        # 华润内部-华润检查要点清单知识库
        def retrieve_crc_checklist_knowledgebase(arguments):
            knowledge_id = "6936748b8edb13150a6c0f70"
            body = {
                "query": arguments["question"],
                "email": user_email,
                "knowledge_id": knowledge_id,
                "top_k" : 5,
                "score_threshold" : 0.3,
                "retrieval_type": "hybrid",
                "rerank_enabled": True,
                "keyword_enabled": True,
                "metadata_filters":user_metadata_filters
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
                    file_name = {"file_name": record.get("metadata").get("file_name")}
                    filtered_record = {
                        "score": record.get("score"),
                        "content": record.get("content"),
                        "metadata": file_name
                    }
                    
                    filtered_records.append(filtered_record)
                
                return json.dumps(filtered_records, ensure_ascii=False)
            except json.JSONDecodeError:
                return json.dumps([], ensure_ascii=False)
            
            
        # 华润内部-华润审计案例知识库
        def retrieve_crc_audit_case_knowledgebase(arguments):
            knowledge_id = "693674744747a415b71faef9"
            body = {
                "query": arguments["question"],
                "email": user_email,
                "knowledge_id": knowledge_id,
                "top_k" : 5,
                "score_threshold" : 0.3,
                "retrieval_type": "hybrid",
                "rerank_enabled": True,
                "keyword_enabled": True,
                "metadata_filters":user_metadata_filters
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
                    file_name = {"file_name": record.get("metadata").get("file_name")}
                    filtered_record = {
                        "score": record.get("score"),
                        "content": record.get("content"),
                        "metadata": file_name
                    }
                    
                    filtered_records.append(filtered_record)
                
                return json.dumps(filtered_records, ensure_ascii=False)
            except json.JSONDecodeError:
                return json.dumps([], ensure_ascii=False)
            


        # 定义工具函数映射表
        tool_functions = {
            "retrieve_general_audit_qualitative_knowledgebase": retrieve_general_audit_qualitative_knowledgebase,
            "retrieve_audit_issue_list_knowledgebase": retrieve_audit_issue_list_knowledgebase,
            "retrieve_general_national_law_knowledgebase": retrieve_general_national_law_knowledgebase,
            "retrieve_general_audit_knowledgebase": retrieve_general_audit_knowledgebase,
            "retrieve_general_audit_case_knowledgebase": retrieve_general_audit_case_knowledgebase,
            "retrieve_crc_business_units_policy_knowledgebase": retrieve_crc_business_units_policy_knowledgebase,
            "retrieve_crc_checklist_knowledgebase": retrieve_crc_checklist_knowledgebase,
            "retrieve_crc_audit_case_knowledgebase": retrieve_crc_audit_case_knowledgebase
        }

        # 处理工具调用
        all_tool_results = []
        if tools:
            tool_calls = tools
            
            # 并行执行所有工具调用
            with concurrent.futures.ThreadPoolExecutor(max_workers=len(tool_calls)) as executor:
                # 提交所有任务
                future_to_tool = {}
                for tool_call in tool_calls:
                    func_name = tool_call['name']
                    try:
                        arguments = user_question
                    except json.JSONDecodeError:
                        arguments = {}
                    
                    print(f"准备调用工具 [{func_name}]，参数：{arguments}")
                    
                    if func_name in tool_functions:
                        bound_function = tool_functions[func_name]
                        future = executor.submit(bound_function, arguments)
                        future_to_tool[future] = func_name
                    else:
                        print(f"未知工具函数: {func_name}")
                
                # 收集所有结果
                for future in concurrent.futures.as_completed(future_to_tool):
                    func_name = future_to_tool[future]
                    try:
                        tool_result = future.result()
                        print(f"工具 [{func_name}] 返回：{tool_result}")
                        all_tool_results.append(tool_result)
                    except Exception as exc:
                        tool_result = []
                        print(f"工具 [{func_name}] 出错：{tool_result}")
                        all_tool_results.append(tool_result)

        if all_tool_results:
            final_list = []
            
            for res_str in all_tool_results:
                try:
                    # 1. 把每个工具返回的 JSON 字符串还原成 Python 列表
                    data = json.loads(res_str)
                    
                    # 2. 如果是列表，就合并进去 (extend)
                    if isinstance(data, list):
                        final_list.extend(data)
                    # 3. 如果是字典或其他（防御性编程），就追加进去 (append)
                    else:
                        final_list.append(data)
                        
                except json.JSONDecodeError:
                    # 4. 如果遇到无法解析的字符串，手动封装成错误对象放入
                    final_list.append({
                        "status": "error", 
                        "content": f"结果解析失败: {str(res_str)}",
                        "score": 0
                    })
            
            # 5. 将合并后的总列表转为 JSON 字符串
            final_response = json.dumps(final_list, ensure_ascii=False)
        else:
            # 返回空列表的 JSON
            final_response = json.dumps([], ensure_ascii=False)

        yield self.create_text_message(final_response)



