# IKUN 香港入境预测复现

这些脚本复现网页中公开历史数据上的两种模型。每轮使用三份在模拟日中午前可见的归档。赛前另用一份归档固定 10 个代理口岸。脚本先保存预测和 SHA-256，再单独读取实绩完成评分。 [网页方法说明](https://brad-zqh.github.io/hong-kong-arrivals-outlook/methods.html) · [香港入境处历史数据](https://data.gov.hk/en-data/dataset/hk-immd-set5-statistics-daily-passenger-traffic/resource/e06a2a45-fe05-4eb4-9302-237d74343d52)

## 运行

在仓库根目录执行。需要 Python 3.10 或更高版本及 curl。模型权重由 Hugging Face 提供，约 478 MB。默认用 CPU，已安装兼容 PyTorch 的 CUDA 环境可传 `--device cuda`。公开网页的运行使用 chronos-forecasting 2.3.2 和 PyTorch 2.12.1+cu130。

```sh
python -m pip install chronos-forecasting==2.3.2 openpyxl
hf download amazon/chronos-2 config.json model.safetensors --revision e19c427c73837c00b5e932da5fbfede2929677ce --local-dir local/reproduction/chronos-2
python -B reproduction/strict_rehearsal_sources.py --archive-dir local/reproduction/archives
python -B reproduction/strict_rehearsal.py forecast --archive-dir local/reproduction/archives --weights local/reproduction/chronos-2 --out local/reproduction/results
curl -fL "https://app.data.gov.hk/v1/historical-archive/get-file?url=https%3A%2F%2Fwww.immd.gov.hk%2Fopendata%2Feng%2Ftransport%2Fimmigration_clearance%2Fstatistics_on_daily_passenger_traffic.csv&time=20260501-1029" -o local/reproduction/truth.csv
python -B reproduction/strict_rehearsal.py score --out local/reproduction/results --truth local/reproduction/truth.csv
```

实绩归档覆盖到最后一轮预测期末日。校验了各轮全部 1,500 个实绩值，与网页评分使用的后续公开版本一致。归档接口使用香港时间。 [历史归档 API](https://data.gov.hk/en/help/api-spec) · [Chronos-2 模型版本](https://huggingface.co/amazon/chronos-2/tree/e19c427c73837c00b5e932da5fbfede2929677ce)

输出包括冻结的预测 CSV、每次发布的评分、两个赛道各自的最佳四轮汇总和 10 份练习 Excel。不同硬件可能产生少量浮点差异。
