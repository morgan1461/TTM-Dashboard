import os
import glob
import pandas as pd
from datetime import date

# temp for manual pulling as of now , delete after access is fixed and implemented
TEMP_TRAINING_STAFFING_MASTER_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/TEMP Training Staffing Master"
ARCHIVED_TRAINING_STAFFING_MASTER_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/Training Staffing Master archive/"

# ------------------------------------------
# Extract
# ------------------------------------------

def TEMP_load_training_staffing_master(path=TEMP_TRAINING_STAFFING_MASTER_PATH, archive_path=ARCHIVED_TRAINING_STAFFING_MASTER_PATH, archive=False):
    '''Temp function to pull the student cdl data from the training and staffing master file manually placed.
    Most recent file is taken from the folder, and an "archive" is saved in the path, this will be more relevant with the automated system, testing here
    
    Args: 
        path (str): The path to the directory containing a manually copied report
        archive_path (str): The path to archive a copy of the training staffing master, in case of need to audit in future.
        archive (bool): Determines if should be archived in the archive path or not, default False
    Returns:
        pd.DataFrame: 
    '''
    latest_file = max(glob.glob(os.path.join(path, "*.xlsx")), key=os.path.getctime)
    student_data = pd.read_excel(latest_file, sheet_name='Students')

    # save to excel
    if archive:
        student_data.to_excel(archive_path + f"{str(date.today())}_archived.xlsx")

    return student_data

# ------------------------------------------
# Transform
# ------------------------------------------

def clean_student_training_staffing_master(df):
    '''Cleans the training staffing master report for the timeline progress
    
    Args:
        df (pd.DataFrame): The raw training staffing master report
    Returns:
        pd.DataFrame: The cleaned training staffing master report
    '''
    # important columns: hire date, Orientation date, cdl permit date, cdl traiining start date, cdl date, permit deadline, etc
    important_columns = [
        'Name',
        'Drivers #',
        'Active',
        'Permit',
        'CDL',
        'Hire Date',
        'Orientation Date',
        'Student Permit Deadline',
        'Student CDL Permit Date',
        'Student CDL Training Start Date',
        'Student CDL Date',
    ]

    df = df[important_columns]

    df = df.rename(columns={
    'Name': 'full_name', # hopefully will match up decently well with other df
    'Drivers #': 'driver_num',
    'Active': 'active',
    'Permit': 'permit',
    'CDL': 'cdl',
    'Hire Date': 'hire_date',
    'Student CDL Training Start Date': 'cdl_training_start_date',
    'Orientation Date': 'orientation_date',
    'Student Permit Deadline': 'student_permit_deadline',
    'Student CDL Permit Date': 'student_cdl_permit_date',
    'Student CDL Date': 'student_cdl_date',
})

    return df

# ------------------------------------------
# Control
# ------------------------------------------
if __name__ == "__main__":
    tsm_master = TEMP_load_training_staffing_master()
    tsm_master = clean_student_training_staffing_master(tsm_master)

    print(tsm_master.head())