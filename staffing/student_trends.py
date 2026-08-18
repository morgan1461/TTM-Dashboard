import os
import glob
import pandas as pd
import numpy as np
from datetime import date

# temp for manual pulling as of now , delete after access is fixed and implemented
TEMP_TRAINING_STAFFING_MASTER_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/TEMP Training Staffing Master"
ARCHIVED_TRAINING_STAFFING_MASTER_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Staffing/Training Staffing Master archive/"
STUDENT_TRENDS_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Student Trends/trends/"
NON_CDL_TRACK_PATH = "K:/AP/TTM/Data/+ Data Repository/Dashboard/Student Trends/non_cdl_track_employees.txt"

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
    '''Cleans the training staffing master report for the timeline progress. This will parse important columns, rename to pythonic format, and convert to proper dtypes
    
    Args:
        df (pd.DataFrame): The raw training staffing master report
    Returns:
        pd.DataFrame: The cleaned training staffing master report
    '''
    # important columns: hire date, Orientation date, cdl permit date, cdl traiining start date, cdl date, permit deadline, etc
    important_columns = [
        'Name',
        'Employee ID',
        'Drivers #',
        'Active',
        'Permit',
        'CDL',
        'Hire Date', #jic
        'Orientation Date',
        'Student Permit Deadline', #jic
        'Student CDL Permit Date',
        'DOT Cert',
        'Student CDL Training Start Date',
        'Student CDL Date',
    ]

    df = df[important_columns]

    df = df.rename(columns={ # column will be added that indicates students that are not on the cdl track
    'Name': 'full_name', # hopefully will match up decently well with other df
    'Employee ID': 'employee_id',
    'Drivers #': 'driver_num',
    'Active': 'active',
    'Permit': 'permit',
    'CDL': 'cdl',
    'Hire Date': 'hire_date',
    'Orientation Date': 'orientation_date',
    'Student Permit Deadline': 'student_permit_deadline',
    'Student CDL Permit Date': 'student_cdl_permit_date',
    'DOT Cert': 'dot_cert',
    'Student CDL Training Start Date': 'cdl_training_start_date',
    'Student CDL Date': 'student_cdl_date',
})

    # convert cols to proper dtypes
    int_cols = ['employee_id', 'driver_num']
    bool_cols = ['active', 'permit', 'cdl']
    date_cols = [
        'hire_date',
        'orientation_date',
        'cdl_training_start_date',
        'student_permit_deadline',
        'student_cdl_permit_date',
        'student_cdl_date',
    ]

    df[int_cols] = df[int_cols].astype('Int64')
    df[bool_cols] = df[bool_cols].astype('Int64') # 1, 0
    df[date_cols] = df[date_cols].apply(lambda col: pd.to_datetime(col, format='mixed', errors='coerce').dt.normalize())

    return df

def student_feature_engineering(df):
    '''Feature engineering for the student training staffing master report

    
    Args:
        df (pd.DataFrame): The cleaned training staffing master report
    Returns:
        pd.DataFrame: The training staffing master report with additional features
    '''

    # Calculate durations in days
    df['orientation_to_permit_days'] = (df['student_cdl_permit_date'] - df['orientation_date']).dt.days
    df['permit_to_dot_days'] = (df['dot_cert'] - df['student_cdl_permit_date']).dt.days
    df['dot_to_training_start_days'] = (df['cdl_training_start_date'] - df['dot_cert']).dt.days
    df['training_start_to_cdl_days'] = (df['student_cdl_date'] - df['cdl_training_start_date']).dt.days
    df['orientation_to_cdl_days'] = (df['student_cdl_date'] - df['orientation_date']).dt.days

    # create a stage col based on where each individual student employee is at
    # most recent thing to be completed...
    # categories: inactive, non cdl track, orientation, cdl permit, dot permit, cdl training, cdl

    # define conditions
    conditions = [
        (df['active'] == 0),                       # inactive
        # (df['non_cdl_track'] == 1),             # non cdl track
        (df['cdl'] == 1),                          # cdl
        (df['student_cdl_permit_date'].notna()),  # cdl permit obtained
        (df['dot_cert'].notna()),                  # dot cert obtained
        (df['cdl_training_start_date'].notna()),  # cdl training
        (df['orientation_date'].notna()),          # orientation
    ]

    response = [
        'inactive',
        # 'non_cdl_track',
        'cdl',
        'cdl_permit',
        'dot_cert',
        'cdl_training',
        'orientation',
    ]

    df['status'] = np.select(
        [c.to_numpy(dtype=bool, na_value=False) for c in conditions],
        response,
        default='unknown'
    )

    return df

# WIP
def mark_non_cdl_track_students(df, path=NON_CDL_TRACK_PATH):
    '''Marks students that are not on the cdl track in the training staffing master report
    
    Args:
        df (pd.DataFrame): The cleaned training staffing master report
        path (str): The path to the txt file containing the list of students not on the cdl track - stored in data repository in TTM/Data - name must match what is on the sheet
    Returns:
        pd.DataFrame: The training staffing master report with an additional column indicating if a student is on the cdl track or not
    '''
    # Load the list of non-cdl track students from the txt file
    with open(path, 'r') as file:
        non_cdl_track_students = [line.strip() for line in file.readlines()]

    # Create a new column 'non_cdl_track' and mark students that are not on the cdl track
    df['non_cdl_track'] = df['full_name'].apply(lambda x: 1 if x in non_cdl_track_students else 0)

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
    tsm_master = mark_non_cdl_track_students(tsm_master)
    tsm_master = student_feature_engineering(tsm_master)


    save_student_training_staffing_master(tsm_master)
    print(f"Cleaned and feature engineered training staffing master report saved to {STUDENT_TRENDS_PATH}")

    # print(tsm_master.head())
    # print(tsm_master.info())
    # tsm_master.to_csv(os.path.join(f"TEST_{str(date.today())}.csv"), index=False)