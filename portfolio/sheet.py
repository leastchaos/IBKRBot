"""utils for google sheet"""
import logging
import gspread as gs
import gspread_dataframe as gd
import pandas as pd


CREDENTIALS_PATH = "./credentials/google_service_account.json"
logger = logging.getLogger()

def get_worksheet(workbook: str, sheet_name: str) -> gs.Worksheet:
    """get the worksheet"""
    gc = gs.service_account(filename=CREDENTIALS_PATH)
    sh = gc.open(workbook)
    worksheet = sh.worksheet(sheet_name)
    return worksheet


def get_sheet_data(
    workbook: str,
    sheet_name: str,
    evaluate_formulas: bool = False,
    headers: list[str] | None = None,
) -> pd.DataFrame:
    """get the data from the sheet"""
    logger.info(f"Getting data from {workbook} {sheet_name}")
    worksheet = get_worksheet(workbook, sheet_name)
    dataframe = gd.get_as_dataframe(worksheet, evaluate_formulas=evaluate_formulas)
    logger.info(f"Data retrieved from {workbook} {sheet_name}")
    # if not isinstance(dataframe, pd.DataFrame):
    #     logger.error(f"Failed to retrieve data from {workbook} {sheet_name}")
    #     return pd.DataFrame()
    # remove empty rows
    logging.info(dataframe.head())
    dataframe = dataframe.dropna(how="all")
    # remove empty cols
    dataframe = dataframe.dropna(axis=1, how="all")
    # make sure all headers are in the dataframe and in the right order
    if headers is not None:
        # add the headers that are not in the dataframe
        for header in headers:
            if header not in dataframe.columns:
                dataframe[header] = None
        dataframe = dataframe[headers]
    return dataframe


def set_sheet_data(
    workbook: str, sheet_name: str, dataframe: pd.DataFrame, clear: bool = True
):
    """set the data to the sheet"""
    logger.info(f"Setting data to {workbook} {sheet_name}")
    worksheet = get_worksheet(workbook, sheet_name)
    if clear:
        worksheet.clear()
    gd.set_with_dataframe(worksheet, dataframe)
    logger.info(f"Data set to {workbook} {sheet_name}")
