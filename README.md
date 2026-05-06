# zsxq-daily

每日早上 7 点（HK）自动生成一份简报，提交到 `daily/YYYY-MM-DD.md`。

简报包括：
1. **央行动态** — Fed / ECB / PBoC / BoJ 过去 24 小时表态（Gemini + Google Search grounding）
2. **AI 产业链异动** — 涨跌幅 >2% 的标的（yfinance）
3. **贵金属 / 美元 / 利率** — 黄金、白银、DXY、美 10Y
4. **知识星球摘要** — 4 个星球过去 24 小时内容，按主题分类总结

---

## 一次性配置（约 30 分钟）

### 1. 拿到知识星球 cookie

1. 桌面浏览器打开 https://wx.zsxq.com，扫码登录
2. 任意点开一个星球
3. 打开 DevTools（F12）→ **Network** 标签 → 刷新页面
4. 在 filter 里输入 `topics`，找到 `api.zsxq.com/v1.10/groups/.../topics?...` 的请求
5. 点击它 → **Headers** → **Request Headers** → 复制 **整个 Cookie 字段**
6. 同时记下 URL 中 `groups/{NUMBER}/topics` 的数字 — 这是 `group_id`

每个星球点一遍，记录 4 个 group_id。Cookie 同一个就够。

### 2. 编辑 `config.yaml`

打开 `config.yaml`，把每个 planet 下的 `group_id: "REPLACE_ME"` 替换成实际 ID。

如果不需要某个分类的股票，删掉对应 ticker 即可。

### 3. 创建 GitHub 仓库

```bash
# 把这个文件夹推到一个 *私有* 仓库（cookie 在 secrets 里，但还是建议私有）
cd zsxq-daily
git init -b main
git add .
git commit -m "init"
gh repo create zsxq-daily --private --source=. --push
# 或者用网页：先在 github.com 建空 private repo，然后 git push
```

### 4. 配置 Secrets

在仓库 → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**：

| Name | Value |
|---|---|
| `ZSXQ_COOKIE` | 第 1 步复制的整段 Cookie |
| `GEMINI_API_KEY` | 你的 Gemini API key（[aistudio.google.com/apikey](https://aistudio.google.com/apikey)）|

### 5. 测试运行

不要等到明早，手动触发一次：

仓库 → **Actions** → **Daily Brief** → **Run workflow** → **Run workflow**。

跑完看 `daily/` 文件夹里有没有新增 MD 文件。第一次跑的话往 Actions 里看 logs，常见问题：
- `zsxq API error: ... 1059 ...` → cookie 过期或不对，重做第 1 步
- `yfinance` 错误 → 临时网络问题，下一次就好
- 央行 section 空白 → 当天确实没有重要表态

### 6. 接收通知（可选）

简报已经 commit 到 repo 了，若想得到推送：
- **GitHub email**: repo 顶部 **Watch** → **Custom** → 勾选 **Pushes**
- **RSS**: `https://github.com/<user>/zsxq-daily/commits.atom` 加进任何 RSS reader
- **手机通知**: 装 GitHub mobile app，开 push 通知

---

## 本地测试

```bash
pip install -r requirements.txt
export ZSXQ_COOKIE="zsxq_access_token=...; ..."
export GEMINI_API_KEY="AIza..."
python main.py
cat daily/$(date +%Y-%m-%d).md
```

---

## 调整

| 想做的事 | 改哪里 |
|---|---|
| 改运行时间 | `.github/workflows/daily.yml` 的 cron（UTC 时区）|
| 改 % 阈值 | `config.yaml` → `stock_threshold_pct` |
| 加/删 ticker | `config.yaml` → `ai_tickers` |
| 调每个星球的 prompt | `config.yaml` → `prompts` |
| 改 lookback 窗口 | `config.yaml` → `zsxq_lookback_hours` |
| 换更高质量模型 | `config.yaml` → `model: "gemini-2.5-pro"` |

---

## 已知问题

- **Cookie 会过期**（通常几个月）。失效后 Action 会失败 — 看 Actions 里的红叉提示，重新走第 1 步。
- **yfinance 偶尔 rate limit**：一般重试一次就好；workflow 里没加 retry，可以自己加。
- **A 股节假日**：大陆休市当天那些 `.SS`/`.SZ` 标的不会有数据，会安静跳过。
- **图片/图表**：知识星球帖子里的图片不会被解析；只总结文字。
