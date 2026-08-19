# 会话交接文档（2026-08-08）

> 用途：新开会话时作为背景上下文。可直接把本文件内容喂给新会话，或用 `ReadSessionContext` 读取。
> 主题：DeepAssetLens 配电重过载场景——数据模型修正 + 台区级计算重构 + IAB验证。

---

## 一、本次会话目标与结论

### 用户诉求（原始）
排查并修正配变重过载数据模型的 4 个问题：
1. 馈线-配变：一对多（已正确，无需改）
2. 台区-配变：需支持**多路供电**（1台区多配变）；多路时负载率 = 台区所有计量点功率 / SUM(各配变容量)，"不能简单粗暴"
3. 配变-调压设备-调压设备资产：严格 1:1:1（已正确，无需改）
4. 计量点-用户：一个计量点只属一个用户，但**一用户可多计量点**；一个计量点可有多表(equip_src_id)

附加："配电变压器数据可以少些，但应模拟计量点、用户多个的情况，重新扩展数据。"
后续："给我4类案例的问答，逐个跑一遍，分析结果合理性。"

### 结论
**全部完成并通过 IAB 验证**。4 个测试案例结果均合理。改动**未提交 git**（按用户要求"本次提交后不自动更新"）。

---

## 二、改动文件清单（未提交）

| 文件 | 状态 | 说明 |
|---|---|---|
| `backend/data/init/gen_x10_data.py` | **新增**(251行) | v3 数据生成：60配变/45台区/135计量点，台区多路+多计量点+台区表填充 |
| `backend/data/skills/scenarios/distribution-overload/SKILL.md` | **修改**(+302/-157) | 口径改台区级；第1/2/3步重构；输出规范+降级规则更新 |
| `backend/data/init/verify_skill_sql.py` | **新增**(96行) | 台区级第2/3步SQL验证脚本 |
| `backend/data/init/init_distribution_ontology.py` | 未改动(495行) | 早期本体导入脚本，仅参考；注意它用MySQL 33066(见下"已知问题") |
| `docs/配电重过载本体导入方案.md` | 未改动 | 本体导入映射方案文档，仅参考 |

```
git status --short
 M backend/data/skills/scenarios/distribution-overload/SKILL.md
?? backend/data/init/gen_x10_data.py
?? backend/data/init/init_distribution_ontology.py
?? backend/data/init/verify_skill_sql.py
?? docs/配电重过载本体导入方案.md
```

> 最近提交基线：`3bed53a refactor: decouple tupu from ragflow, add independent MySQL/ES stack`

---

## 三、数据模型设计（gen_x10_data.py 核心要点）

### 实体规模
| 实体 | 数量 | 说明 |
|---|---|---|
| 配变 | 60台(T001-T060) | 视图 vw_transformer = 非柱上60 + 柱上60 = 120行 |
| 台区 | 45个(dist_sta_id 1-45) | **30单路 + 15多路**；填充 cms20_dist_sta(原空表) |
| 客户 | 90个(cust_id 1-90) | 发电1-45 + 用电46-90 |
| 计量点 | 135个(inst_id 1-135) | 每台区3个(1102上网+1101发电+01用电) |
| 功率 | 135×2天×96点 = 25920行 | 20260801(有案例) + 20260802(全normal) |

### 拓扑映射函数（已验证正确）
```python
def sta_of_tf(j):        # 配变T00j -> 所属台区
    return j if j <= 30 else 31 + (j - 31) // 2   # 1-30单路, 31-45多路(每台区2配变)

def sta_total_cap(sta):   # 台区总容量(单路=配变容量, 多路=配变容量之和)
    if sta <= 30: return 800 + sta * 50
    k = sta - 30
    j1, j2 = 30 + 2*k - 1, 30 + 2*k
    return (800 + j1*50) + (800 + j2*50)

def inst_sta(j):          # 计量点inst j -> 所属台区
    if j <= 45: return j        # inst1-45 上网 -> 台区1-45
    if j <= 90: return j - 45   # inst46-90 发电 -> 台区1-45(同发电户多计量点!)
    return j - 90              # inst91-135 用电 -> 台区1-45
```

### 台区-配变拓扑（单路+多路混合）
```
台区1-30(单路): 台区i -> 1配变T00i              (30台区30配变)
台区31-45(多路): 台区31 -> T031+T032             (每台区2配变)
                台区32 -> T033+T034
                ...
                台区45 -> T059+T060             (15台区30配变)
合计: 60台配变 ✓
```

### 计量点-用户关系（一用户多计量点 + 一户多号 + 多表）
- **一用户多计量点**：发电户 cust_id 1-45 各有 2 个计量点
  - inst j(1102上网, 台区j) + inst j+45(1101发电, 台区j) → 同一 cust_id
  - 例：cust_id=1 → inst_id=1(1102上网) + inst_id=46(1101发电)
- **一户多号**：
  - gpc_id=1 与 gpc_id=201 共享 cust_id=1（发电户多号）
  - elec_cons_cust_id=46 与 301 共享 cust_id=46（用电户多号）
- **一计量点多表**：inst_id=1 有 equip_src_id=1(主表) + 201(副表,功率2x)；视图 `WHERE equip_src_id=inst_id` 只取主表

### 重过载案例设计（仅20260801）
| inst_id | 台区 | 类型 | 模式 | 说明 |
|---|---|---|---|---|
| 1 | 台区1(单路) | 1102上网 | overload | 720-825点 106%过载(连续8点) |
| 2 | 台区2(单路) | 1102上网 | heavy | 480-585点 89%重载(连续8点) |
| 3 | 台区3(单路) | 1102上网 | risk | 660-690+900点 105%但**不连续**(断续,不达8点→正常) |
| 121 | 台区31(多路) | 01用电 | heavy | 89%重载,演示多路总容量分摊 |
| 77 | 台区32(多路) | 1101发电 | heavy | 89%重载,演示多路+发电负载 |

> 20260802 全部 normal（演示日期传参：指定20260802应得0台重过载）

### 功率方向规则
- `1102上网`(inst 1-45)：power 取负（倒送），剧本用 `abs(power)` 还原
- `1101发电`(inst 46-90)：power 正
- `01用电`(inst 91-135)：power 正

### 参考数据码值
```python
VLEVELS = ['AC00101','AC00101','AC00101','AC00201','AC01101']  # 电压等级
INDCLS_GEN = ['D4410','D4445','D4441','D4444','D4442']          # 发电行业
INDCLS_USE = ['A000','B000','C000','D000','E000','F000','H000','I000','K000','G000']  # 用电行业
PSCATEG = ['01','02','03']      # 电源类别
CUSTCLS = ['01','02','03']      # 客户分类
```

---

## 四、SKILL.md 剧本设计（核心改动）

### 口径定义（v3 改为台区级）
```
负载率 = 台区汇集功率 / 台区总容量(SUM of 配变容量) × 100%
  - 单路台区: 1配变, 台区总容量=该配变容量
  - 多路台区: 多配变, 台区总容量=所有配变容量之和
连续性: PARTITION BY 负荷类型, 台区编号, date
重载: 连续≥8点 负载率≥80%; 过载: 连续≥8点 负载率≥100%
```

### 三步模块化（执行哪步取决于用户问什么）
| 用户问 | 执行 | 返回 |
|---|---|---|
| 户变关系(用电户/发电户 与 台区/配变) | 仅第1步 | 关系明细表 |
| 重过载情况(重载/过载/负载率/96点) | 第1+2步 | 判定结果表(含时段) |
| 负载占有率排序(倒排/影响最大) | 第1+2+3步 | 客户负载倒排表 |

### 第2步核心：拆功率/容量两条路径，JOIN在台区级（防笛卡尔积）
> **根因**：原第2步 `JOIN 计量点.dist_sta_id = 调压设备.dist_sta_id` 在多路台区(1台区2配变)会产生 N 行/计量点 → 功率翻倍。修正方法：功率走"计量点→台区"，容量独立CTE `GROUP BY dist_sta_id`，在台区级JOIN。
```sql
WITH 计量点台区 AS (  -- 功率路径: 计量点->台区(不JOIN配变,避免翻倍)
  SELECT DISTINCT 负荷类型, inst_id, inst_usage_cls, dist_sta_id AS 台区编号
  FROM cms20_inst_elec_cons WHERE inst_usage_cls IN ('01','1102','1101')
),
台区容量 AS (  -- 容量路径: 配变->台区, SUM容量
  SELECT v.dist_sta_id, SUM(t.capacity) AS 台区总容量, STRING_AGG(t.psrid,',') AS 配变列表
  FROM cms20_adj_volt_dev v JOIN ...asset va ... JOIN vw_transformer t
  WHERE t.runstate='20' GROUP BY v.dist_sta_id
),
dist_power AS (  -- 台区级JOIN: 功率/容量
  SELECT ..., SUM(CASE WHEN inst_usage_cls='1102' THEN abs(power) ELSE power END) AS 负载_kw,
         上述 / 台区总容量 * 100 AS 负载率
  FROM 计量点台区 m JOIN vw_cust_power_ts pw ON m.inst_id=pw.inst_id
       JOIN 台区容量 c ON m.台区编号=c.台区编号
  GROUP BY 负荷类型, 台区编号, 台区总容量, 配变列表, date, occur_time
),
flagged AS (... ROWS 7 PRECEDING PARTITION BY 负荷类型,台区编号,date ...)
```

### 第3步核心：多计量点客户先SUM后AVG
```sql
cust_agg AS (  -- 同客户多计量点先SUM(该时间点真实总负载)
  SELECT ..., SUM(CASE WHEN inst_usage_cls='1102' THEN abs(power) ELSE power END) AS 客户负载_kw
  FROM 户变关系 r JOIN vw_cust_power_ts pw ... JOIN over_pts o ...
  GROUP BY 客户类型,负荷类型,客户编号,...,date,occur_time
)
-- 再AVG跨达标时间点
SELECT ..., ROUND(AVG(客户负载_kw)::numeric,1) AS 平均负载_kW,
       ROUND(AVG(客户负载_kw)/台区总容量*100,1) AS 负载占有率
FROM cust_agg GROUP BY ... ORDER BY 负荷类型, 负载占有率 DESC
```
> 直接AVG各计量点会低估多计量点客户负载。over_pts JOIN 带date防跨天。

### 负荷类型与功率方向（inst_usage_cls决定）
| inst_usage_cls | 负荷类型 | 功率方向 | 汇集公式 |
|---|---|---|---|
| `01` | 用电负载 | power正 | `SUM(power)` |
| `1102` | 上网负载 | power负(倒送) | `SUM(abs(power))` |
| `1101` | 发电负载 | power正(出力) | `SUM(power)` |

> 三种负荷类型**分别**计算、分别判定，不混合。统一表达式：`SUM(CASE WHEN inst_usage_cls='1102' THEN abs(power) ELSE power END)`

### 动态条件传参（12项，执行时按用户意图注入WHERE）
| 用户说 | 注入条件 |
|---|---|
| "8月1日" | `AND pw.date='20260801'` |
| "在运配变" | `WHERE t.runstate='20'`(默认) |
| "停运配变" | `WHERE t.runstate='40'` |
| "在用计量点" | `AND i.inst_stat='02'` |
| "正常用电户" | `AND ec.ecc_stat='01'` |
| "正常发电户" | `AND g.gc_stat='01'` |
| "高压用户" | `AND ec.cust_cls='01'` |
| "分布式电源/光伏" | `AND g.cust_pscateg='01'` |
| "只看上网负载" | `AND i.inst_usage_cls='1102'` |

---

## 五、IAB 验证结果（4案例全过）

### 验证矩阵
| 案例 | 问句 | 步骤 | 结果 | 合理性 |
|---|---|---|---|---|
| 1 | 查8月1日上网负载的重过载情况 | 第2步+日期+负荷类型 | 台区1(106%过载)+台区2(89%重载) | ✅ 仅上网,日期20260801,台区3断续不达8点正确排除 |
| 2 | 查8月1日重过载台区的客户负载占有率倒排 | 第3步 | 4台区倒排 | ✅ 多路台区32(T033,T034)/31(T031,T032),一户多号(1/201),客户001占有率106%主因 |
| 3 | 查8月2日的配变重过载情况 | 第2步+日期 | 0台重过载 | ✅ 20260802全normal,日期传参生效,数据完整非缺数 |
| 4 | 查发电户和配变的户变关系 | 第1步 | 45发电户 | ✅ 一用户多计量点(1102+1101),台区名称(单路/多路),配变列表(T031,T032),一户多号 |

### 覆盖的验证点
- 三步模块化（不同问句触发不同步骤）
- 日期传参（20260801有案例 / 20260802全0）
- 负荷类型过滤（只看上网→仅上网台区）
- 多路供电（台区31/32, 配变列表多值, 总容量=配变容量之和）
- 一用户多计量点（发电户1-45各有1102+1101两个计量点）
- 一户多号（gpc_id 1/201, elec_cons_cust_id 46/301）
- 台区级计算（防笛卡尔积翻倍）
- abs(power) 还原上网负功率
- 边界案例（台区3断续不达连续8点→正常）

### IAB 测试技术要点（踩坑记录）
- 按钮点击：`getByRole('button',{name:'play-circle'}).click()` 会超时；改用 `tab.playwright.evaluate()` 读按钮bbox坐标，再 `tab.cua.click({x,y})` 坐标点击
- `keyboard.press`/`isDisabled`/`inputValue` 在 Codex IAB 不可用
- mcp__node_repl__js 长等待(55s+)会超时，拆成30-35s批次
- 测试入口 `http://localhost:23000`（前端dev server），setupProxy.js 转发到 28000 后端

---

## 六、当前环境状态（已验证）

### 运行中的服务
| 服务 | 容器/进程 | 端口 | 状态 |
|---|---|---|---|
| tupu 后端 | 本地进程 | **28000** | ✅ LISTENING |
| 前端 dev server | 本地进程 | **23000** | (需启动) |
| PostgreSQL | tupu_pg | **5432** | ✅ healthy |
| MySQL | docker-mysql-1 | **33066** | ✅ healthy (见已知问题) |
| Elasticsearch | docker-es01-1 | 11200 | ✅ healthy (ragflow栈) |
| Doris FE | tupu_doris_fe | 9030/18030 | ✅ |
| Neo4j | tupu_neo4j | 7474/7687 | ✅ healthy |
| Qdrant | tupu_qdrant | 6333-6334 | ✅ |

### 数据库连接串
- **PG(业务数据)**: `postgresql://postgres:postgres@localhost:5432/tupu` — gen_x10_data.py / verify_skill_sql.py 用这个
- **MySQL(元数据)**: `mysql+pymysql://root:root@localhost:33066/tupu` — kg_* 表在这

### PG 数据加载验证（已确认）
```
配变视图: 120 (非柱上60 + 柱上60)
台区表:   45 (30单路 + 15多路)
计量点:   135
客户:     90
功率天数: 2 (20260801 + 20260802)
功率总点: 25920 (135×2×96 ✓)
```
20260801 重过载台区（分负荷类型）：上网台区1/2、发电台区32、用电台区31（台区3断续正确排除）。

### 如何重新生成数据
```bash
# gen_x10_data.py 是幂等的（TRUNCATE + RESTART IDENTITY 后重建）
docker exec tupu_pg python3 - <<'EOF'  # 或本地 python
# 需 psycopg2; 脚本直连 PG 5432
EOF
# 实际执行：
cd backend/data/init && python gen_x10_data.py
# 验证：
python verify_skill_sql.py
```

---

## 七、已知问题与注意事项

### ⚠️ MySQL 端口不一致（重要）
- **工作区 AGENTS.md** 写 tupu MySQL = **3306**（独立栈，不复用ragflow 33066）
- **实际运行** `docker-mysql-1` 在 **33066**（ragflow 共享栈），无 3306 容器
- `init_distribution_ontology.py` 用 33066（与实际一致）
- **影响**：本次配电重过载任务只用 PG(5432)，不受影响。但若新会话要动 kg_* 元数据(MySQL)，需注意端口实际是 33066，AGENTS.md 的 3306 表是"目标态"未落地。
- ES 同理：AGENTS.md 说 tupu ES=9200，实际是 docker-es01-1 在 11200（ragflow栈）。

### SKILL.md 中 VARCHAR 类型标注
- 部分 CTE 用了 `::VARCHAR` 类型转换（如视图 transformer_type 列），PG 兼容，但若迁移到其他库需注意

### gen_x10_data.py 中视图重建
- 脚本每次 DROP VIEW + TRUNCATE 后重建 vw_transformer / vw_cust_power_ts
- vw_cust_power_ts 用 `LATERAL (VALUES ...)` 把96列宽表转窄表，`WHERE equip_src_id=inst_id` 去重副表

---

## 八、站立约束（不可违反，来自用户长期指令）

1. **不自动 git commit/push**："本次提交更新后，以后不自动更新了，除非明确说明再更新"——除非用户明确说"提交/同步到git"，不要动git
2. **不动项目代码**："别动项目代码"——只改数据层(gen_x10_data.py等) + 剧本层(SKILL.md)，不改 graph_query_neo4j.py 等后端业务代码
3. **后端固定 28000**，前端 23000，setupProxy.js 转发，前端代码用相对路径不硬编码端口
4. **浏览器测试用 IAB**（control-browser 技能 + mcp__node_repl__js + agent.browsers.get("iab")），禁外部浏览器，禁 `start`/`explorer` 弹窗
5. **Docker 端口映射不可改**（见工作区 AGENTS.md 端口表）
6. **YAGNI 原则**：不为想象需求写代码；标准库能搞定的不引依赖

---

## 九、可继续的方向（若新会话需要）

1. **提交本次改动**：用户若明确要求，`git add` 上述4个文件 + commit（gen_x10_data.py / SKILL.md / verify_skill_sql.py / docs方案）
2. **扩展案例**：可加更多负荷类型组合、跨天对比、停运配变(runstate=40)场景
3. **MySQL端口对齐**：把 AGENTS.md 的 3306 或实际容器统一（需用户决策，涉及ragflow解耦）
4. **本体导入回溯**：init_distribution_ontology.py 是早期脚本(用33066)，若要重导本体需确认MySQL端口与 kg_* 表现状

---

## 十、关键文件速查

| 要看什么 | 文件 |
|---|---|
| 数据怎么生成 | `backend/data/init/gen_x10_data.py` (251行) |
| 剧本SQL逻辑 | `backend/data/skills/scenarios/distribution-overload/SKILL.md` (346行) |
| SQL验证脚本 | `backend/data/init/verify_skill_sql.py` (96行) |
| 本体导入方案 | `docs/配电重过载本体导入方案.md` |
| 早期本体导入脚本 | `backend/data/init/init_distribution_ontology.py` (495行, 用33066) |
| 工作区原则/端口 | `AGENTS.md` |
| 本计划全文 | `.zcode/plans/plan-sess_059476e9-efc0-4095-920b-5c89a737d1bf.md` |
