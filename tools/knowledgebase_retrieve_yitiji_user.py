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
import json
import os
import random
import requests
import concurrent.futures

class SyToolsTool(Tool):

    # print(messages)
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:

        sy_retrieval_url = "http://192.168.110.35:8760/api/v1/retrieval"
        # Bearer token
        user_token = tool_parameters.get('token')
        # 元数据过滤列表
        # user_metadata_filters = tool_parameters.get('metadata')
        # if isinstance(user_metadata_filters, str):
        #     user_metadata_filters = json.loads(user_metadata_filters)
        master_results = []

        #获取知识库列表
        headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {user_token}"
            }
        response = requests.get("http://192.168.110.35:8760/api/v1/datasets", headers=headers)
        response = response.json()

        dataset_menu_lines = []
        dataset_id_map = {}

        valid_ids_set = set()

        for ds in response.get("data", []):
            d_id = ds.get("id")
            d_name = ds.get("name")
            # 加入白名单中
            valid_ids_set.add(d_id)
            # 清洗描述，如果是 None 就用名字代替
            d_desc = ds.get("description")
            if not d_desc or str(d_desc) == "None":
                d_desc = f"关于{d_name}的详细业务文档"
            
            # 存入 map 供工具执行时使用
            dataset_id_map[d_id] = ds
            
            # 添加到菜单文本
            dataset_menu_lines.append(f"- ID: {d_id} | 名称: 《{d_name}》 | 描述: {d_desc}")

        dataset_menu_str = "\n".join(dataset_menu_lines)

        # 定义工具
        universal_tool_def = PromptMessageTool(
                name="retrieve_knowledgebase",
                description="根据用户问题，在一个或多个指定的知识库中检索信息。",
                parameters={
                    "type": "object",
                    "properties": {
                        "question": {
                            "type": "string",
                            "description": "用户用来检索知识库的问题"
                        },
                        "target_dataset_ids": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "需要查询的知识库 ID 列表 (例如 ['id1', 'id2'])"
                        }
                    },
                    "required": ["question", "target_dataset_ids"]
                }
            )
        # 通用-知识库检索模板
        def retrieve_knowledgebase(arguments):
            print(f"函数内部接收参数类型: {type(arguments)}, 内容: {arguments}")
            raw_ids = arguments["target_dataset_ids"]
            if isinstance(raw_ids, str):
                raw_ids = [raw_ids]

            filter_ids = [tid for tid in raw_ids if tid in valid_ids_set]
            print(f"【Debug】过滤后发给API的 IDs: {filter_ids}")

            body = {
                "question": arguments["question"],
                "dataset_ids": filter_ids,
                "page_size": 1,
                "top_k" : 1,
                "similarity_threshold" : 0.5,
                # 选择rerank模型
                # "rerank_id":123
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {user_token}"
            }
            response = requests.post(sy_retrieval_url, json=body, headers=headers)
            try:
                result = response.json()
                # print("result---------------------------", result)
                data = result.get("data", {})
                records = data.get("chunks", [])
                
                # 筛选出字段
                filtered_records = []
                for record in records:
                    filtered_record = {
                        "content": record.get("content"),
                        # "dataset_id": record.get("dataset_id"),
                        "chunk_id": record.get("id"),
                        "document_keyword": record.get("document_keyword"),
                        "document_id": record.get("document_id"),
                        "similarity": record.get("similarity"),
                        # "term_similarity": record.get("term_similarity"),
                        # "vector_similarity": record.get("vector_similarity")
                    }
                    
                    filtered_records.append(filtered_record)
                
                return json.dumps(filtered_records, ensure_ascii=False)
            except json.JSONDecodeError:
                return json.dumps([], ensure_ascii=False)



        model_info = tool_parameters.get('chat_model')
        if model_info is None:
            raise ValueError("Missing 'chat_model' in tool_parameters")
        
        response_user = self.session.model.llm.invoke(
            model_config= LLMModelConfig(
                provider = model_info.get('provider'),
                model = model_info.get('model'),
                mode = model_info.get('mode'),
                completion_params= model_info.get('completion_params')
            ),
            prompt_messages =[
                SystemPromptMessage(content=f'''你是一个智能审计专家，具备多源知识检索能力。
                    **任务目标**：
                    1. 分析用户问题。
                    2. 浏览下方的【所有可用知识库】。
                    3. **自主决定**需要从哪些维度进行查证（例如：先查制度依据，再查过往案例，再查通用知识），目前知识库领域一般涉及法律法规、审计通用知识、审计案例、或企业内部法规、制度、案例等方面，你需要根据下方的知识库信息自己判别。
                    4. **发起并行工具调用**：你可以调用多次且但是不能超过两次 `retrieve_knowledgebase` 工具。每一次调用对应一个检索维度（维度内可包含多个相关库 ID），且不同的工具调用输入的问题需要针对领域、场景进行定制化。
                    5. **唯一性**：严禁对同一个知识库进行重复调用。
                    **所有可用知识库**：
                    {dataset_menu_str}

                    **要求**：
                    - 如果问题复杂，请务必拆解成不同的检索组。
                    - 严禁闲聊，直接进行工具调用。'''),
                UserPromptMessage(content=tool_parameters['query'])
            ],
            tools = [universal_tool_def],
            stream= False
        )

        llm_message_user = response_user.message
        print(f"Model Response Type: {type(llm_message_user)}")
        print(f"Tool Calls Count: {len(llm_message_user.tool_calls) if llm_message_user.tool_calls else 0}")
        print("第二次调用: ", response_user)


        if llm_message_user.tool_calls:
            tool_calls = llm_message_user.tool_calls
            tasks = []
            
            # --- 1. 解析参数 (保持之前的修复逻辑) ---
            for tool_call in tool_calls:
                func_name = tool_call.function.name
                raw_args = tool_call.function.arguments
                
                parsed_args_list = []
                
                try:
                    # 尝试正常解析
                    args_data = json.loads(raw_args)
                    if isinstance(args_data, dict):
                        parsed_args_list.append(args_data)
                    elif isinstance(args_data, list):
                        parsed_args_list.extend(args_data)
                except json.JSONDecodeError:
                    # 修复连体 JSON "}{"
                    try:
                        fixed_json = f"[{raw_args.replace('}{', '},{')}]"
                        args_data = json.loads(fixed_json)
                        if isinstance(args_data, list):
                            parsed_args_list.extend(args_data)
                    except Exception as e:
                        print(f"参数解析失败: {raw_args}")

                # 收集任务
                for args in parsed_args_list:
                    if isinstance(args, dict):
                        tasks.append((func_name, args))
            
            # --- 2. 并行执行任务 ---
            if tasks:
                with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(tasks), 4)) as executor:
                    future_to_tool = {}
                    
                    # 提交所有任务
                    for func_name, args in tasks:
                        if func_name == "retrieve_knowledgebase":
                            future = executor.submit(retrieve_knowledgebase, args)
                            # print("123456", args)
                            question = args.get('question', '未知问题')
                            future_to_tool[future] = f"{func_name} - {question}"
                    
                    # 收集所有结果
                    for future in concurrent.futures.as_completed(future_to_tool):
                        try:
                            tool_result_str = future.result()
                            # 【关键修改】：尝试将返回的字符串解析为JSON对象列表并合并
                            try:
                                result_data = json.loads(tool_result_str)
                                if isinstance(result_data, list):
                                    master_results.extend(result_data)
                                elif isinstance(result_data, dict):
                                    master_results.append(result_data)
                            except json.JSONDecodeError:
                                print(f"用户库工具返回非JSON数据，已忽略: {tool_result_str}")
                        except Exception as exc:
                            print(f"用户库工具执行异常: {exc}")

        final_json_output = json.dumps(master_results, ensure_ascii=False)
        
        # 即使为空也是 "[]"，符合 JSON 格式，不会出现文本提示
        yield self.create_text_message(final_json_output)
