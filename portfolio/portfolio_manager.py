import logging
import pandas as pd
from ib_async import IB
from typing import cast, Tuple

from portfolio import data_fetcher, calculations, sheet
from portfolio.models import PositionRow

logger = logging.getLogger()


class PortfolioManager:
    """
    Orchestrates the fetching, processing, and storing of portfolio data.
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

    # --- Private Helper Methods for Orchestration ---

    def _fetch_raw_data(self) -> Tuple[pd.DataFrame, ...]:
        """Fetches all raw data from IBKR and returns it as DataFrames."""
        logger.info("Stage 1: Fetching raw data from IBKR...")
        (
            positions,
            contract_details,
            original_contracts,
        ) = data_fetcher.fetch_positions_and_contracts(self.ib_client)
        
        if not positions:
            logger.warning("No positions found from IBKR. Aborting update process.")
            return tuple()

        balance_df = data_fetcher.fetch_balance(self.ib_client)
        positions_df = pd.DataFrame([vars(p) for p in positions])
        contracts_df = pd.DataFrame([vars(c) for c in contract_details])
        
        existing_market_data_df = sheet.get_sheet_data(
            self.workbook_name, self.market_data_sheet
        )
        market_data_list = data_fetcher.fetch_market_data(
            self.ib_client, original_contracts, existing_market_data_df
        )
        market_data_df = pd.DataFrame([vars(md) for md in market_data_list])

        return positions_df, contracts_df, market_data_df, balance_df

    def _read_and_prepare_dataframes(self) -> Tuple[pd.DataFrame, ...]:
        """Reads the raw data from sheets and prepares them for merging."""
        logger.info("Stage 2: Reading and preparing data...")
        pos_df = sheet.get_sheet_data(self.workbook_name, self.positions_sheet)
        con_df = sheet.get_sheet_data(self.workbook_name, self.contracts_sheet)
        mkt_df = sheet.get_sheet_data(self.workbook_name, self.market_data_sheet)
        scenario_df = sheet.get_sheet_data(self.workbook_name, self.scenario_sheet)

        # Ensure market data is unique by conId before merging
        mkt_df.drop_duplicates(subset=["conId"], keep="first", inplace=True)

        for df in [pos_df, con_df, mkt_df]:
            if "conId" not in df.columns:
                raise KeyError(f"Critical Error: 'conId' column is missing.")
            df["conId"] = pd.to_numeric(df["conId"])

        return pos_df, con_df, mkt_df, scenario_df

    def _combine_and_enrich_data(
        self,
        pos_df: pd.DataFrame,
        con_df: pd.DataFrame,
        mkt_df: pd.DataFrame,
        scenario_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """Merges dataframes and enriches with forex rates and scenarios."""
        logger.info("Stage 3: Combining and enriching data...")
        combined_df = pd.merge(pos_df, con_df, on="conId", how="left")
        combined_df = pd.merge(combined_df, mkt_df, on="conId", how="left")

        # Enrich with Forex rates
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

        # Enrich with Scenario data
        if not scenario_df.empty:
            scenario_df["symbol"] = scenario_df["symbol"].astype(str)
            combined_df = combined_df.merge(
                scenario_df,
                left_on="symbol",
                right_on="symbol",
                how="left",
            )
        else:
            combined_df["targetPrice"] = 0.0

        combined_df.rename(columns={"quantity": "position"}, inplace=True)
        return combined_df

    def _run_calculation_pipeline(self, df: pd.DataFrame) -> pd.DataFrame:
        """Runs a structured pipeline of calculations on the combined DataFrame."""
        logger.info("Stage 4: Running calculation pipeline...")
        records = [cast(PositionRow, row) for row in df.to_dict("records")]

        df["positionType"] = [calculations.determine_position_type(row) for row in records]
        df["marketValueBase"] = (df["marketPrice"] * df["position"] * df["multiplier"] * df["forexRate"])
        df["initialMaxRisk"] = [calculations.calculate_initial_risk(row) for row in records]
        df["notionalExposure"] = [calculations.calculate_notional_exposure(row) for row in records]
        df["intrinsicValue"] = [calculations.calculate_intrinsic_value(row) for row in records]
        
        # Re-cast to records after adding new columns for subsequent calculations
        records = [cast(PositionRow, row) for row in df.to_dict("records")]
        df["worstCaseRisk"] = [calculations.calculate_worst_case_risk(row) for row in records]
        df["targetProfit"] = [calculations.calculate_target_profit(row) for row in records]
        df["timeValue"] = df["marketValueBase"] - df["intrinsicValue"]

        return df

    def _save_data_to_sheets(self, *dataframes: Tuple[str, pd.DataFrame]):
        """Clears and saves a series of dataframes to their respective sheets."""
        logger.info("Stage 5: Saving all data to Google Sheets...")
        for sheet_name, df in dataframes:
            sheet.set_sheet_data(self.workbook_name, sheet_name, df)

    # --- Main Orchestration Method ---

    def update_portfolio_data(self):
        """
        Orchestrates the full workflow of fetching, processing, and saving data.
        """
        logger.info("--- Starting Portfolio Data Update ---")
        try:
            raw_data = self._fetch_raw_data()
            if not raw_data:
                # If no data is fetched, do nothing and preserve existing sheets.
                return

            positions_df, contracts_df, market_data_df, balance_df = raw_data
            
            # --- Save Raw Data Immediately ---
            self._save_data_to_sheets(
                (self.positions_sheet, positions_df),
                (self.contracts_sheet, contracts_df),
                (self.market_data_sheet, market_data_df),
                (self.balance_sheet, balance_df),
            )
            
            # --- Process and Save Combined View ---
            pos_df, con_df, mkt_df, scenario_df = self._read_and_prepare_dataframes()
            if any(df.empty for df in [pos_df, con_df, mkt_df]):
                logger.warning("One of the raw data sheets is empty after fetch. Aborting combined view update.")
                self._save_data_to_sheets(
                    (self.combined_sheet, pd.DataFrame())
                )
                return

            combined_df = self._combine_and_enrich_data(pos_df, con_df, mkt_df, scenario_df)
            final_df = self._run_calculation_pipeline(combined_df)

            self._save_data_to_sheets(
                (self.combined_sheet, final_df)
            )
            logger.info("--- Portfolio data update completed successfully. ---")

        except Exception as e:
            logger.exception(f"An error occurred during portfolio update: {e}")