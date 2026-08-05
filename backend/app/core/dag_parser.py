"""
DAG 解析器（纯解析逻辑，无 DB 依赖）

从 scheduler_core 剥离，供 ExecutionEngineV2 混合技能 DAG 执行使用。
"""

from collections import defaultdict, deque
from typing import List


class DAGParser:
    """
    DAG解析器
    解析DAG结构，构建执行计划
    """

    def __init__(self):
        pass

    def parse_dag(self, dag_definition: dict) -> dict:
        """
        解析DAG定义

        Args:
            dag_definition: DAG定义（JSON格式）

        Returns:
            dict: 解析后的DAG信息
        """
        nodes = dag_definition.get("nodes", [])
        edges = dag_definition.get("edges", [])

        # 构建邻接表
        adjacency = defaultdict(list)
        in_degree = defaultdict(int)
        node_map = {node["node_id"]: node for node in nodes}

        # 初始化所有节点的入度
        for node in nodes:
            in_degree[node["node_id"]] = 0

        # 构建边和计算入度
        for edge in edges:
            from_node = edge["from"]
            to_node = edge["to"]
            adjacency[from_node].append(to_node)
            in_degree[to_node] += 1

        # 拓扑排序
        execution_order = self.topological_sort(nodes, in_degree, adjacency)

        return {
            "nodes": node_map,
            "edges": edges,
            "adjacency": adjacency,
            "execution_order": execution_order,
            "parallel_levels": self.calculate_parallel_levels(execution_order, adjacency)
        }

    def topological_sort(self, nodes: List[dict], in_degree: dict,
                        adjacency: dict) -> List[str]:
        """
        拓扑排序

        Args:
            nodes: 节点列表
            in_degree: 入度字典
            adjacency: 邻接表

        Returns:
            List[str]: 执行顺序
        """
        queue = deque([node["node_id"] for node in nodes if in_degree[node["node_id"]] == 0])
        execution_order = []

        while queue:
            node_id = queue.popleft()
            execution_order.append(node_id)

            for neighbor in adjacency[node_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(execution_order) != len(nodes):
            raise ValueError("DAG存在环，无法进行拓扑排序")

        return execution_order

    def calculate_parallel_levels(self, execution_order: List[str],
                                   adjacency: dict) -> List[List[str]]:
        """
        计算并行层级

        Args:
            execution_order: 执行顺序
            adjacency: 邻接表

        Returns:
            List[List[str]]: 每层可以并行执行的节点
        """
        levels = []
        current_level = []
        visited = set()
        remaining_nodes = set(execution_order)

        reverse_adjacency = defaultdict(set)
        for from_node, to_nodes in adjacency.items():
            for to_node in to_nodes:
                reverse_adjacency[to_node].add(from_node)

        while remaining_nodes:
            # 找出所有没有依赖或依赖已完成的节点
            next_level = []
            for node_id in remaining_nodes:
                dependencies = reverse_adjacency.get(node_id, set())
                # 如果所有依赖都已访问，可以加入当前层
                if all(dep in visited for dep in dependencies if dep in remaining_nodes):
                    next_level.append(node_id)

            if not next_level:
                # 如果找不到可执行节点，选择第一个
                next_level = [next(iter(remaining_nodes))]

            levels.append(next_level)
            for node_id in next_level:
                visited.add(node_id)
                remaining_nodes.discard(node_id)

        return levels

    def validate_dag(self, dag_definition: dict) -> tuple[bool, str]:
        """
        验证DAG定义的有效性

        Args:
            dag_definition: DAG定义

        Returns:
            tuple: (是否有效, 错误信息)
        """
        try:
            required_fields = ["nodes", "edges"]
            for field in required_fields:
                if field not in dag_definition:
                    return False, f"缺少必需字段: {field}"

            nodes = dag_definition.get("nodes", [])
            if not nodes:
                return False, "DAG必须包含至少一个节点"

            node_ids = {node["node_id"] for node in nodes}
            edges = dag_definition.get("edges", [])

            for edge in edges:
                if edge["from"] not in node_ids:
                    return False, f"边引用了不存在的节点: {edge['from']}"
                if edge["to"] not in node_ids:
                    return False, f"边引用了不存在的节点: {edge['to']}"

            # 检查是否有环
            parsed = self.parse_dag(dag_definition)
            if len(parsed["execution_order"]) != len(nodes):
                return False, "DAG存在环"

            return True, "DAG验证通过"
        except Exception as e:
            return False, f"DAG验证失败: {str(e)}"
