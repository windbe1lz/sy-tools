from collections.abc import Generator
from typing import Any
import json
import os
import requests
import concurrent.futures
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class SyToolsTool(Tool):
    
    # 删除了 _async_retrieve，因为后面用的是同步请求，不需要它了

    def _process_records(self, records: list, record_type: str):
        '''处理检索结果'''
        processed_records = []
        for record in records:
            filtered_records = {
                "content": record.get("content"),
                "chunk_id": record.get("id"),
                "document_keyword": record.get("document_keyword"),
                "type": record_type,
                "document_id": record.get("document_id"),
                "similarity": record.get("similarity"),
            }
            processed_records.append(filtered_records)
        return processed_records

    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        # 本地调试用 IP，容器部署请改回 host 名
        sy_retrieval_url = "http://ragflow-ragflow-cpu-1/api/v1/retrieval"
        # sy_retrieval_url = "http://192.168.110.220:8760/api/v1/retrieval"
        
        # --- 1. 参数获取 ---
        user_token = tool_parameters.get('token')
        user_query = tool_parameters.get('query')
        user_vector_similarity_weight = tool_parameters.get('user_vector_similarity_weight', 0.5)
        sy_top_N = tool_parameters.get('top_N', 10)
        sy_threshold = tool_parameters.get('similarity_threshold', 0.4)
        sy_vector_similarity_weight = tool_parameters.get('vector_similarity_weight', 0.5)
        
        # --- 2. 构建系统知识库 ID 列表 ---
        sy_datasets = []
        # 审计国家级法律库
        if tool_parameters.get('country_laws_kb') == True:
            sy_datasets.append("cc5a73b0e55f11f08bc50242ac1d0006")
        if tool_parameters.get('local_laws_kb') == True:
            sy_datasets.append("92de6f32e55b11f08bc50242ac1d0006")
        # 审计问题清单库
        if tool_parameters.get('gen_question_list_kb') == True:
            sy_datasets.append("a40d2638dbb811f08bc50242ac1d0006")
        # 审计案例库
        if tool_parameters.get('gen_audit_case_kb') == True:
            sy_datasets.append("d976d63edbb811f08bc50242ac1d0006")
        # 审计问题定性整改库
        if tool_parameters.get('gen_audit_qualitative_kb') == True:
            sy_datasets.append("7d5cdd76dbb811f08bc50242ac1d0006")
        # 审计基础知识库
        if tool_parameters.get('gen_audit_kb') == True:
            sy_datasets.append("abdda9dedbac11f08bc50242ac1d0006")

        # --- 3. 统一准备请求数据 (Requests Data) ---
        # 这种方式比先创建 tasks 再创建 requests_data 更清晰，且没有死代码
        requests_data = []

        # A. 添加系统知识库请求
        if sy_datasets:
            sy_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.environ.get('RAGFLOW_API_KEY', 'ragflow-xxxxxxxx')}"
            }
            sy_body = {
                "question": user_query,
                "dataset_ids": sy_datasets,
                "page_size": sy_top_N,
                "top_k": 100,
                "similarity_threshold": sy_threshold,
                "vector_similarity_weight": sy_vector_similarity_weight,
            }
            requests_data.append((sy_retrieval_url, sy_headers, sy_body, "sy"))

        # B. 添加用户知识库请求 (修复了解析逻辑)
        dataset_id_value = tool_parameters.get('dataset_id')
        # print("dataset_id_value:", dataset_id_value)
        # 使用 split + strip 处理 'id1', 'id2' 这种字符串
        if dataset_id_value and str(dataset_id_value).strip():

            dataset_id_value = json.loads(dataset_id_value)
            user_headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {user_token}"
            }
            user_body = {
                "question": user_query,
                "dataset_ids": dataset_id_value,
                "page_size": sy_top_N,
                "top_k": 100,
                "similarity_threshold": sy_threshold,
                "vector_similarity_weight": user_vector_similarity_weight,
            }
            requests_data.append((sy_retrieval_url, user_headers, user_body, "user"))

        # print(f"[DEBUG] 待执行请求总数: {len(requests_data)}")
        # --- 4. 定义同步请求函数 ---
        def sync_retrieve(url: str, headers: dict, body: dict):
            """同步检索函数，带错误处理"""
            try:
                # print(f"[-]正在请求: {url}")
                # 设置超时，防止无限等待
                response = requests.post(url, headers=headers, json=body, timeout=100)
                if response.status_code != 200:
                    print(f"[Error] HTTP状态码: {response.status_code}, 内容: {response.text[:200]}")
                    return []
                try:
                    result = response.json()
                except json.JSONDecodeError:
                    print(f"[Fatal] 返回非JSON格式: {response.text[:200]}")
                    return []
                if result.get("code") != 0:
                     print(f"[Error] RAGFlow业务报错: {result}")
                     return [] # 业务报错直接返回空
                # 安全获取 data
                data = result.get("data")
                if data is None:
                    # print(f"[Warn] data字段为None")
                    data = {}
                # print(f"[DEBUG] 获取到 {len(data.get('chunks', []))} 条数据")
                return data.get("chunks", [])
                
            except Exception as e:
                # print(f"[Exception] 请求异常: {str(e)}")
                return []

        # --- 5. 线程池并行执行 ---
        master_results = []
        if requests_data:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                # 提交任务，同时保存类型信息
                future_to_type = {}
                for url, headers, body, req_type in requests_data:
                    future = executor.submit(sync_retrieve, url, headers, body)
                    future_to_type[future] = req_type  # 将future与类型关联

                # 获取结果
                for future in concurrent.futures.as_completed(future_to_type):
                    records = future.result()
                    record_type = future_to_type[future]  # 获取对应的类型
                    
                    processed = self._process_records(records, record_type)
                    master_results.extend(processed)

        # --- 6. 返回最终结果 ---
        final_json_output = json.dumps(master_results, ensure_ascii=False)
        yield self.create_text_message(final_json_output)