# 香港入境预测网页

网页呈现公开日度入境数据的历史模拟。五轮采用 2025–2026 年与正式赛程同月同日的窗口，每轮覆盖 10 个代理口岸和两类访客，提交长度 15 日。评分采用第 2–15 日。三个模拟发布版本使用各自发布日前的历史客流计算四周同星期均值。Chronos-2 曲线来自已完成的同一窗口回测，使用最后一次发布的历史截止日。

站点展示 MASE、缩放 Winkler 和 70% 区间覆盖率。两个缩放分数使用历史七日差分均值作分母，沿用项目的回测口径。每轮的 Excel 包含 Chronos-2 日历版本全部 300 个点预测和 300 对区间，采用练习表头。组委会发布模板后，以其原文件中的日期、口岸、客群、表名和填报位置为准。 [比赛规则](https://tourismforecasting.net/tfc/rules.html) · [官方模板](https://tourismforecasting.net/tfc/data_release.html#submission-templates)

## 本地

直接打开 `site/index.html`。从项目根目录重建历史模拟和练习表格需安装 Python 3.12 和 openpyxl，并使用项目内已保存的 `practice/seasonal_rehearsal` 模型输出。

```powershell
python -B dashboard/rehearse.py
python -B dashboard/refresh_sources.py --archive dashboard/local/downloads
```

入境处数据快照覆盖 2021-01-01 至 2026-11-08。早期训练窗口来自事后保存的 CSV，历史逐日原始发布版本未经重建。公开站点使用的 API 来源为入境处公开客流和组委会发布页。 [入境事务处日度客流](https://data.gov.hk/en-data/dataset/hk-immd-set5-statistics-daily-passenger-traffic)

## 更新和提交

GitHub Actions 每日北京时间 12:23 检查公开客流、组委会训练库及模板，并发布网页数据状态。每日发布安排截至 2027-04-30。腾讯服务器也可托管 `site/`，并用本机调度运行 `refresh_sources.py`。

团队本地的 `local/downloads` 按内容指纹留档。正式赛轮用该轮最新版工作簿，核对实际历史截止日和 20 条序列后重跑模型。模板填报须保留官网原格式，校验日期、序列覆盖、非负值及区间次序。正式预测和方法材料用于队内校验及官方邮件提交。网页的公开内容是历史模拟、赛程和数据状态。 [提交规定](https://tourismforecasting.net/tfc/rules.html)
