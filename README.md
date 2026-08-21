# 事件时间线（Tidslinje）

Mål B 22021-24（斯德哥尔摩地方法院）案件的证据时间线，用一个纯静态网页把病历、聊天记录、购买记录、访问网站等证据按时间顺序可视化展示。

## 项目结构

| 文件 | 作用 |
|---|---|
| `timeline.csv` | 数据源。每行一条事件：`日期\|分类\|描述`。**以后要新增/修改事件，只改这个文件。** |
| `index.html` | 最终发布的页面。样式、交互逻辑都写在这个文件里；里面的事件数据（`const EVENTS=[...]`）是由 `timeline.csv` 生成的，不要手动改事件数据部分。 |
| `generate_timeline.py` | 把 `timeline.csv` 转换、同步进 `index.html` 的脚本。 |

## 已完成功能

- **时间轴可视化**：按年份分组，事件左右交替排列在中轴线两侧，条目间距按时间间隔的平方根缩放（间隔越长，视觉间距越大）。
- **分类颜色系统**：8 个分类（婚前协议 / 聊天短信邮件 / 购买记录 / 访问网站 / 网络搜索 / 病历 / 化验值 / 其他）各有专属颜色，时间轴卡片和顶部筛选按钮的颜色保持一致。
- **分类筛选**：点击顶部按钮可只看某一类事件，或点"Alla"看全部。
- **滚动进度条 + 卡片滚入动画**：页面顶部有阅读进度条，卡片滚动到可视区域时淡入。
- **响应式布局**：窄屏（≤680px）下时间轴收起为单侧列表。
- **CSV → HTML 自动化生成**：`generate_timeline.py` 会把 CSV 里较细的分类（比如具体聊天对象、"Besökt hemsida"）归并成页面用的 8 个大类，并做和现有页面一致的引号规整，详见下文。

## 如何使用（查看页面）

直接用浏览器打开 `index.html` 即可，不需要启动任何服务器：

```bash
open index.html
```

## 更新 CSV 后如何转成 HTML

1. 编辑 `timeline.csv`，新增/修改/删除事件行（格式：`日期|分类|描述`，日期用 `YYYY-MM-DD`）。
2. 在本目录下运行：

   ```bash
   python3 generate_timeline.py
   ```

   这会读取 `timeline.csv`，只重写 `index.html` 里的事件数据（`const EVENTS=[...]`）和页头的事件计数，其余样式/排版/交互代码完全不动。
3. 打开 `index.html` 检查效果无误后，`git add`/`git commit`/`git push`。

如果不想直接覆盖 `index.html`，可以先预览：

```bash
python3 generate_timeline.py --out preview.html
```

### 关于分类归并

`timeline.csv` 里的分类比页面上显示的更细（例如按聊天对象区分的 `Chatt Den tilltalade till Målsäganden`、`Chatt Den tilltalade till NN4` 等），但 `index.html` 的配色系统只认 8 个大类。`generate_timeline.py` 里的 `CATEGORY_MAP` 负责把细分类归并成这 8 个大类之一。

**如果在 CSV 里用了一个全新的分类**，运行脚本时会在终端打印警告，提示这个分类没有归并规则、颜色会退化成默认色。这时需要：

- 如果这只是某个已有大类的另一种写法（比如又加了一个新的聊天对象），在 `generate_timeline.py` 顶部的 `CATEGORY_MAP` 里加一条映射规则；或者
- 如果确实是全新的大类，需要同时在 `index.html` 的 `<style>` 里加对应的 CSS 变量和筛选按钮颜色规则，以及 `<script>` 里的 `CAT_COLOR` / `CAT_INDENT`。

`CATEGORY_MAP` 也可以用来给某个分类改名，而不改 CSV 原始数据 —— 比如 `Journal`（瑞典语"病历"）被 Google 翻译成中文后会变成"杂志"，容易误导不懂瑞典语的读者，所以映射成了消歧义更强的 `Patientjournal`（患者病历，瑞典《病历法》Patientdatalagen 里的正式用语）。同理改了 `index.html` 里 `CAT_COLOR`/`CAT_INDENT`/CSS 里的分类键名（颜色不变，只改名字），跑一遍脚本即可同步。

### 关于引号规整

对于以引号开头的直接引语（聊天记录原文等），脚本只去掉**最前面**那一层引号（例如 `"Foo bar".` → `Foo bar.`），同一条描述里后面出现的引号会原样保留。这个规则是从现有 `index.html` 内容反推出来的，和已发布页面的写法保持一致。

### 关于人名匿名化

出于隐私考虑，`timeline.csv` 里已经不含任何真实姓名，全部替换成瑞典语的匿名称谓（因为原文本身就是瑞典语）：

| 原名 | 替换为 | 说明 |
|---|---|---|
| Zhihui（含所有格 Zhihuis） | `Målsäganden` / `Målsägandens` | 原告 / 被害人（瑞典刑事诉讼用语，而非民事的 Kärande） |
| Zoe（含 Zoe Tang） | `Den tilltalade` | 被告 / 被指控人 |
| Kristina（S&P 理财顾问） | `Rådgivaren` | 按其专业角色称呼 |
| Martin Dreilich（主治医生） | `Läkaren` | 按其专业角色称呼 |
| Ir0nF1st / Bingwen He / Jietan Liu / Wei / Shoujji（私人联系人） | `NN1` `NN2` `NN3` `NN4` `NN5` | 瑞典法律文书里对匿名个人的标准占位符，按首次出现顺序编号，每人固定对应一个编号 |

**以后如果 CSV 里又出现新的真实姓名**，按同样的思路处理：案件当事人两方继续用 `Målsäganden`/`Den tilltalade`；有专业身份的（医生、律师、顾问等）用角色称呼；其他私人联系人依次分配下一个 `NN` 编号（当前用到 `NN5`，下一个新人应为 `NN6`）。改完 CSV 后记得同步更新 `generate_timeline.py` 里 `CATEGORY_MAP` 中含人名的分类键（比如 `Chatt Den tilltalade till NN1` 这种），否则脚本会在运行时警告该分类未归并。
