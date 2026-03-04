# 聚宽策略转可运行 Python 代码 Prompt

## 目标与范围
- **目标**：将聚宽策略代码转为**可在聚宽平台（joinquant.com 网页端回测）直接运行的 .py**。仅做格式整理与兼容性修复，**不修改任何策略逻辑**（选股、择时、买卖、风控等）。
- **环境**：兼容对象为聚宽网页端回测环境（Python 3、平台 pandas/jqdata），非本机环境。

---

## 一、核心原则
1. **逻辑不变**：不增删、不改写业务逻辑与算法。
2. **备注转注释**：非注释的说明文字每行前加 `#`；删除或注释 Jupyter 标记（如 `# In[37]:`）。
3. **必须做兼容修复**：按第二节做最小必要替换，否则平台回测会报错，视为未完成。
4. **保持原结构**：缩进、空行、代码顺序不变。

---

## 二、兼容性修复规则（机械替换）

| 类型 | 处理 |
|------|------|
| **废弃 import** | 删除 `from pandas.stats.api import ols` 及未使用的 `statsmodels` 等；其他平台已废弃/不存在的库：未用则删，有用则改为当前写法并加注释。 |
| **Python 2→3** | `print x` → `print(x)`；必要时 `iteritems()`→`items()`、`iterkeys()`→`keys()`。 |
| **pandas** | `df.sort('列名', ...)` → `df.sort_values('列名', ...)`；`df.ix` → `.loc[]` 或 `.iloc[]`。 |
| **聚宽 handle_data** | 若存在 `handle_data(context, data)` 且用 `data[code].mavg(...)`：改为 `run_daily(函数, time='09:30')`，函数内用 `history(..., unit='1d', field='close', ...)` 取日线并自算均线，再执行与原逻辑相同的择时/清仓；只换实现，不改“何时买卖”的规则。其他聚宽废弃 API 用当前推荐写法替代。 |
| **三引号** | 若 `'''...'''` 导致后续代码被当字符串或语法错误，改为多行 `#` 注释。 |

---

## 三、格式转换示例

**备注 → 注释**
```text
原：克隆自聚宽文章：https://...
    标题：xxx
后：# 克隆自聚宽文章：https://...
    # 标题：xxx
```

**代码内说明**
```text
原：选股函数
    def buy(context):
后：# 选股函数
    def buy(context):
```

**Jupyter**：删除或注释 `# In[数字]:` 行。

**兼容性**
```text
原：print df    → 后：print(df)
原：df.sort('peg', ascending=True)  → 后：df.sort_values('peg', ascending=True)
原：from pandas.stats.api import ols（未使用）  → 后：删除，可加 # 已移除废弃/未使用 import
```

---

## 四、处理步骤
1. 识别需改注释的说明文字与 Jupyter 标记 → 加 `#` 或删除。
2. 按第二节逐项做兼容性替换（import / print / pandas / 聚宽 API / 三引号）。
3. 通读确认无语法错误、无遗漏弃用用法，逻辑与原文一致。

---

## 五、输出要求
- **只输出**处理后的完整 Python 代码，**不要** markdown 代码块（\`\`\`）、不要说明或修改总结。
- 输出须满足：备注均为 `#` 注释、Jupyter 已清理、兼容性已修复、逻辑未改，可直接保存为 .py 在聚宽网页端运行回测。
