---
name: locate
description: 定位能力包。把用户问句锚定到业务域(L2)、实体表和字段。含层级树获取、L2校验、子图获取、属性校验四个工具，按需挑用不要求走完。何时用：需要知道查哪个表哪个字段时。
---

# locate 定位能力包

## 用途
把用户问句锚定到具体的业务域(L2)、实体表和字段。

## 工具清单（按需挑用，不要求走完）

- **fetch_l1_l2_tree**：获取 L1(行业域)-L2(业务域) 层级树。参数 `{}`。
- **validate_l2**：校验/回填 L2 真实 UUID。参数 `{"l2_name":"名称"}` 或 `{"l2_id":"id"}`。返回 valid + l2_id。
- **fetch_subgraph**：获取 L2 子图（实体+属性+跨链关系）。参数 `{"l2_id":"UUID"}`。子图可能含多个实体。
- **validate_attributes**：校验/回填属性真实 code。参数 `{"entity_code":"表名","attributes":[{"attribute_code":"","attribute_name":"中文名"}]}`。

## 依赖关系（非顺序，缺啥补啥）
- fetch_subgraph 需要 l2_id（来自 validate_l2，或对话历史，或用户直接给）
- validate_attributes 需要 entity_code（来自 fetch_subgraph，或对话历史，或用户直接给）

## 硬约束
- **entity_en_name 才是物理表名**，entity_code 不能当表名（如用 `ProjectDefinition` 不是 `dim_ps_project_def`）
- validate_l2 返回 valid=false：告知用户未找到该业务域，终止
- validate_attributes 后 code 仍为空：该字段可能不存在，告知用户

## 挑用示例
- 只想看层级树 -> 只调 fetch_l1_l2_tree
- 已有 entity_code -> 直接 validate_attributes，跳过前三步
- 对话已定位同一 L2+实体 -> 跳过整个包
- 子图无匹配实体 -> 调 explore 的 search_entities 兜底搜

## L2 判定参考（常见问句->L2）
- "WBS成本/预算" -> 项目成本管理
- "项目定义/WBS元素/网络活动" -> 项目主数据
- "用电客户/户号" -> 客户主数据
- "电能表/计量点" -> 计量域

## 实体判定参考（子图多实体时选哪个）
- "WBS预算" -> ProjectBudget（不是 WbsElement）
- "WBS成本" -> ProjectCost（不是 WbsElement）
- "WBS元素" -> WbsElement
- "项目定义" -> ProjectDefinition
- "网络活动" -> NetworkActivity
