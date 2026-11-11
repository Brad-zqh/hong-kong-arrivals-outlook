# 香港入境预测网页

IKUN 参赛队的公开历史模拟。预测方法和变量定义见 [方法说明](https://brad-zqh.github.io/hong-kong-arrivals-outlook/methods.html)，运行方式见 [复现代码](reproduction/README.md)。

网页呈现公开日度入境数据的历史模拟。五轮采用 2025–2026 年与正式赛程同月同日的窗口，用 2025-11-30 的赛前归档固定 10 个代理口岸。每轮覆盖两类访客及 15 天，评分采用第 2–15 日。每轮三版均由北京时间 12:00 前可取得的当日归档重新生成。第三版用于模拟提交，评分读取单独的公开实绩文件。

站点展示 MASE、缩放 Winkler 和 70% 区间覆盖率。两个缩放分数使用历史七日差分均值作分母，沿用项目的回测口径。每轮的 Excel 包含 Chronos-2 日历版本全部 300 个点预测和 300 对区间，采用练习表头。组委会发布模板后，以其原文件中的日期、口岸、客群、表名和填报位置为准。 [比赛规则](https://tourismforecasting.net/tfc/rules.html) · [官方模板](https://tourismforecasting.net/tfc/data_release.html#submission-templates)

## 本地

直接打开 `site/index.html`。从项目根目录生成网页及练习表格需安装 Python 3.12 和 openpyxl，并使用 `practice/strict_rehearsal` 下的预测和评分结果。

```powershell
python -B dashboard/rehearse.py --truth dashboard/local/downloads/immd-daily-passengers-975b06f237bd3cd8.csv
python -B dashboard/refresh_sources.py --archive dashboard/local/downloads
```

归档输入来自香港政府开放数据平台，覆盖 2021-01-01 至各次发布的前一日。公开站点使用的 API 来源为入境处公开客流和组委会发布页。 [入境事务处日度客流及归档](https://data.gov.hk/en-data/dataset/hk-immd-set5-statistics-daily-passenger-traffic/resource/e06a2a45-fe05-4eb4-9302-237d74343d52)

## 更新和提交

GitHub Actions 每日北京时间 12:23 检查公开客流、组委会训练库及模板，并发布网页数据状态。每日发布安排截至 2027-04-30。腾讯服务器也可托管 `site/`，并用本机调度运行 `refresh_sources.py`。

团队本地的 `local/downloads` 按内容指纹留档。正式赛轮用该轮最新版工作簿，核对实际历史截止日和 20 条序列后重跑模型。模板填报须保留官网原格式，校验日期、序列覆盖、非负值及区间次序。正式预测和方法材料用于队内校验及官方邮件提交。网页的公开内容是历史模拟、赛程和数据状态。 [提交规定](https://tourismforecasting.net/tfc/rules.html)
