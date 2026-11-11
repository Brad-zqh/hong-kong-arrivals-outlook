"""Calendar covariates and pinned Chronos-2 inference for the arrivals models."""

from datetime import date
from pathlib import Path

import numpy as np

from contest_calendar import HK_HOLIDAYS, WORKDAY, dates_by_year, event_dates


CONTEXT = 512
HORIZON = 15
QUANTILES = [0.15, 0.5, 0.85]
CHRONOS_REVISION = "e19c427c73837c00b5e932da5fbfede2929677ce"


def calendar_data(days: list[date]) -> dict[str, np.ndarray]:
    events, mainland, _ = event_dates()
    hk, work = dates_by_year(HK_HOLIDAYS), dates_by_year(WORKDAY)
    angle = np.array([2 * np.pi * day.weekday() / 7 for day in days])
    features = {
        "weekday_sin": np.sin(angle),
        "weekday_cos": np.cos(angle),
        "mainland_holiday": np.array([d in mainland for d in days]),
        "hongkong_holiday": np.array([d in hk for d in days]),
        "mainland_makeup_workday": np.array([d in work for d in days]),
    }
    for event in sorted({v[0] for v in events.values()}):
        features[f"event_{event}"] = np.array([events.get(d, ("", 0))[0] == event for d in days])
    return {name: values.astype("float32") for name, values in features.items()}


def chronos_forecaster(path: Path, *, device="cpu", names=None):
    from chronos import Chronos2Pipeline

    model = Chronos2Pipeline.from_pretrained(str(path), device_map=device, local_files_only=True)

    def forecast(history: np.ndarray, past: dict, future: dict, *, horizon=HORIZON) -> dict:
        outputs = {}
        for name, inputs in (
            ("chronos_independent", list(history)),
            ("chronos_joint", [history]),
            ("chronos_joint_calendar", [{"target": history, "past_covariates": past, "future_covariates": future}]),
        ):
            if names is not None and name not in names:
                continue
            quantiles, _ = model.predict_quantiles(inputs, prediction_length=horizon, context_length=CONTEXT,
                                                    quantile_levels=QUANTILES, batch_size=64)
            predictions = np.concatenate([q.detach().cpu().numpy() for q in quantiles], axis=0).transpose(1, 0, 2)
            outputs[name] = (predictions[:, :, 1], predictions[:, :, 0], predictions[:, :, 2])
        return outputs

    return forecast
