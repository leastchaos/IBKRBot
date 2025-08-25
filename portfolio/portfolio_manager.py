import logging
import pandas as pd
from ib_async import IB
from typing import cast

from portfolio import data_fetcher, calculations, sheet
from portfolio.models import PositionRow

logger = logging.getLogger()


class PortfolioManager:
    """
    Orchestrates the fetching, processing, and storing of portfolio data
    across multiple Google Sheets for raw and processed data.
    """

    def __init__(
        self,
        ib_client: IB,
        workbook_name: str,
        positions_sheet: str,
        contracts_sheet: str,
        market_data_sheet: str,
        combined_sheet: str,
        balance_sheet: str,
        scenario_sheet: str,
        base_currency: str = "SGD",
    ):
        self.ib_client = ib_client
        self.workbook_name = workbook_name
        self.positions_sheet = positions_sheet
        self.contracts_sheet = contracts_sheet
        self.market_data_sheet = market_data_sheet
        self.combined_sheet = combined_sheet
        self.balance_sheet = balance_sheet
        self.scenario_sheet = scenario_sheet
        self.base_currency = base_currency

    def _run_calculation_pipeline(self, df: pd.DataFrame) -> pd.DataFrame:
        """Runs a structured pipeline of calculations on the combined DataFrame."""
        records = [cast(PositionRow, row) for row in df.to_dict("records")]

        df["positionType"] = [
            calculations.determine_position_type(row) for row in records
        ]
        if "marketPrice" not in df.columns:
            df["marketPrice"] = 0.0
        df["marketValueBase"] = (
            df["marketPrice"] * df["position"] * df["multiplier"] * df["forexRate"]
        )

        records = [cast(PositionRow, row) for row in df.to_dict("records")]
        df["initialMaxRisk"] = [
            calculations.calculate_initial_risk(row) for row in records
        ]
        df["notionalExposure"] = [
            calculations.calculate_notional_exposure(row) for row in records
        ]
        df["intrinsicValue"] = [
            calculations.calculate_intrinsic_value(row) for row in records
        ]

        records = [cast(PositionRow, row) for row in df.to_dict("records")]
        df["worstCaseRisk"] = [
            calculations.calculate_worst_case_risk(row) for row in records
        ]
        df["targetProfit"] = [
            calculations.calculate_target_profit(row) for row in records
        ]
        df["timeValue"] = df["marketValueBase"] - df["intrinsicValue"]

        return df

    def update_portfolio_data(self):
        """
        Orchestrates the full workflow of fetching, processing, and saving portfolio data.
        """
        logger.info("--- Starting Portfolio Data Update ---")
        try:
            # --- Stage 1: Fetch and Save Raw Data ---
            logger.info("Stage 1: Fetching and saving raw data...")
            (
                positions,
                contract_details,
                original_contracts,
            ) = data_fetcher.fetch_positions_and_contracts(self.ib_client)
            balance_df = data_fetcher.fetch_balance(self.ib_client)

            if not positions:
                logger.warning(
                    "No positions found. Clearing sheets and aborting update."
                )
                sheet.set_sheet_data(
                    self.workbook_name, self.positions_sheet, pd.DataFrame()
                )
                sheet.set_sheet_data(
                    self.workbook_name, self.contracts_sheet, pd.DataFrame()
                )
                sheet.set_sheet_data(
                    self.workbook_name, self.market_data_sheet, pd.DataFrame()
                )
                sheet.set_sheet_data(
                    self.workbook_name, self.combined_sheet, pd.DataFrame()
                )
                return

            positions_df = pd.DataFrame([vars(p) for p in positions])
            contracts_df = pd.DataFrame([vars(c) for c in contract_details])
            existing_market_data_df = sheet.get_sheet_data(
                self.workbook_name, self.market_data_sheet
            )
            market_data = data_fetcher.fetch_market_data(
                self.ib_client, original_contracts, existing_market_data_df
            )
            market_data_df = pd.DataFrame([vars(md) for md in market_data])

            sheet.set_sheet_data(
                self.workbook_name, self.positions_sheet, positions_df
            )
            sheet.set_sheet_data(
                self.workbook_name, self.contracts_sheet, contracts_df
            )
            sheet.set_sheet_data(
                self.workbook_name, self.market_data_sheet, market_data_df
            )
            sheet.set_sheet_data(self.workbook_name, self.balance_sheet, balance_df)
            logger.info("Successfully saved raw data to Google Sheets.")

            # --- Stage 2: Read, Combine, and Process Data ---
            logger.info("Stage 2: Reading and processing data...")
            pos_df = sheet.get_sheet_data(self.workbook_name, self.positions_sheet)
            con_df = sheet.get_sheet_data(self.workbook_name, self.contracts_sheet)
            mkt_df = sheet.get_sheet_data(self.workbook_name, self.market_data_sheet)
            scenario_df = sheet.get_sheet_data(self.workbook_name, self.scenario_sheet)

            if pos_df.empty or con_df.empty or mkt_df.empty:
                logger.warning(
                    "One of the raw data sheets is empty after reading. Aborting processing."
                )
                sheet.set_sheet_data(
                    self.workbook_name, self.combined_sheet, pd.DataFrame()
                )
                return

            for df_name, df in [
                ("Positions", pos_df),
                ("Contracts", con_df),
                ("Market Data", mkt_df),
            ]:
                if "conId" not in df.columns:
                    raise KeyError(
                        f"Critical Error: 'conId' column is missing from the '{df_name}' sheet."
                    )
                df["conId"] = pd.to_numeric(df["conId"])

            combined_df = pd.merge(pos_df, con_df, on="conId", how="left")
            combined_df = pd.merge(combined_df, mkt_df, on="conId", how="left")

            unique_currencies = combined_df["currency"].unique()
            forex_rates = {
                curr: data_fetcher.fetch_currency_rate(
                    self.ib_client, curr, self.base_currency
                )
                for curr in unique_currencies
            }
            combined_df["forexRate"] = combined_df["currency"].map(forex_rates)
            combined_df["riskFreeRate"] = combined_df["currency"].map(
                data_fetcher.RISK_FREE_RATES
            )

            if not scenario_df.empty:
                scenario_df["underlyingSymbol"] = scenario_df[
                    "underlyingSymbol"
                ].astype(str)
                combined_df = combined_df.merge(
                    scenario_df,
                    left_on="symbol",
                    right_on="underlyingSymbol",
                    how="left",
                )
            else:
                combined_df["targetPrice"] = 0.0

            combined_df.rename(columns={"quantity": "position"}, inplace=True)

            final_df = self._run_calculation_pipeline(combined_df)

            # --- Stage 3: Save Final Processed View ---
            logger.info("Stage 3: Saving combined and calculated data...")
            sheet.set_sheet_data(self.workbook_name, self.combined_sheet, final_df)

            logger.info("--- Portfolio data update completed successfully. ---")
        except Exception as e:
            logger.exception(f"An error occurred during portfolio update: {e}")