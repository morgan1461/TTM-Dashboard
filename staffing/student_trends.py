import os
import glob
import pandas as pd
from datetime import date

# temp for manual pulling as of now , delete after access is fixed and implemented
TEMP_TRAINING_STAFFING_MASTER_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/TEMP Training Staffing Master"
ARCHIVED_TRAINING_STAFFING_MASTER_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/Training Staffing Master archive/"
STUDENT_TRENDS_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Student Trends/trends/"

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

    df = df.rename(columns={ # column will be added that indicates students that are not on the cdl track
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

def student_feature_engineering(df):
    '''Feature engineering for the student training staffing master report
        1 - Days to permit (permit date - training start date)
        2 - permit to cdl (cdl date - permit date)
        3 - total training days (cdl date - training start date)

        4 - overdue deadline?
    
    Args:
        df (pd.DataFrame): The cleaned training staffing master report
    Returns:
        pd.DataFrame: The training staffing master report with additional features
    '''
    date_cols = [
        'hire_date',
        'orientation_date',
        'cdl_training_start_date',
        'student_permit_deadline',
        'student_cdl_permit_date',
        'student_cdl_date',
    ]

    for col in date_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')

    # Calculate durations in days
    df['days_to_permit'] = (df['student_cdl_permit_date'] - df['cdl_training_start_date']).dt.days
    df['days_permit_to_cdl'] = (df['student_cdl_date'] - df['student_cdl_permit_date']).dt.days
    df['total_training_days'] = (df['student_cdl_date'] - df['cdl_training_start_date']).dt.days
    df['permit_overdue'] = (df['student_permit_deadline'] < pd.Timestamp.today()) & (df['student_cdl_permit_date'].isna())

    return df

# ------------------------------------------
# Load
# ------------------------------------------

def save_student_training_staffing_master(df, path=STUDENT_TRENDS_PATH):
    '''Saves the cleaned and feature engineered training staffing master report to an excel file
    
    Args:
        df (pd.DataFrame): The training staffing master report with additional features
        path (str): The path to save the cleaned and feature engineered training staffing master report
    Returns:
        None
    '''
    df.to_csv(os.path.join(path, f"cleaned_student_training_staffing_master_{str(date.today())}.csv"), index=False)
    return None

# ------------------------------------------
# Control
# ------------------------------------------
if __name__ == "__main__":
    tsm_master = TEMP_load_training_staffing_master()
    tsm_master = clean_student_training_staffing_master(tsm_master)
    tsm_master = student_feature_engineering(tsm_master)

    save_student_training_staffing_master(tsm_master)
    print(f"Cleaned and feature engineered training staffing master report saved to {STUDENT_TRENDS_PATH}")

    print(tsm_master.head())