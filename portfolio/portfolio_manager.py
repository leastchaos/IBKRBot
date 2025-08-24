import logging
import pandas as pd
from ib_async import IB
from . import data_fetcher, calculations, sheet

logger = logging.getLogger()


class PortfolioManager:
    def __init__(self, ib_client: IB, workbook_name: str, position_sheet: str, balance_sheet: str, scenario_sheet: str):
        self.ib_client = ib_client
        self.workbook_name = workbook_name
        self.position_sheet = position_sheet
        self.balance_sheet = balance_sheet
        self.scenario_sheet = scenario_sheet

    def update_portfolio_data(self):
        """
        Orchestrates the fetching, processing, and saving of portfolio data.
        """
        logger.info("Starting portfolio data update...")
        try:
            # 1. Fetch data
            positions_df = data_fetcher.fetch_positions(self.ib_client)
            balance_df = data_fetcher.fetch_balance(self.ib_client)
            scenario_df = sheet.get_sheet_data(self.workbook_name, self.scenario_sheet)

            # 2. Process data
            processed_positions_df = self._process_positions(positions_df, scenario_df)

            # 3. Save data
            sheet.set_sheet_data(self.workbook_name, self.position_sheet, processed_positions_df)
            sheet.set_sheet_data(self.workbook_name, self.balance_sheet, balance_df)

            logger.info("Portfolio data update completed successfully.")
        except Exception as e:
            logger.exception(f"An error occurred during portfolio update: {e}")

    def _process_positions(self, positions_df: pd.DataFrame, scenario_df: pd.DataFrame) -> pd.DataFrame:
        """
        Applies all the calculation functions to the positions DataFrame.
        """
        logger.info("Processing positions data...")
        positions_df['Symbol'] = positions_df['Symbol'].astype(str)
        scenario_df['UnderlyingSymbol'] = scenario_df['UnderlyingSymbol'].astype(str)

        # Merge scenario prices into positions_df
        positions_df = positions_df.merge(
            scenario_df,
            left_on="Symbol",
            right_on="UnderlyingSymbol",
            how="left",
        )

        # Apply calculations
        positions_df["StockEquivalentMovement"] = (
            positions_df["Delta"] * positions_df["Position"] * positions_df["Multiplier"]
        )
        positions_df["PositionType"] = positions_df.apply(calculations.determine_position_type, axis=1)
        positions_df["WorstCaseStockMovement"] = (
            positions_df["Position"]
            * positions_df["Multiplier"]
            * positions_df["PositionType"].isin(["Stock"])
            - positions_df["PositionType"].isin(["Short Put"])
            * positions_df["Position"]
            * positions_df["Multiplier"]
        )
        positions_df["InitialMaxRisk"] = positions_df.apply(calculations.calculate_initial_risk, axis=1)
        positions_df["CurrentMaxRisk"] = positions_df.apply(calculations.calculate_current_risk, axis=1)
        positions_df["WorstCaseRisk"] = positions_df.apply(
            calculations.calculate_worst_case_risk, axis=1
        )
        positions_df["TargetProfit"] = positions_df.apply(calculations.calculate_target_profit, axis=1)
        positions_df["Value_At_Risk_99%"] = positions_df.apply(
            calculations.calculate_var, axis=1, args=(0.01,)
        )
        positions_df["Value_At_Risk_40%"] = positions_df.apply(
            calculations.calculate_var, axis=1, args=(0.6,)
        )
        positions_df["Value_At_Risk_20%"] = positions_df.apply(
            calculations.calculate_var, axis=1, args=(0.8,)
        )
        positions_df["Value_At_Gain_20%"] = positions_df.apply(
            calculations.calculate_var, axis=1, args=(1.2,)
        )
        positions_df["Value_At_Gain_40%"] = positions_df.apply(
            calculations.calculate_var, axis=1, args=(1.4,)
        )
        positions_df["StrikePositions"] = positions_df["Strike"] * positions_df["Position"]
        positions_df["CostBasis"] = (
            positions_df["AvgCost"]
            * positions_df["Position"]
            * positions_df["ForexRate"]
        )
        positions_df["MarketValue"] = (
            positions_df["MarketPrice"]
            * positions_df["Position"]
            * positions_df["Multiplier"]
            * positions_df["ForexRate"]
        )
        positions_df["InstrinsicValue"] = positions_df.apply(
            calculations.calculate_instrinsic_value, axis=1
        )
        positions_df["TimeValue"] = (
            positions_df["MarketValue"] - positions_df["InstrinsicValue"]
        )

        logger.info("Positions data processed successfully.")
        return positions_df