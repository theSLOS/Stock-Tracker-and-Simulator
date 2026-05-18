import logging

import pandas as pd
from PyQt6.QtCore import QThread, pyqtSignal


class PredictionWorker(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, df):
        super().__init__()
        self.df = df.copy()

    def run(self):
        try:
            logging.getLogger("prophet").setLevel(logging.ERROR)
            logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
            from prophet import Prophet
            df = self.df.reset_index()
            date_col = df.columns[0]
            prophet_df = df[[date_col, "Close"]].rename(columns={date_col: "ds", "Close": "y"})
            if hasattr(prophet_df["ds"], "dt") and prophet_df["ds"].dt.tz is not None:
                prophet_df["ds"] = prophet_df["ds"].dt.tz_localize(None)
            prophet_df["ds"] = pd.to_datetime(prophet_df["ds"])
            cutoff = prophet_df["ds"].max() - pd.Timedelta(days=730)
            prophet_df = prophet_df[prophet_df["ds"] >= cutoff]
            model = Prophet(
                daily_seasonality=False,
                weekly_seasonality=False,
                changepoint_prior_scale=0.15,
                changepoint_range=0.95,
            )
            model.fit(prophet_df)
            future = model.make_future_dataframe(periods=30)
            forecast = model.predict(future)
            self.finished.emit(forecast)
        except Exception as e:
            self.error.emit(str(e))
